"""Unit tests for ``sunxue_gates.regression_output``.

Covers the pure counter helpers and the comparison helper. Behavior over
the actual example files is exercised in ``tests/test_gates_live.py``.
"""

from __future__ import annotations

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
        # Temporarily remove a metric so the INFO branch fires.
        saved = regression_output.EXPECT.copy()
        try:
            regression_output.EXPECT.pop("「我说好」类", None)
            checks = regression_output._check_text("label", text)
        finally:
            regression_output.EXPECT.clear()
            regression_output.EXPECT.update(saved)
        # The INFO check must be present for the missing metric.
        info_checks = [c for c in checks if "[INFO]" in c.message]
        assert len(info_checks) >= 1
        assert any("「我说好」类" in c.message for c in info_checks)
        # The restored EXPECT must be intact for subsequent tests.
        assert "「我说好」类" in regression_output.EXPECT


# ---------------------------------------------------------------------------
# Run gate — cover the MISS branch and the FAIL summary branch
# ---------------------------------------------------------------------------


class TestRunGateMissingSamples:
    """Drive the ``samples`` MISS branch of ``regression_output.run``."""

    def test_missing_example_file_reports_miss(self, tmp_path: Path) -> None:
        # Create an examples/ directory with a stem that sample_files
        # looks for, but DON'T create the file. The run() should emit a
        # MISS check and a "FAIL (... 含 N 个文件缺失)" summary.
        (tmp_path / "examples").mkdir()
        # Note: the implementation uses a fixed list of sample stems
        # (writing-巴菲特午餐, writing-示例2-被割版, …). We create only
        # a dummy directory tree and rely on all four stems being absent.
        gr = regression_output.run(tmp_path)
        # The gate MUST fail because none of the sample files exist.
        assert gr.passed is False
        # And the summary must contain the "文件缺失" wording.
        assert "文件缺失" in gr.summary

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
        # Create ALL four sample files so no MISS is reported, but make
        # one of them break a metric (e.g. 程度副词 > 0, expected == 0).
        # This drives the FAIL summary branch (line 325) because the
        # gate fails but there is no MISS.
        ex = tmp_path / "examples"
        ex.mkdir()
        stems = (
            "writing-巴菲特午餐",
            "writing-示例2-被割版",
            "writing-示例3-AI时代前端",
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
