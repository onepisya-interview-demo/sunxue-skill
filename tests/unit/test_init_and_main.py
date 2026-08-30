"""Unit tests for the package entry points (``sunxue_gates.__init__``
and ``sunxue_gates.__main__``).

Covers:
- ``run_all`` runs every gate in order and returns one GateResult per gate.
- ``run(gate_name, root)`` dispatches to the right gate and raises on
  unknown names.
- ``default_root`` points at the repo root (the directory that contains
  this package's ``src/``).
- ``main`` returns 0 when all gates PASS and 1 otherwise.

The repo carries seven gates (the seventh is ``lint_claims``, plan 1.2).
GATE_NAMES is the source of truth for the count.

The ``default_root`` / ``main`` tests resolve the repo root from the
package's own ``__file__`` — which is wrong under mutation testing
(mutmut copies the package source into ``mutants/src/``). They are
skipped when ``MUTANT_UNDER_TEST`` is set so that mutmut can complete
its stats phase.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sunxue_gates import GATE_NAMES, run, run_all
from sunxue_gates.__main__ import _ALL_CHAIN, _load_budgets, default_root, main

_SKIP_PATH_TESTS_UNDER_MUTMUT = "MUTANT_UNDER_TEST" in os.environ
skip_path = pytest.mark.skipif(
    _SKIP_PATH_TESTS_UNDER_MUTMUT,
    reason=(
        "These tests resolve paths from the package's __file__; under "
        "mutation testing mutmut copies the package source to mutants/, "
        "so the resolved root is no longer the real repo."
    ),
)


# ---------------------------------------------------------------------------
# run_all
# ---------------------------------------------------------------------------


class TestRunAll:
    def test_returns_one_result_per_gate(self, skill_root: Path) -> None:
        results = run_all(skill_root)
        assert len(results) == len(GATE_NAMES)
        names = [r.name for r in results]
        assert names == list(GATE_NAMES)

    def test_results_are_in_canonical_order(self, skill_root: Path) -> None:
        # The order in GATE_NAMES is the order of execution.
        results = run_all(skill_root)
        for got, want in zip(results, GATE_NAMES, strict=True):
            assert got.name == want


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


class TestRun:
    def test_dispatches_each_gate_by_name(self, skill_root: Path) -> None:
        for name in GATE_NAMES:
            gr = run(name, skill_root)
            assert gr.name == name

    def test_unknown_gate_raises(self, skill_root: Path) -> None:
        with pytest.raises(KeyError):
            run("not_a_real_gate", skill_root)


# ---------------------------------------------------------------------------
# default_root + main
# ---------------------------------------------------------------------------


class TestDefaultRoot:
    @skip_path
    def test_default_root_is_repo_root(self) -> None:
        # The repo root is the parent of the ``src/`` directory that holds
        # this package. So default_root() should be ``<repo>/..``'s
        # parent of ``src/sunxue_gates/__main__.py``.
        root = default_root()
        assert root.is_dir()
        # The repo root contains SKILL.md.
        assert (root / "SKILL.md").exists()


class TestMain:
    @skip_path
    def test_main_returns_zero_on_clean_repo(self) -> None:
        # Running main() with no argv against the repo root must exit 0.
        rc = main([])
        assert rc == 0

    @skip_path
    def test_main_passes_explicit_root(self, skill_root: Path) -> None:
        rc = main([str(skill_root)])
        assert rc == 0

    def test_main_returns_one_on_missing_repo(self, tmp_path: Path) -> None:
        rc = main([str(tmp_path)])
        # SKILL.md is missing → lint_structure / token_budget / injection_drill /
        # mutation_drill FAIL → overall FAIL.
        assert rc == 1


class TestLoadBudgets:
    """_load_budgets reads [tool.sunxue.budgets] with safe defaults."""

    def test_loads_from_real_pyproject(self, skill_root: Path) -> None:
        budgets = _load_budgets(skill_root)
        assert set(budgets.keys()) >= {"gates_all", "pytest", "mutmut"}
        assert budgets["gates_all"] == 60
        assert budgets["pytest"] == 5
        assert budgets["mutmut"] == 30

    def test_defaults_when_no_budgets_table(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0"\n', encoding="utf-8"
        )
        budgets = _load_budgets(tmp_path)
        assert budgets == {"gates_all": 60.0, "pytest": 5.0, "mutmut": 30.0}

    def test_defaults_when_pyproject_missing(self, tmp_path: Path) -> None:
        budgets = _load_budgets(tmp_path)
        assert budgets == {"gates_all": 60.0, "pytest": 5.0, "mutmut": 30.0}

    def test_defaults_when_pyproject_malformed(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("not = valid toml [[[", encoding="utf-8")
        budgets = _load_budgets(tmp_path)
        assert budgets == {"gates_all": 60.0, "pytest": 5.0, "mutmut": 30.0}

    def test_partial_table_falls_back_per_key(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            "[tool.sunxue.budgets]\npytest = 7\n", encoding="utf-8"
        )
        budgets = _load_budgets(tmp_path)
        assert budgets["pytest"] == 7
        assert budgets["gates_all"] == 60
        assert budgets["mutmut"] == 30

    def test_non_numeric_values_are_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[tool.sunxue.budgets]\npytest = "oops"\nmutmut = 25\n',
            encoding="utf-8",
        )
        budgets = _load_budgets(tmp_path)
        assert budgets["pytest"] == 5
        assert budgets["mutmut"] == 25


class TestChainHasBudgetKeys:
    """Every chain entry carries a budget_key that _load_budgets knows about."""

    def test_every_stage_has_a_known_budget_key(self, skill_root: Path) -> None:
        budgets = _load_budgets(skill_root)
        for label, _argv, budget_key in _ALL_CHAIN:
            assert budget_key in budgets, (
                f"stage {label!r} uses budget_key {budget_key!r} "
                "which is missing from [tool.sunxue.budgets]"
            )

    def test_chain_length_is_eight(self) -> None:
        assert len(_ALL_CHAIN) == 8

    def test_mutmut_stage_uses_mutmut_budget(self) -> None:
        labels = [entry[0] for entry in _ALL_CHAIN]
        assert "mutmut run" in labels
        for label, _argv, budget_key in _ALL_CHAIN:
            if label == "mutmut run":
                assert budget_key == "mutmut"

    def test_pytest_stages_use_pytest_budget(self) -> None:
        for label, _argv, budget_key in _ALL_CHAIN:
            if label.startswith("pytest"):
                assert budget_key == "pytest"
