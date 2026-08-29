"""Six-layer gate harness for the sunxue skill.

Public API:
- :func:`run_all` — execute all six gates against a root directory.
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

# Import gate modules lazily so callers can opt into one gate without paying for all six.
from . import (
    injection_drill,
    lint_structure,
    mutation_drill,
    regression_output,
    scan_security,
    token_budget,
)

# Execution order matches the original test/ scripts.
GATES = (
    lint_structure,
    scan_security,
    regression_output,
    token_budget,
    injection_drill,
    mutation_drill,
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
