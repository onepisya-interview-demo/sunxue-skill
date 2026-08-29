"""Live regression: every gate must PASS against the current repo.

This pins the contract that used to be the exit-code of the original
stdlib scripts. Each gate's ``run(root)`` returns ``passed = True``.

The repo carries seven gates (the seventh is ``lint_claims``, plan 1.2);
GATE_NAMES drives the parametrize list so this module stays in sync with
``sunxue_gates.GATES`` automatically.

NOTE: This test runs the gates against the actual skill repo on disk.
Under mutation testing, mutmut copies the test tree into ``mutants/``,
so the resolved path no longer points at the real repo. We skip the
whole module when ``MUTANT_UNDER_TEST`` is set — the per-mutation
correctness of every gate is already exercised by the unit tests in
``tests/unit/`` and the property tests in ``tests/property/``.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from sunxue_gates import GATE_NAMES, run

_SKIP_LIVE_UNDER_MUTMUT = "MUTANT_UNDER_TEST" in os.environ
pytestmark = pytest.mark.skipif(
    _SKIP_LIVE_UNDER_MUTMUT,
    reason=(
        "test_gates_live runs against the real repo root; under mutation "
        "testing the test tree is copied to mutants/ so the resolved "
        "root is no longer the real repo. Unit + property tests already "
        "exercise every gate's per-mutation correctness."
    ),
)


@pytest.mark.parametrize("gate_name", list(GATE_NAMES))
def test_each_gate_passes_on_repo_root(gate_name: str, skill_root: Path) -> None:
    gr = run(gate_name, skill_root)
    assert gr.passed is True, (
        f"gate {gate_name!r} should PASS on the repo root but failed; "
        f"failing checks: {[c.name for c in gr.details if not c.passed]}\n"
        f"messages:\n" + "\n".join(c.message for c in gr.details if not c.passed)
    )


def test_lint_structure_emits_skill_and_references(skill_root: Path) -> None:
    from sunxue_gates import lint_structure

    gr = lint_structure.run(skill_root)
    names = {c.name for c in gr.details}
    # The SKILL.md header check is always emitted.
    assert any(n.startswith("SKILL.md") for n in names)
    # At least one reference file check is emitted (the repo has 7 references).
    assert any(n.startswith("references/") for n in names)


def test_token_budget_emits_cold_start(skill_root: Path) -> None:
    from sunxue_gates import token_budget

    gr = token_budget.run(skill_root)
    names = {c.name for c in gr.details}
    assert "cold-start" in names
