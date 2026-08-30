"""Unit tests for ``sunxue_gates.token_budget``.

Covers:
- ``est_tokens`` — arithmetic + edge cases (negative input, zero).
- ``est_tokens_text`` — heuristic fallback + ``SUNXUE_PRECISE`` dispatch
  (plan 3.3).
- ``is_precise_active`` — env-switch + tiktoken-importable combinator.
- ``run(root)`` — gate contract against synthesized fixtures: clean PASS,
  over-limit FAIL, missing directories, mixed-content behavior.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sunxue_gates import token_budget
from sunxue_gates.results import GateResult
from sunxue_gates.token_budget import (
    CHARS_PER_TOKEN,
    SOFT_LIMIT,
    est_tokens,
    est_tokens_text,
    is_precise_active,
    run,
)


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


class TestEstTokensText:
    """est_tokens_text dispatches on SUNXUE_PRECISE env switch.

    Default mode is heuristic (chars / 3). The precise path requires both
    the env switch AND tiktoken importable; if either is missing, the
    heuristic is used and the returned mode tag makes the fallback visible.
    """

    def test_heuristic_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SUNXUE_PRECISE", raising=False)
        text = "hello world"
        tok, mode = est_tokens_text(text)
        # Heuristic: 11 // 3 = 3.
        assert tok == len(text) // CHARS_PER_TOKEN
        assert mode == "heuristic"

    def test_heuristic_when_env_set_but_tiktoken_unavailable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SUNXUE_PRECISE", "1")
        monkeypatch.setattr(token_budget, "_TIKTOKEN_ENCODING", None, raising=False)
        monkeypatch.setattr(token_budget, "_TIKTOKEN_IMPORT_ERROR", ImportError("x"), raising=False)
        tok, mode = est_tokens_text("hello world")
        assert tok == len("hello world") // CHARS_PER_TOKEN
        assert mode == "heuristic"

    def test_precise_when_env_set_and_tiktoken_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SUNXUE_PRECISE", "1")
        text = "hello world \u8fd9\u662f\u4e2d\u6587\u6d4b\u8bd5"
        tok, mode = est_tokens_text(text)
        assert mode == "precise"
        # cl100k_base produces a positive integer for any non-empty input.
        assert tok > 0
        # And it differs from the heuristic for Chinese-heavy text.
        assert tok != len(text) // CHARS_PER_TOKEN


class TestIsPreciseActive:
    """is_precise_active returns True iff switch + tiktoken both available."""

    def test_false_when_env_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SUNXUE_PRECISE", raising=False)
        assert is_precise_active() is False

    def test_false_when_env_set_but_tiktoken_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SUNXUE_PRECISE", "1")
        monkeypatch.setattr(token_budget, "_TIKTOKEN_ENCODING", None, raising=False)
        monkeypatch.setattr(token_budget, "_TIKTOKEN_IMPORT_ERROR", ImportError("x"), raising=False)
        assert is_precise_active() is False

    def test_false_when_env_set_to_other_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for value in ("0", "true", "yes", "", " 1"):
            monkeypatch.setenv("SUNXUE_PRECISE", value)
            assert is_precise_active() is False

    def test_true_when_env_set_to_one_and_tiktoken_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SUNXUE_PRECISE", "1")
        if token_budget._try_load_tiktoken() is None:
            pytest.skip("tiktoken not installed in this environment")
        assert is_precise_active() is True


class TestRunGateWithPrecisionSwitch:
    """run() honors the precision switch in user-facing output."""

    def test_default_emits_no_mode_header(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SUNXUE_PRECISE", raising=False)
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\nsmall", encoding="utf-8")
        gr = run(tmp_path)
        names = [c.name for c in gr.details]
        assert "mode" not in names

    def test_precise_emits_mode_header_and_tag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SUNXUE_PRECISE", "1")
        if token_budget._try_load_tiktoken() is None:
            pytest.skip("tiktoken not installed in this environment")
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\nsmall", encoding="utf-8")
        gr = run(tmp_path)
        names = [c.name for c in gr.details]
        assert "mode" in names
        mode_check = next(c for c in gr.details if c.name == "mode")
        assert mode_check.detail["mode"] == "precise"
        skill_check = next(c for c in gr.details if c.name == "SKILL.md")
        assert skill_check.detail["mode"] == "precise"

    def test_precise_env_without_tiktoken_falls_back_to_heuristic_with_tag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SUNXUE_PRECISE", "1")
        monkeypatch.setattr(token_budget, "_TIKTOKEN_ENCODING", None, raising=False)
        monkeypatch.setattr(token_budget, "_TIKTOKEN_IMPORT_ERROR", ImportError("x"), raising=False)
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\nsmall", encoding="utf-8")
        gr = run(tmp_path)
        names = [c.name for c in gr.details]
        assert "mode" not in names
        skill_check = next(c for c in gr.details if c.name == "SKILL.md")
        assert skill_check.detail["mode"] == "heuristic"
        assert "estimate=heuristic" in skill_check.message


class TestPreciseReferencesLoop:
    """The references loop in ``run()`` must exercise the precise branch too."""

    def test_precise_mode_processes_references(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # SUNXUE_PRECISE=1 with tiktoken available must drive the references
        # loop through ``est_tokens_text`` -- otherwise diff-cover flags the
        # new branch as uncovered and the gate fails.
        monkeypatch.setenv("SUNXUE_PRECISE", "1")
        if token_budget._try_load_tiktoken() is None:
            pytest.skip("tiktoken not installed in this environment")
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\nsmall", encoding="utf-8")
        refs = tmp_path / "references"
        refs.mkdir()
        (refs / "r1.md").write_text("hello world\n", encoding="utf-8")
        (refs / "r2.md").write_text("\u4e2d\u6587 test\n", encoding="utf-8")
        gr = run(tmp_path)
        # Per-reference check must carry the precise tag.
        ref_check = next(c for c in gr.details if c.name == "references/r1.md")
        assert ref_check.detail["mode"] == "precise"
        # Aggregate must also be precise.
        total_check = next(c for c in gr.details if c.name == "references/total")
        assert total_check.detail["mode"] == "precise"


class TestTiktokenImportErrorHandler:
    """The ImportError branch in ``_try_load_tiktoken`` is reachable in CI."""

    def test_records_error_when_tiktoken_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Reset the module-level cache so we can re-trigger the import path.
        monkeypatch.setattr(token_budget, "_TIKTOKEN_ENCODING", None, raising=False)
        monkeypatch.setattr(token_budget, "_TIKTOKEN_IMPORT_ERROR", None, raising=False)
        # Force an ImportError to flow through the except handler by stubbing
        # the import mechanism.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
            if name == "tiktoken" or name.startswith("tiktoken"):
                raise ImportError("no tiktoken")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        # Force cache miss so the except branch runs.
        token_budget._TIKTOKEN_ENCODING = None
        token_budget._TIKTOKEN_IMPORT_ERROR = None
        # Direct call to exercise the except arm.
        result = token_budget._try_load_tiktoken()
        assert result is None
        # And the cached error is now populated.
        assert token_budget._TIKTOKEN_IMPORT_ERROR is not None
