"""Unit tests for ``sunxue_gates.regression_output``.

Covers the pure counter helpers and the comparison helper. Behavior over
the actual example files is exercised in ``tests/test_gates_live.py``.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest

from sunxue_gates import regression_output
from sunxue_gates.regression_output import (
    EXPECT,
    cmp,
    count_chen_mo,
    count_degree,
    count_direct_question_end,
    count_emo,
    count_fan_wen,
    count_loop_closure,
    count_metaphor,
    count_numbers,
    count_object_callback,
    count_pai_bi,
    count_punct,
    count_scene_break,
    count_server_polyphony,
    count_shuo_hao,
)

# ---------------------------------------------------------------------------
# cmp
# ---------------------------------------------------------------------------


class TestCmp:
    @pytest.mark.parametrize(
        "actual, expected, op, want",
        [
            (5, 5, "==", True),
            (4, 5, "==", False),
            (5, 5, ">=", True),
            (4, 5, ">=", False),
            (5, 5, "<=", True),
            (6, 5, "<=", False),
        ],
    )
    def test_comparison_ops(self, actual: int, expected: int, op: str, want: bool) -> None:
        assert cmp(actual, expected, op) is want

    def test_unknown_op_raises(self) -> None:
        with pytest.raises(ValueError):
            cmp(1, 1, "!=")


# ---------------------------------------------------------------------------
# Counter helpers
# ---------------------------------------------------------------------------


class TestCountNumbers:
    def test_chinese_numerals(self) -> None:
        assert count_numbers("一二三") == 1

    def test_arabic_digits(self) -> None:
        assert count_numbers("我有 12 和 3.5 个苹果") >= 2

    def test_combined(self) -> None:
        # Both Chinese and Arabic numerals in the same text. The Arabic
        # regex uses \b word boundaries, so digits must be ASCII-isolated
        # (separated from CJK by a space) to be counted.
        text = "一共有 12 个"
        assert count_numbers(text) >= 2

    def test_zero_on_plain_text(self) -> None:
        assert count_numbers("plain ascii text only here") == 0


class TestCountPaiBi:
    def test_three_term_paibi(self) -> None:
        # Pattern requires three '、' separators, so a 3-term list needs
        # the form ``A、B、C、D<terminator>``.
        assert count_pai_bi("苹果、香蕉、橘子、芒果。") == 1

    def test_two_terms_not_paibi(self) -> None:
        # Only two '、' — must NOT match the 3-term pattern.
        assert count_pai_bi("苹果、香蕉。") == 0

    def test_zero_on_plain_text(self) -> None:
        assert count_pai_bi("没有并列标点的句子。") == 0


class TestCountFanWen:
    def test_question_mark_in_first_80pct(self) -> None:
        assert count_fan_wen("怎么会这样？嗯。") == 1

    def test_ignores_late_question(self) -> None:
        # Question past the 80% cutoff must NOT count as 反问.
        body = "没有问号的句子。" * 50 + "这是末尾问号？"
        assert count_fan_wen(body) == 0

    def test_empty(self) -> None:
        assert count_fan_wen("") == 0


class TestCountMetaphor:
    def test_phrase_match(self) -> None:
        assert count_metaphor("他仿佛一头狮子。") == 1

    def test_no_false_positive_on_shuo_hao(self) -> None:
        # Earlier regex matched '同' inside '合同' as a metaphor connector.
        # Pin the regression: '合同' must NOT be flagged.
        assert count_metaphor("我们签订了合同。") == 0

    def test_zero_on_plain_text(self) -> None:
        assert count_metaphor("普通的描述性句子。") == 0


class TestCountShuoHao:
    def test_phrase_match(self) -> None:
        assert count_shuo_hao("我说好，咱们继续。") == 1

    def test_mama_match(self) -> None:
        assert count_shuo_hao("好，妈妈知道了。") == 1

    def test_zero_on_plain_text(self) -> None:
        assert count_shuo_hao("普通的叙述性句子。") == 0


class TestCountChenMo:
    def test_phrase_match(self) -> None:
        assert count_chen_mo("我没有说，只是点了点头。") >= 1

    def test_zero_on_plain_text(self) -> None:
        assert count_chen_mo("普通的对话。") == 0


class TestCountServerPolyphony:
    def test_known_role(self) -> None:
        assert count_server_polyphony("那个服务员走过来。") >= 1

    def test_zero_on_plain_text(self) -> None:
        assert count_server_polyphony("没有任何角色词的句子。") == 0


class TestCountObjectCallback:
    def test_na_marker(self) -> None:
        assert count_object_callback("那个杯子又空了一回。") >= 1

    def test_combined_marker_count(self) -> None:
        # Pin ``a + b``: the function returns the SUM of "那个 X" hits and
        # "它又" hits. A mutation that turns ``+`` into ``-`` would
        # produce wrong values.
        text = "那个东西。它又出现了一次。"
        # The "那个 X" regex is ``那个[一-龥]{1,4}`` so "那个东西" matches
        # (5 CJK chars after "那个" is 4 — at the boundary; actually 2
        # CJK chars "东西" is 2 which matches {1,4}). And "它又出现" also
        # matches. Total >= 2.
        assert count_object_callback(text) >= 2

    def test_only_ta_marker(self) -> None:
        # "它又..." only — no "那个" marker.
        assert count_object_callback("它又出现了。") >= 1

    def test_zero_on_plain_text(self) -> None:
        assert count_object_callback("没有物件标记的句子。") == 0


class TestCountLoopClosure:
    def test_repeated_phrase(self) -> None:
        # Length filter is strict: 4 < len(s) < 20, so the sentence must
        # be longer than 4 chars.
        text = "我在桥上等你。\n我在桥上等你。\n我在桥上等你。\n"
        # Three occurrences of a 6-char sentence → counted as 1 closure candidate.
        assert count_loop_closure(text) >= 1

    def test_five_char_sentence_included(self) -> None:
        # Strict lower bound: 4 < len(s), so a 5-char sentence counts.
        text = "abcde。\nabcde。\nabcde。\n"
        assert count_loop_closure(text) >= 1

    def test_four_char_sentence_excluded(self) -> None:
        # The filter is ``4 < len < 20``, strict on the lower bound —
        # exactly 4 chars must NOT count.
        text = "abcd。\nabcd。\nabcd。\n"
        assert count_loop_closure(text) == 0

    def test_twentyone_char_sentence_excluded(self) -> None:
        # Upper bound is strict ``len < 20`` — exactly 20 is included,
        # 21+ is excluded.
        long = "a" * 21
        text = f"{long}。\n{long}。\n{long}。\n"
        assert count_loop_closure(text) == 0

    def test_zero_on_unique_sentences(self) -> None:
        assert count_loop_closure("abcdef。ghijkl。mnopqr。") == 0


class TestCountSceneBreak:
    def test_horizontal_rule(self) -> None:
        assert count_scene_break("a\n---\nb") == 1

    def test_em_dash(self) -> None:
        assert count_scene_break("a\n——\nb") == 1

    def test_zero_on_plain_text(self) -> None:
        assert count_scene_break("普通的段落。") == 0


class TestCountDirectQuestionEnd:
    def test_in_tail(self) -> None:
        text = "普通段落。" * 5 + "那么，接下来该怎么办？"
        assert count_direct_question_end(text) >= 1

    def test_tail_window_is_exactly_200(self) -> None:
        # Pin the tail window: exactly 200 chars are inspected. A question
        # just inside the 200-char tail must count; one just outside
        # must not.
        pad = "无" * 199  # 199 chars of padding
        assert count_direct_question_end(pad + "？") >= 1
        pad2 = "无" * 200  # 200 chars of padding (no question at end)
        text = "？" + pad2  # question at position 0, far outside tail
        assert count_direct_question_end(text) == 0

    def test_outside_tail_ignored(self) -> None:
        # Question at the very start of the text is NOT in the last 200 chars.
        text = "？" + "无关文字。" * 200
        assert count_direct_question_end(text) == 0


class TestCountDegree:
    def test_match(self) -> None:
        assert count_degree("今天非常冷。") == 1

    def test_zero(self) -> None:
        assert count_degree("今天冷。") == 0


class TestCountEmo:
    def test_match(self) -> None:
        assert count_emo("我很难过，今天。") >= 1

    def test_zero(self) -> None:
        assert count_emo("今天天气不错。") == 0


class TestCountPunct:
    def test_all_four_categories(self) -> None:
        text = "你好！这是……一个——测试\u201c引号\u201d内容。"
        out = count_punct(text)
        assert set(out) == {"感叹号", "省略号", "破折号", "引号"}
        assert out["感叹号"] >= 1
        assert out["省略号"] >= 1
        assert out["破折号"] >= 1
        assert out["引号"] >= 1

    def test_uses_addition_not_subtraction(self) -> None:
        # Each counter is the SUM of two text.count() calls. If a future
        # refactor turns one into a subtraction, this test catches it.
        ascii_only = "Hello! ... -- text"
        out = count_punct(ascii_only)
        assert out["感叹号"] == 1
        assert out["省略号"] == 1
        assert out["破折号"] == 1

    def test_unicode_and_ascii_punct_both_counted(self) -> None:
        # Both 全角 and 半角 variants should be summed.
        text = "！!"  # one 全角 + one 半角
        out = count_punct(text)
        assert out["感叹号"] == 2

    def test_em_dash_and_double_hyphen_both_counted(self) -> None:
        text = "—— --"  # one em-dash + one double-hyphen
        out = count_punct(text)
        assert out["破折号"] == 2

    def test_ellipsis_variants_both_counted(self) -> None:
        text = "…… ..."  # one 中文 ellipsis + one ASCII triple-dot
        out = count_punct(text)
        assert out["省略号"] == 2

    def test_zero_when_no_punct(self) -> None:
        out = count_punct("plain ascii text")
        assert all(v == 0 for v in out.values())


# ---------------------------------------------------------------------------
# EXPECT table sanity
# ---------------------------------------------------------------------------


class TestExpectTable:
    def test_all_entries_have_valid_op(self) -> None:
        for _name, spec in EXPECT.items():
            assert spec[2] in {"==", ">=", "<="}

    def test_all_entries_have_nonnegative_expected(self) -> None:
        for _name, spec in EXPECT.items():
            assert spec[1] >= 0


class TestCheckTextDefensiveBranches:
    """Exercise the defensive branches inside ``_check_text.record``.

    These branches are unreachable through ``run()`` because every metric
    recorded inside ``_check_text`` is already present in :data:`EXPECT`.
    We call the (private) ``_check_text`` directly with EXPECT temporarily
    missing a metric, then restore.
    """

    def test_record_info_branch_when_metric_missing_from_expect(self) -> None:
        text = "我说好，咱们继续。"
        # Build a custom expect dict that omits the metric — exercises the
        # INFO branch via plan 2.2 dependency injection (no module-global
        # monkey-patching, no try/finally restore).
        partial = {k: v for k, v in regression_output.EXPECT.items() if k != "「我说好」类"}
        checks = regression_output._check_text("label", text, expect=partial)
        # The INFO check must be present for the missing metric.
        info_checks = [c for c in checks if "[INFO]" in c.message]
        assert len(info_checks) >= 1
        assert any("「我说好」类" in c.message for c in info_checks)
        # The module-level EXPECT must still contain the metric — DI
        # does not touch it.
        assert "「我说好」类" in regression_output.EXPECT


# ---------------------------------------------------------------------------
# Run gate — cover the MISS branch and the FAIL summary branch
# ---------------------------------------------------------------------------


class TestRunGateMissingSamples:
    """Drive the ``samples`` MISS branch of ``regression_output.run``."""

    def test_missing_example_file_reports_miss(self, tmp_path: Path) -> None:
        # Drive the MISS branch inside the for-loop by passing a
        # ``samples`` list whose Path points at a file that does not
        # exist. The auto-discovery glob would return [] here, so the
        # for-loop never runs — we exercise the loop's MISS branch
        # explicitly via the ``samples`` parameter.
        missing = tmp_path / "writing-not-here.md"
        gr = regression_output.run(
            tmp_path,
            samples=[("writing-not-here", missing)],
        )
        # The gate fails because the sample file does not exist.
        assert gr.passed is False
        # And the summary must contain the "文件缺失" wording.
        assert "文件缺失" in gr.summary
        # The MISS check itself is recorded in details.
        miss_checks = [c for c in gr.details if c.name == "writing-not-here" and not c.passed]
        assert len(miss_checks) == 1

    def test_examples_directory_missing(self, tmp_path: Path) -> None:
        # No examples/ at all → samples() returns []. run() must still
        # produce a GateResult (not raise) and FAIL it.
        gr = regression_output.run(tmp_path)
        assert gr.passed is False
        # "examples" WARN check is emitted.
        assert any(c.name == "examples" for c in gr.details)


class TestRunGateFailSummary:
    """Drive the ``elif passed`` branch (samples present but a metric FAILs)."""

    def test_fail_summary_when_metric_breaks(self, tmp_path: Path) -> None:
        # Create ALL five sample files so no MISS is reported, but make
        # one of them break a metric (e.g. 程度副词 > 0, expected == 0).
        # This drives the FAIL summary branch (line 325) because the
        # gate fails but there is no MISS.
        ex = tmp_path / "examples"
        ex.mkdir()
        stems = (
            "writing-巴菲特午餐",
            "writing-示例2-被割版",
            "writing-示例3-AI时代前端",
            "writing-十二个字节",
            "judgment-老客户账期",
        )
        bad = "这一段非常地长，特别冷。\n也有一些数字 123 和 456 等等。\n"
        for stem in stems:
            (ex / f"{stem}.md").write_text(bad, encoding="utf-8")
        gr = regression_output.run(tmp_path)
        # The gate fails because 程度副词 > 0 (expected == 0).
        assert gr.passed is False
        # And the summary must use the "失败 N 项" wording — NOT the
        # MISS-included wording.
        assert "失败" in gr.summary
        assert "文件缺失" not in gr.summary


# ---------------------------------------------------------------------------
# Plan 3.1 second half — mode-aware EXPECT tiers
# ---------------------------------------------------------------------------


class TestModeInference:
    """``writing-*`` and ``judgment-*`` filenames map to their tiers.

    ``meta-*`` is supported in the machinery (a future tester may ship a
    meta sample); an unknown prefix falls back to ``writing`` so new
    samples default to the strict tier instead of silently passing.
    """

    def test_writing_prefix_maps_to_writing(self) -> None:
        assert regression_output._mode_for_label("writing-巴菲特午餐") == "writing"

    def test_judgment_prefix_maps_to_judgment(self) -> None:
        assert regression_output._mode_for_label("judgment-老客户账期") == "judgment"

    def test_meta_prefix_maps_to_meta(self) -> None:
        assert regression_output._mode_for_label("meta-whatever") == "meta"

    def test_unknown_prefix_falls_back_to_writing(self) -> None:
        assert regression_output._mode_for_label("totally-unknown") == "writing"


class TestExpectByMode:
    """Per-mode EXPECT tables are well-formed."""

    def test_three_modes_defined(self) -> None:
        assert set(regression_output.EXPECT_BY_MODE) == {"writing", "judgment", "meta"}

    def test_writing_tier_is_empty_so_writing_default_applies(self) -> None:
        # Writing tier is empty by design: ``_merge_expect('writing')``
        # returns the original 17-entry EXPECT. We verify the empty dict
        # rather than the merged result so the contract is explicit.
        assert regression_output.EXPECT_BY_MODE["writing"] == {}

    def test_judgment_tier_relaxes_writing_specific_metrics(self) -> None:
        j = regression_output.EXPECT_BY_MODE["judgment"]
        for relaxed_metric in (
            "程度副词",
            "「我说好」类",
            "「我沉默了」类",
            "服务者复调",
            "物件 callback 标记",
            "闭环句候选",
            "场景切换",
        ):
            assert relaxed_metric in j, f"missing {relaxed_metric} relaxation"
            assert j[relaxed_metric][2] == "info", f"{relaxed_metric} not relaxed"

    def test_judgment_tier_keeps_structural_close_strict(self) -> None:
        # 结尾直接提问 is not in EXPECT_BY_MODE["judgment"]; the
        # judgment tier inherits the strict == 1 rule from the
        # writing tier via _merge_expect. We verify via the merged
        # table so the test reflects the actual behavior.
        merged = regression_output._merge_expect("judgment")
        assert merged["结尾直接提问"] == ("number", 1, "==")

    def test_judgment_tier_relaxes_digit_floor(self) -> None:
        j = regression_output.EXPECT_BY_MODE["judgment"]
        assert j["数字"][1] == 10
        assert j["数字"][2] == ">="

    def test_meta_tier_keeps_parallelism_and_rhetorical_strict(self) -> None:
        m = regression_output.EXPECT_BY_MODE["meta"]
        assert m["排比"][2] == "=="
        assert m["排比"][1] == 0
        assert m["反问"][2] == "=="
        assert m["反问"][1] == 0

    def test_meta_tier_relaxes_everything_else(self) -> None:
        m = regression_output.EXPECT_BY_MODE["meta"]
        for metric in m:
            if metric in {"排比", "反问"}:
                continue
            assert m[metric][2] == "info", f"{metric} not relaxed in meta"


class TestMergeExpect:
    """``_merge_expect(mode)`` overlays ``EXPECT_BY_MODE[mode]`` on ``EXPECT``."""

    def test_writing_merge_returns_full_expect(self) -> None:
        merged = regression_output._merge_expect("writing")
        assert merged == regression_output.EXPECT
        assert len(merged) == 17

    def test_judgment_merge_drops_digit_threshold(self) -> None:
        merged = regression_output._merge_expect("judgment")
        assert merged["数字"] == ("number", 10, ">=")
        assert merged["「我说好」类"] == ("number", 0, "info")
        assert merged["结尾直接提问"] == ("number", 1, "==")

    def test_meta_merge_relaxes_everything_except_parallelism(self) -> None:
        merged = regression_output._merge_expect("meta")
        assert merged["排比"] == ("number", 0, "==")
        assert merged["反问"] == ("number", 0, "==")
        relaxed_count = sum(1 for v in merged.values() if v[2] == "info")
        strict_count = sum(1 for v in merged.values() if v[2] in {"==", ">=", "<="})
        assert strict_count == 2
        assert relaxed_count == len(merged) - 2


class TestCheckTextModeDetail:
    """Each emitted CheckResult carries the sample's mode in its detail."""

    def test_mode_recorded_on_header_check(self, tmp_path: Path) -> None:
        sample = tmp_path / "writing-x.md"
        sample.write_text("", encoding="utf-8")
        gr = regression_output.run(tmp_path, samples=[("writing-x", sample)])
        header = next(c for c in gr.details if c.name == "writing-x")
        assert header.detail.get("mode") == "writing"

    def test_mode_recorded_on_header_for_judgment_sample(self, tmp_path: Path) -> None:
        sample = tmp_path / "judgment-x.md"
        sample.write_text("一二三四五六七八九十一二三四五六七八九十", encoding="utf-8")
        gr = regression_output.run(tmp_path, samples=[("judgment-x", sample)])
        header = next(c for c in gr.details if c.name == "judgment-x")
        assert header.detail.get("mode") == "judgment"

    def test_info_check_carries_relaxed_flag(self) -> None:
        text = "这是一段文本，包含许多程度副词，非常地很特别极其。"
        checks = regression_output._check_text(
            "label",
            text,
            expect=regression_output._merge_expect("judgment"),
            mode="judgment",
        )
        relaxed = [c for c in checks if c.name == "label.程度副词"]
        assert len(relaxed) == 1
        assert relaxed[0].passed is True
        assert "[INFO]" in relaxed[0].message
        assert "relaxed" in relaxed[0].message
        assert relaxed[0].detail.get("relaxed") is True

    def test_strict_check_records_op_and_mode(self) -> None:
        text = "一段普通的句子，里面没有任何特殊的写作技巧。"
        checks = regression_output._check_text(
            "label",
            text,
            expect=regression_output._merge_expect("judgment"),
            mode="judgment",
        )
        strict = [c for c in checks if c.name == "label.排比"]
        assert len(strict) == 1
        assert strict[0].passed is True
        assert "[OK]" in strict[0].message
        assert strict[0].detail.get("mode") == "judgment"


