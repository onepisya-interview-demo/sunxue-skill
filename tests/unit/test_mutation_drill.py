"""Unit tests for ``sunxue_gates.mutation_drill``.

Covers:
- The three mutators (``mutate_synonym`` / ``mutate_split`` / ``mutate_soften``)
  on synthetic inputs that exercise the table mappings.
- ``hit_count`` — keyword overlap counter.
- ``extract_key_sentences`` — phrase-matching, length filter, dedup.
- ``run(root)`` — full gate contract on a synthetic SKILL.md.

Behavior (not string literals) is asserted wherever mutation testing would
otherwise survive trivially: e.g. we assert ``'必须' not in out`` rather
than ``out == '务必'``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sunxue_gates.mutation_drill import (
    HARD_KEYWORDS,
    KEY_PHRASES,
    MUTATORS,
    extract_key_sentences,
    hit_count,
    mutate_soften,
    mutate_split,
    mutate_synonym,
    run,
)
from sunxue_gates.results import GateResult

# ---------------------------------------------------------------------------
# M1 — synonym
# ---------------------------------------------------------------------------


class TestMutateSynonym:
    def test_replaces_must_synonym(self) -> None:
        out = mutate_synonym("你必须先做这件事。")
        assert "必须" not in out
        assert "务必" in out

    def test_replaces_dont_synonym(self) -> None:
        out = mutate_synonym("你不要再说这句话。")
        assert "不要" not in out
        assert "请勿" in out

    def test_idempotent_on_text_without_keywords(self) -> None:
        text = "没有强语气词的句子。"
        assert mutate_synonym(text) == text

    def test_deterministic(self) -> None:
        text = "你必须这样写，不要那样写。"
        assert mutate_synonym(text) == mutate_synonym(text)


# ---------------------------------------------------------------------------
# M2 — split
# ---------------------------------------------------------------------------


class TestMutateSplit:
    def test_returns_a_different_string(self) -> None:
        text = "你必须先做这件事，然后告诉我结果。"
        out = mutate_split(text)
        assert out != text

    def test_inserts_explanatory_conjunction(self) -> None:
        text = "前半句。后半句。"
        out = mutate_split(text)
        # Whatever the precise wording, the mutated output must reference
        # the explanatory conjunction introduced by the operator.
        assert "也就是说" in out

    def test_deterministic(self) -> None:
        text = "a, b, c"
        assert mutate_split(text) == mutate_split(text)

    def test_no_internal_separator_appends_marker(self) -> None:
        text = "一气呵成的句子没有任何标点"
        out = mutate_split(text)
        assert out != text
        # The fallback path appends the marker clause verbatim.
        assert "这一条不要忘" in out


# ---------------------------------------------------------------------------
# M3 — soften
# ---------------------------------------------------------------------------


class TestMutateSoften:
    @pytest.mark.parametrize(
        "src, banned_word",
        [
            ("你必须这样做。", "必须"),
            ("你务必签字。", "务必"),
            ("请勿大声说话。", "请勿"),
            ("严禁触碰开关。", "严禁"),
        ],
    )
    def test_strong_word_is_replaced(self, src: str, banned_word: str) -> None:
        out = mutate_soften(src)
        # '不要' deliberately appears inside the softened replacement
        # '尽量不要' — it's a softer carrier phrase, not a banned word.
        # The other three strict strong words must NOT survive.
        assert banned_word not in out, (banned_word, out)

    def test_soften_output_differs_from_input(self) -> None:
        text = "你必须改写这一段，不要写得太长。"
        assert mutate_soften(text) != text

    def test_soften_is_deterministic(self) -> None:
        text = "你必须改写这一段。"
        assert mutate_soften(text) == mutate_soften(text)


# ---------------------------------------------------------------------------
# hit_count + extract_key_sentences
# ---------------------------------------------------------------------------


class TestHitCount:
    def test_zero_on_empty(self) -> None:
        assert hit_count("") == 0

    def test_counts_overlap(self) -> None:
        text = "这里出现数字、服务者、物件。"
        n = hit_count(text)
        assert n >= 3

    def test_dedupes_keyword_with_multiple_occurrences(self) -> None:
        # '数字' appears three times but counts once.
        text = "数字 数字 数字"
        assert hit_count(text) == 1

    def test_no_overlap(self) -> None:
        assert hit_count("纯文字，没有任何硬指标关键词。") == 0


class TestExtractKeySentences:
    def test_finds_a_sentence_with_must(self) -> None:
        # The extractor requires sentences with 20 <= len(s) <= 200 to pass
        # the length filter, so pad the key sentence to satisfy that.
        text = (
            "无关首句。"
            "你必须先做这件事，这是不可绕过的前提条件，也是整个流程的基础步骤。"
            "其他无关内容填充在这里以确保长度满足要求。"
        )
        out = extract_key_sentences(text)
        assert any("必须" in s for s in out)

    def test_respects_max_n(self) -> None:
        # Five key phrases, each in its own sentence → max_n caps the result.
        sents = []
        for kw in KEY_PHRASES:
            sents.append(f"这一句包含关键词「{kw}」用于测试。")
        text = "\n".join(sents)
        out = extract_key_sentences(text, max_n=3)
        assert len(out) <= 3

    def test_filters_out_too_short_or_too_long_sentences(self) -> None:
        # '必须' inside a 3-char sentence (< 20) must be skipped.
        text = "必须\n" + "这一句必须出现而且长度足够通过过滤器。" * 5
        out = extract_key_sentences(text)
        assert all(20 <= len(s) <= 200 for s in out)

    def test_19_char_sentence_with_must_excluded(self) -> None:
        # Lower bound is strict: ``20 <= len(s)``. A 19-char sentence
        # containing a key phrase must NOT be picked up.
        # 19 chars: "这一句必须出现而且长" (count chars: 1+1+1+2+1+3+1+1+1 = 11, add 8 more)
        # Construct exactly 19 chars with "必须" inside.
        s = "必须" + "无" * 17  # 19 chars total
        out = extract_key_sentences(s)
        assert out == []

    def test_20_char_sentence_with_must_included(self) -> None:
        # Exactly 20 chars with "必须" — must be picked up.
        s = "必须" + "无" * 18  # 20 chars total
        out = extract_key_sentences(s)
        assert len(out) == 1

    def test_201_char_sentence_excluded(self) -> None:
        # Upper bound is strict: ``len(s) <= 200``. A 201-char sentence
        # with a key phrase must NOT be picked up.
        s = "必须" + "无" * 199  # 201 chars total
        out = extract_key_sentences(s)
        assert out == []

    def test_empty_on_no_match(self) -> None:
        assert extract_key_sentences("没有关键指令的纯文字内容。") == []


# ---------------------------------------------------------------------------
# run(root)
# ---------------------------------------------------------------------------


class TestRunGate:
    def test_passes_when_sentences_have_keywords(self, tmp_path: Path) -> None:
        # Build a SKILL.md with sentences that hit HARD_KEYWORDS.
        skill = (
            "---\nname: test\ndescription: x\n---\n"
            + "这一句必须出现数字、服务者、物件、闭环、沉默、排比、反问、程度副词、情绪、"
            "比喻、场景切换、我说好、遗留物等关键词。\n" + "其他无关内容。\n"
        )
        (tmp_path / "SKILL.md").write_text(skill, encoding="utf-8")
        gr = run(tmp_path)
        assert isinstance(gr, GateResult)
        assert gr.passed is True

    def test_fails_when_skill_missing(self, tmp_path: Path) -> None:
        gr = run(tmp_path)
        assert gr.passed is False
        # The MISS check is the first detail.
        assert any(c.name == "SKILL.md" and not c.passed for c in gr.details)

    def test_mutator_table_has_three_entries(self) -> None:
        assert len(MUTATORS) == 3

    def test_key_phrases_table_is_nonempty(self) -> None:
        assert len(KEY_PHRASES) >= 1

    def test_hard_keywords_table_is_nonempty(self) -> None:
        assert len(HARD_KEYWORDS) >= 1


# ---------------------------------------------------------------------------
# Drive uncovered branches in mutation_drill.run
# ---------------------------------------------------------------------------


class TestRunGateEmptyAndFullBranches:
    def test_empty_sentences_warns_but_passes(self, tmp_path: Path) -> None:
        # SKILL.md exists but contains NO key phrases → extract_key_sentences
        # returns []. The gate should PASS with a [WARN] check (drives
        # lines 161-169).
        (tmp_path / "SKILL.md").write_text(
            "---\nname: x\ndescription: y\n---\n"
            "正文没有任何关键指令的纯文字内容。\n"
            "完全没有任何必须或者不要的字样。\n",
            encoding="utf-8",
        )
        gr = run(tmp_path)
        assert gr.passed is True
        # The WARN check is emitted.
        assert any(c.name == "no_sentences" for c in gr.details)

    def test_max_n_caps_extraction(self, tmp_path: Path) -> None:
        # SKILL.md with one sentence per KEY_PHRASE — extractor finds 5
        # distinct sentences and the ``len(out) >= max_n`` break
        # (line 119) fires after the last one. With max_n=5 this is the
        # tightest exercise of that branch.
        sent_must = "你必须先做这件事，这是不可绕过的前提条件，也是整个流程的基础步骤。"
        sent_dont = "你不要这样说，这是不可接受的表达方式，也是整个流程的严重错误。"
        sent_change = "改成这样写吧，这是不可绕过的前提条件，也是整个流程的基础步骤。"
        sent_court = "出庭作证这件事，这是不可绕过的前提条件，也是整个流程的基础步骤。"
        sent_judge = "判断一个句子是否合格，这是不可绕过的前提条件，也是整个流程的基础步骤。"
        body = "\n".join([sent_must, sent_dont, sent_change, sent_court, sent_judge])
        (tmp_path / "SKILL.md").write_text(
            "---\nname: x\ndescription: y\n---\n" + body + "\n",
            encoding="utf-8",
        )
        gr = run(tmp_path)
        # All 5 KEY_PHRASES found → exactly 5 sentence.N.original checks.
        original_checks = [
            c for c in gr.details if c.name.startswith("sentence.") and c.name.endswith(".original")
        ]
        assert len(original_checks) == 5

    def test_failures_incremented_when_mutator_drops_all_hits(self, tmp_path: Path) -> None:
        # The ``failures += 1`` branch (line 194) fires when a mutator
        # produces 0 hard-keyword hits AND the original sentence had
        # >= 1 hit. The shipped mutators don't structurally destroy
        # HARD_KEYWORDS (they only touch their own tables), so we
        # monkey-patch :data:`MUTATORS` to add a "drop everything"
        # mutator and assert the FAIL is recorded.
        import sunxue_gates.mutation_drill as md

        # Build an SKILL.md whose key sentence contains BOTH a key phrase
        # and a hard keyword. The shipped mutators preserve the hard
        # keyword, but the injected mutator drops it.
        sent = "你必须先做这件事，这里出现了数字，也出现了服务者，这是一段关键指令。"
        # Must be 20..200 chars and contain "必须" (a KEY_PHRASE).
        assert 20 <= len(sent) <= 200
        assert "必须" in sent
        assert "数字" in sent and "服务者" in sent

        saved_mutators = md.MUTATORS
        try:
            # Inject a mutator that drops EVERY hard keyword.
            md.MUTATORS = (("M_drop", lambda text: "完全没有任何关键词的纯文字"),)
            (tmp_path / "SKILL.md").write_text(
                "---\nname: x\ndescription: y\n---\n" + sent + "\n",
                encoding="utf-8",
            )
            gr = md.run(tmp_path)
        finally:
            md.MUTATORS = saved_mutators

        # The mutator dropped the hard keywords → at least one FAIL.
        assert gr.passed is False
        # And the summary mentions "破坏硬约束".
        assert "破坏硬约束" in gr.summary
