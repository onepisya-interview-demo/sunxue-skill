"""CLI flag canonical set for the ``gates`` console script.

v1.3.0 cluster A F8: single source of truth for the CLI flag set. The
function lives in its own module (not ``__init__.py``) so that gate
modules can import it without creating a circular import back through
``sunxue_gates/__init__.py``.

``__init__.py`` re-exports :func:`get_gates_flags` for backward-compat
with code that already does ``from sunxue_gates import get_gates_flags``.
"""

from __future__ import annotations


def get_gates_flags() -> frozenset[str]:
    """Return the canonical set of CLI flags exposed by the ``gates`` console script.

    v1.3.0 cluster A F8: single source of truth for the CLI flag set.
    ``__main__.main`` consumes this set for flag-membership checks
    (unknown-flag rejection + un-wired-flag alarm, wired v1.3.1 per
    audit-v4 N4), and the lint_claims ast-check keeps ``--all`` /
    ``--json`` literals in ``__main__`` aligned with it. The return
    type is a frozenset for O(1) membership tests.
    """
    return frozenset({"--all", "--json"})