class TestSampleFileDiscovery:
    """The glob-based auto-discovery in ``sample_files`` excludes
    reference-quote filenames (anything containing ``原文片段`` /
    ``引用片段``). These are quoted source material, not
    original-composition samples, so the writing-tier counter
    checks would false-positive on them.
    """

    def test_quote_filenames_are_excluded(self, tmp_path: Path) -> None:
        examples = tmp_path / "examples"
        examples.mkdir()
        # Counter sample - must be picked up.
        (examples / "writing-real.md").write_text("一段普通的叙述文字", encoding="utf-8")
        # Reference quote - must be excluded.
        (examples / "writing-景甜-原文片段.md").write_text("原文片段内容", encoding="utf-8")
        # Another quote - also excluded.
        (examples / "judgment-quote-引用片段.md").write_text("引用片段内容", encoding="utf-8")
        samples = regression_output.sample_files(tmp_path)
        stems = [s[0] for s in samples]
        assert "writing-real" in stems
        assert "writing-景甜-原文片段" not in stems
        assert "judgment-quote-引用片段" not in stems

    def test_dedup_branch_is_covered_via_glob_injection(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # ``sample_files`` globs ``writing-*.md`` then ``judgment-*.md``;
        # in normal usage the two globs return disjoint paths so the
        # ``if path in seen: continue`` True arm (line 353) is unreachable.
        # Patch ``Path.glob`` on the examples dir so the second glob
        # returns a duplicate of a path the first glob already added to
        # ``seen`` — this drives the dedup True arm and verifies the
        # exact filter behavior: dedup keeps the first-seen entry, the
        # duplicate is silently dropped.
        examples = tmp_path / "examples"
        examples.mkdir()
        keep = examples / "writing-real.md"
        keep.write_text("一段普通的叙述文字", encoding="utf-8")

        real_glob = Path.glob

        def fake_glob(self: Path, pattern: str) -> Generator[Path, None, None]:
            # Only patch the examples dir's glob; leave everything else
            # alone so ``.exists()`` etc. on unrelated paths still work.
            if self != examples:
                yield from real_glob(self, pattern)
                return
            if pattern == "writing-*.md":
                yield from iter([keep])
                return
            if pattern == "judgment-*.md":
                # Second glob re-emits ``keep`` as if it matched both
                # patterns. The dedup ``if path in seen`` must skip it.
                yield from iter([keep])
                return
            return

        monkeypatch.setattr(Path, "glob", fake_glob)

        samples = regression_output.sample_files(tmp_path)
        stems = [s[0] for s in samples]
        # ``keep`` is in exactly one sample — the dedup ``continue``
        # dropped the duplicate emission from the judgment-* glob.
        assert stems == ["writing-real"]
        assert samples == [("writing-real", keep)]


class TestGateRunWithModes:
    """``run()`` applies per-sample modes end-to-end against tmp_path."""

    def test_meta_mode_treats_everything_as_info(self, tmp_path: Path) -> None:
        sample = tmp_path / "meta-z.md"
        sample.write_text(
            "任意内容。带很多程度副词，非常地很特别极其。我说好。我说好。",
            encoding="utf-8",
        )
        gr = regression_output.run(tmp_path, samples=[("meta-z", sample)])
        assert gr.passed is True
        meta_checks = [c for c in gr.details if c.detail.get("mode") == "meta"]
        assert len(meta_checks) >= 17


class TestLiveRepoModeRouting:
    """The live regression gate routes samples to their tier."""

    def test_judgment_samples_carry_judgment_mode(self) -> None:
        from pathlib import Path as _P

        gr = regression_output.run(_P("."))
        for c in gr.details:
            if c.name.startswith("judgment-") and c.detail.get("mode") != "judgment":
                raise AssertionError(f"{c.name} mode={c.detail.get('mode')}")

    def test_writing_samples_carry_writing_mode(self) -> None:
        from pathlib import Path as _P

        gr = regression_output.run(_P("."))
        for c in gr.details:
            if c.name.startswith("writing-") and c.detail.get("mode") != "writing":
                raise AssertionError(f"{c.name} mode={c.detail.get('mode')}")
