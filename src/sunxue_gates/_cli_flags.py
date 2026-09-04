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
    ``__main__.main`` and ``lint_claims._GATES_FLAGS`` both import from
    here, so the dict-vs-set drift that the v1.2.0 audit caught cannot
    happen again. The return type is a frozenset for O(1) membership
    tests in the ast-based detection path.
    """
    return frozenset({"--all", "--json"})
