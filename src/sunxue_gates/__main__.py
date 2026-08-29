"""Console entry point: ``python -m sunxue_gates`` or the ``gates`` script.

Runs all six gates serially against the repo root (the parent directory of
``src/sunxue_gates/__main__.py``) and exits 0 iff every gate PASSES. Preserves
the original ``PASS = 0 / FAIL = 1`` contract.
"""

from __future__ import annotations

import sys
from pathlib import Path

from . import GATE_NAMES, run_all

__all__ = ["main", "default_root"]


def default_root() -> Path:
    """Return the repo root: parent of this package's source directory."""
    # src/sunxue_gates/__main__.py  →  src/sunxue_gates  →  src  →  repo root
    return Path(__file__).resolve().parent.parent.parent


def main(argv: list[str] | None = None) -> int:
    """Run all gates against the repo root; return the shell exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]).resolve() if args else default_root()

    print("=" * 70)
    print(f"sunxue gates — 六层门禁 ({len(GATE_NAMES)} 个)")
    print("=" * 70)
    print(f"skill 根目录: {root}")

    results = run_all(root)

    failed: list[str] = []
    for result in results:
        print()
        print(f"=== {result.name} ===")
        for detail in result.details:
            print(detail.message)
        print(f"{result.summary}")
        if not result.passed:
            failed.append(result.name)

    print()
    print("=" * 70)
    if failed:
        print(f"总结: FAIL ({len(failed)}/{len(results)} 失败: {', '.join(failed)})")
        return 1
    print(f"总结: PASS ({len(results)}/{len(results)} 通过)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
