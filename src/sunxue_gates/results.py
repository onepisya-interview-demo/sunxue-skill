"""Result types shared across all six gates.

Each gate returns a :class:`GateResult` from its ``run(root: Path)`` entry point.
Gates never raise on a normal FAIL — instead they collect structured details
and set ``passed = False``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["CheckResult", "GateResult", "merge_passed"]


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single sub-check inside a gate.

    Attributes:
        name: Short label of the sub-check (e.g. ``'frontmatter.name'``).
        passed: Whether this sub-check succeeded.
        message: Human-readable line that the original scripts printed.
        detail: Optional structured payload (counts, sizes, …) for callers /
            future unit tests. ``Any`` because each gate carries different
            shapes; keep keys stable per gate.
    """

    name: str
    passed: bool
    message: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GateResult:
    """Outcome of one gate run.

    Attributes:
        name: Human-readable gate name (e.g. ``'lint_structure'``).
        passed: True iff every recorded :class:`CheckResult` passed.
        details: All sub-checks in execution order.
        summary: One-line summary printed by the original scripts.
    """

    name: str
    passed: bool
    details: tuple[CheckResult, ...]
    summary: str

    @property
    def failure_count(self) -> int:
        return sum(1 for d in self.details if not d.passed)


def merge_passed(results: list[bool]) -> bool:
    """Return ``True`` iff every value in ``results`` is true. Empty input is True."""
    return all(results)
