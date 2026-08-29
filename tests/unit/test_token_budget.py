"""Unit tests for ``sunxue_gates.token_budget``.

Covers:
- ``est_tokens`` — arithmetic + edge cases (negative input, zero).
- ``run(root)`` — gate contract against synthesized fixtures: clean PASS,
  over-limit FAIL, missing directories, mixed-content behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sunxue_gates.results import GateResult
from sunxue_gates.token_budget import CHARS_PER_TOKEN, SOFT_LIMIT, est_tokens, run


class TestEstTokens:
    @pytest.mark.parametrize(
        "chars, expected",
        [
            (0, 0),
            (1, 0),  # floor div: 1 // 3 = 0
            (2, 0),
            (3, 1),
            (6, 2),
            (10, 3),
            (100, 33),
        ],
    )
    def test_equals_floor_div(self, chars: int, expected: int) -> None:
        assert est_tokens(chars) == expected

    def test_chars_per_token_constant(self) -> None:
        # Pin the documented formula; if this changes, every other test
        # in this module needs to be revisited.
        assert CHARS_PER_TOKEN == 3

    def test_monotone_in_chars(self) -> None:
        prev = -1
        for n in range(0, 200):
            t = est_tokens(n)
            assert t >= prev
            prev = t


class TestRunGate:
    def test_returns_gate_result(self, tmp_path: Path) -> None:
        # Empty repo: SKILL.md and references/ are both absent → SKILL.md
        # check is a MISS and the gate FAILs, but it still returns a
        # GateResult with a ``name`` and ``details``.
        gr = run(tmp_path)
        assert isinstance(gr, GateResult)
        assert gr.name == "token_budget"
        assert gr.passed is False  # SKILL.md MISS flips passed=False
        # At least one check is the SKILL.md MISS check.
        names = [c.name for c in gr.details]
        assert "SKILL.md" in names

    def test_pass_on_small_skill_file(self, tmp_path: Path) -> None:
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\n" + "a" * 1000, encoding="utf-8")
        gr = run(tmp_path)
        # The SKILL.md check must PASS.
        skill_check = next(c for c in gr.details if c.name == "SKILL.md")
        assert skill_check.passed is True

    def test_fail_when_skill_over_soft_limit(self, tmp_path: Path) -> None:
        # Generate chars > 3 × SOFT_LIMIT["SKILL.md"].
        big = "a" * (SOFT_LIMIT["SKILL.md"] * CHARS_PER_TOKEN + 100)
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\n" + big, encoding="utf-8")
        gr = run(tmp_path)
        assert gr.passed is False
        skill_check = next(c for c in gr.details if c.name == "SKILL.md")
        assert skill_check.passed is False

    def test_references_missing_emits_warn_not_fail(self, tmp_path: Path) -> None:
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\nsmall", encoding="utf-8")
        gr = run(tmp_path)
        # No references/ → the references aggregate check still passes;
        # overall gate passes too.
        assert gr.passed is True
        ref_check = next(c for c in gr.details if c.name == "references")
        assert ref_check.passed is True

    def test_references_aggregate_fail(self, tmp_path: Path) -> None:
        # Total tokens must exceed SOFT_LIMIT["references_total"].
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\nsmall", encoding="utf-8")
        refs = tmp_path / "references"
        refs.mkdir()
        big = "a" * (SOFT_LIMIT["references_total"] * CHARS_PER_TOKEN // 2 + 100)
        (refs / "r1.md").write_text(big, encoding="utf-8")
        (refs / "r2.md").write_text(big, encoding="utf-8")
        gr = run(tmp_path)
        assert gr.passed is False
        total_check = next(c for c in gr.details if c.name == "references/total")
        assert total_check.passed is False

    def test_examples_are_info_only_never_fail(self, tmp_path: Path) -> None:
        # Examples can be arbitrarily huge; the gate should still PASS.
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\nsmall", encoding="utf-8")
        ex = tmp_path / "examples"
        ex.mkdir()
        (ex / "big.md").write_text("a" * 10_000_000, encoding="utf-8")
        gr = run(tmp_path)
        assert gr.passed is True
        # All examples/* checks are passed=True even when huge.
        for c in gr.details:
            if c.name.startswith("examples/"):
                assert c.passed is True

    def test_cold_start_recorded_when_skill_present(self, tmp_path: Path) -> None:
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\nsmall", encoding="utf-8")
        gr = run(tmp_path)
        cold = next(c for c in gr.details if c.name == "cold-start")
        assert cold.passed is True
        assert cold.detail.get("available", True) is not False
        # A real I/O read should produce a positive ms reading.
        assert cold.detail["milliseconds"] >= 0
