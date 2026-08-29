"""Console entry point: ``python -m sunxue_gates`` or the ``gates`` script.

Default (no flag): run the legacy six in-process Python gates serially against
the repo root (parent of ``src/sunxue_gates/__main__.py``); exit 0 iff every
gate PASSES. Preserves the original ``PASS = 0 / FAIL = 1`` contract.

``gates --all`` runs the full eight-command acceptance chain as subprocesses
(ruff check, ruff format --check, basedpyright, ty check ., pytest, pytest
--cov=... --cov-fail-under=90, diff-cover coverage.xml --compare-branch
gate-baseline --fail-under=100, mutmut run). Each stage is timed; the chain
stops at the first failure (exit code surfaced verbatim); a stage table and
total wall time are printed at the end; the ``mutants/`` directory created by
mutmut is removed afterwards. Useful for CI and the one-command local
acceptance check described in PLAN §1.3.

``gates --json`` prints the six ``GateResult`` objects as a JSON array (one
object per gate: ``name``, ``passed``, ``summary``, ``failure_count``,
``details``) — machine-readable output for CI dashboards. Exit code mirrors
the legacy default (0 iff all gates pass).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import GATE_NAMES, run_all

__all__ = ["main", "default_root"]


def default_root() -> Path:
    """Return the repo root: parent of this package's source directory."""
    # src/sunxue_gates/__main__.py  →  src/sunxue_gates  →  src  →  repo root
    return Path(__file__).resolve().parent.parent.parent


# Eight-stage acceptance chain (PLAN §1.3). Each entry: (label, argv).
# Args are run verbatim through ``subprocess.run``; cwd is the repo root.
_ALL_CHAIN: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ruff check", ("ruff", "check", ".")),
    ("ruff format --check", ("ruff", "format", "--check", ".")),
    ("basedpyright", ("basedpyright",)),
    ("ty check .", ("ty", "check", ".")),
    ("pytest", ("pytest",)),
    (
        "pytest --cov (>=90%)",
        (
            "pytest",
            "--cov=sunxue_gates",
            "--cov-branch",
            "--cov-report=xml",
            "--cov-fail-under=90",
        ),
    ),
    (
        "diff-cover (>=100%)",
        (
            "diff-cover",
            "coverage.xml",
            "--compare-branch",
            "gate-baseline",
            "--fail-under=100",
        ),
    ),
    ("mutmut run", ("mutmut", "run")),
)


def _run_chain(root: Path) -> int:
    """Execute the eight-stage acceptance chain; stop at first failure."""
    print("=" * 78)
    print(f"sunxue gates --all ({len(_ALL_CHAIN)} stages)")
    print("=" * 78)
    print(f"repo root: {root}")
    print()

    rows: list[tuple[str, str, str, str]] = []
    overall_start = time.perf_counter()
    cumulative = 0.0
    failed_stage: tuple[str, int] | None = None

    for index, (label, argv) in enumerate(_ALL_CHAIN, start=1):
        stage_start = time.perf_counter()
        # Stream child stdout/stderr straight to the parent terminal so the
        # operator sees the same output as running the command by hand.
        proc = subprocess.run(argv, cwd=str(root))  # noqa: S603 — argv is a fixed tuple
        stage_elapsed = time.perf_counter() - stage_start
        cumulative += stage_elapsed
        status = "PASS" if proc.returncode == 0 else f"FAIL(exit={proc.returncode})"
        rows.append((str(index), label, f"{stage_elapsed:6.2f}s", status))
        if proc.returncode != 0:
            failed_stage = (label, proc.returncode)
            break

    total = time.perf_counter() - overall_start

    # Cleanup: remove mutants/ directory if mutmut created it. Done after the
    # chain (success or failure) so the post-condition always holds.
    mutants_dir = root / "mutants"
    if mutants_dir.exists():
        shutil.rmtree(mutants_dir, ignore_errors=True)

    # Stage table.
    print()
    print("=" * 78)
    print("Stage table")
    print("-" * 78)
    print(f"{'#':>3}  {'stage':<28}  {'time':>8}  {'status':<16}")
    print("-" * 78)
    for n, label, t, status in rows:
        print(f"{n:>3}  {label:<28}  {t:>8}  {status:<16}")
    print("-" * 78)
    print(f"{'total':<32}  {total:>8.2f}s")
    print("=" * 78)

    if failed_stage is not None:
        label, code = failed_stage
        print(f"总结: FAIL — stage {label!r} exited with code {code}")
        return code if code != 0 else 1
    print(f"总结: PASS — {len(_ALL_CHAIN)}/{len(_ALL_CHAIN)} stages green in {total:.2f}s")
    return 0


def _gate_result_to_dict(gr) -> dict:
    """Convert one GateResult to a JSON-serializable dict (PLAN §1.3 --json)."""
    return {
        "name": gr.name,
        "passed": gr.passed,
        "summary": gr.summary,
        "failure_count": gr.failure_count,
        "details": [
            {
                "name": c.name,
                "passed": c.passed,
                "message": c.message,
                "detail": c.detail,
            }
            for c in gr.details
        ],
    }


def _emit_json(root: Path) -> int:
    """Run the six legacy in-process gates; emit JSON array of GateResults."""
    results = run_all(root)
    payload = [_gate_result_to_dict(gr) for gr in results]
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0 if all(gr.passed for gr in results) else 1


def main(argv: list[str] | None = None) -> int:
    """Dispatch on flags:

    - ``--all`` → eight-stage shell chain (PLAN §1.3)
    - ``--json`` → six-gate results as JSON array
    - default → legacy six-gate serial behavior (byte-compatible)

    A positional argument selects the repo root (default: ``default_root()``).
    """
    args = list(sys.argv[1:] if argv is None else argv)

    # Flag parsing — order-independent; flags come before the optional root path.
    chain = False
    as_json = False
    positional: list[str] = []
    for a in args:
        if a == "--all":
            chain = True
        elif a == "--json":
            as_json = True
        elif a in ("-h", "--help"):
            print(
                "usage: gates [--all | --json] [ROOT]",
                "\n  --all   run the 8-stage acceptance chain (CI / one-command local)",
                "\n  --json  print six GateResults as JSON (machine-readable)",
                "\n  ROOT    repo root (default: parent of src/sunxue_gates)",
                sep="\n",
            )
            return 0
        elif a.startswith("-"):
            print(f"unknown flag: {a}", file=sys.stderr)
            return 2
        else:
            positional.append(a)

    root = Path(positional[0]).resolve() if positional else default_root()

    if chain:
        return _run_chain(root)
    if as_json:
        return _emit_json(root)

    # Legacy six-gate serial path — keep this branch byte-compatible with
    # the v1.1.0 contract: print the same banners, walk the same six gates,
    # exit 0 iff every gate PASSES.
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
