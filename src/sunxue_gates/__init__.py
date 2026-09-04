"""Eight-layer gate harness for the sunxue skill.

Public API:
- :func:`run_all` — execute all eight gates against a root directory.
- :func:`run` — execute a single gate by name.
- :class:`~sunxue_gates.results.GateResult` / :class:`~sunxue_gates.results.CheckResult`
- Individual gate modules (``lint_structure``, ``scan_security``, …) are also importable
  for direct unit testing.
"""

from __future__ import annotations

from pathlib import Path

from .results import CheckResult, GateResult

__all__ = [
    "CheckResult",
    "GateResult",
    "GATES",
    "GATE_NAMES",
    "run",
    "run_all",
]

# Gate modules are imported eagerly below so that :data:`GATES` is a concrete
# module tuple ready for ``run_all`` / ``run`` lookups. Tests can still import
# a single gate module directly (e.g. ``from sunxue_gates import lint_structure``)
# without paying for the rest; the import side-effect here is module loading,
# not gate execution.
from . import (
    injection_drill,
    lint_claims,
    lint_pii,
    lint_structure,
    mutation_drill,
    regression_output,
    scan_security,
    token_budget,
)

# Execution order matches the original test/ scripts; lint_claims (gate 7)
# is appended at the end since it is a documentation / cross-check gate
# that does not touch the skill body. lint_pii is appended as gate 8 —
# it is a documentation-only PII guard that runs after every content
# gate has had its say, so a hit here points unambiguously at a leak
# rather than at a side-effect of another gate's pass/fail message.
GATES = (
    lint_structure,
    scan_security,
    regression_output,
    token_budget,
    injection_drill,
    mutation_drill,
    lint_claims,
    lint_pii,
)

GATE_NAMES: tuple[str, ...] = tuple(m.__name__.split(".")[-1] for m in GATES)


def run(gate_name: str, root: Path) -> GateResult:
    """Run a single gate by module name (e.g. ``'lint_structure'``) against ``root``."""
    for module in GATES:
        if module.__name__.endswith(gate_name):
            return module.run(root)
    raise KeyError(f"unknown gate: {gate_name!r}; known: {GATE_NAMES}")


def run_all(root: Path) -> list[GateResult]:
    """Execute every gate in :data:`GATES` order; return all :class:`GateResult`s."""
    return [m.run(root) for m in GATES]
