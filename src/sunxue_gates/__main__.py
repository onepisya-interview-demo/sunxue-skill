"""Console entry point: ``python -m sunxue_gates`` or the ``gates`` script.

Default (no flag): run the seven in-process Python gates serially against
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

The mutmut stage picks up ``PYTEST_ADDOPTS`` (and other pytest-arg
overrides) from
``[tool.mutmut] pytest_add_cli_args_test_selection`` in ``pyproject.toml``
(mutmut 3.7.x documented key). Every invocation path (``uv run mutmut
run`` directly, ``gates --all`` here, CI) gets the same coverage.
``uv run pytest`` and the in-process gate chain still run every test
file; the ignore only affects mutmut pytest invocations.

Performance budgets (plan 3.4) are read from ``[tool.sunxue.budgets]`` in
``pyproject.toml`` (keys: ``gates_all``, ``pytest``, ``mutmut``; seconds).
If a stage exceeds its budget, the chain fails with a budget-exceeded
message and the operator gets a stage-table row marked ``OVER``.

``gates --json`` prints the seven ``GateResult`` objects as a JSON array (one
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
import tomllib
from pathlib import Path

from . import GATE_NAMES, run_all

__all__ = ["main", "default_root"]


def default_root() -> Path:
    """Return the repo root: parent of this package's source directory."""
    # src/sunxue_gates/__main__.py  →  src/sunxue_gates  →  src  →  repo root
    return Path(__file__).resolve().parent.parent.parent


# Eight-stage acceptance chain (PLAN §1.3). Each entry:
#   (label, argv, budget_key)
# ``budget_key`` is one of the keys in ``[tool.sunxue.budgets]``
# (``gates_all`` / ``pytest`` / ``mutmut``); ``gates_all`` is the default for
# stages that don't have a dedicated budget. Args are run verbatim through
# ``subprocess.run``; cwd is the repo root.
_ALL_CHAIN: tuple[tuple[str, tuple[str, ...], str], ...] = (
    ("ruff check", ("ruff", "check", "."), "gates_all"),
    ("ruff format --check", ("ruff", "format", "--check", "."), "gates_all"),
    ("basedpyright", ("basedpyright",), "gates_all"),
    ("ty check .", ("ty", "check", "."), "gates_all"),
    ("pytest", ("pytest",), "pytest"),
    (
        "pytest --cov (>=90%)",
        (
            "pytest",
            "--cov=sunxue_gates",
            "--cov-branch",
            "--cov-report=xml",
            "--cov-fail-under=90",
        ),
        "pytest",
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
        "gates_all",
    ),
    ("mutmut run", ("mutmut", "run"), "mutmut"),
)


def _load_budgets(root: Path) -> dict[str, float]:
    """Read ``[tool.sunxue.budgets]`` from ``root/pyproject.toml``.

    Missing keys fall back to safe defaults (plan 3.4): 60s for the overall
    chain, 5s for pytest, 30s for mutmut. The defaults are identical to
    ``pyproject.toml`` so a missing table does not silently relax the gates.
    """
    defaults: dict[str, float] = {"gates_all": 60.0, "pytest": 5.0, "mutmut": 45.0}
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return defaults
    try:
        cfg = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):  # pragma: no cover - defensive
        return defaults
    raw = cfg.get("tool", {}).get("sunxue", {}).get("budgets", {})
    out = dict(defaults)
    if isinstance(raw, dict):
        for k, v in raw.items():
            try:
                out[str(k)] = float(v)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
    return out


def _run_chain(root: Path) -> int:
    """Execute the eight-stage acceptance chain; stop at first failure.

    Each stage is timed and compared to the matching budget from
    ``[tool.sunxue.budgets]`` (plan 3.4). A stage that exceeds its budget
    is recorded as ``OVER`` in the stage table; the chain fails with a
    ``budget-exceeded`` exit code if any budget was violated, even if the
    stage itself exited cleanly. ``mutants/`` is removed after the chain
    in all cases.
    """
    budgets = _load_budgets(root)
    budget_summary = ", ".join(f"{k}={int(v)}s" for k, v in sorted(budgets.items()))
    print("=" * 78)
    print(f"sunxue gates --all ({len(_ALL_CHAIN)} stages; budgets: {budget_summary})")
    print("=" * 78)
    print(f"repo root: {root}")
    print()

    rows: list[tuple[str, str, str, str]] = []
    overall_start = time.perf_counter()
    cumulative = 0.0
    failed_stage: tuple[str, int] | None = None
    budget_violations: list[tuple[str, float, float]] = []  # (label, elapsed, budget)

    for index, (label, argv, budget_key) in enumerate(_ALL_CHAIN, start=1):
        stage_start = time.perf_counter()
        # Stream child stdout/stderr straight to the parent terminal so the
        # operator sees the same output as running the command by hand.
        # ``PYTEST_ADDOPTS`` and other pytest-arg overrides for the mutmut
        # stage come from ``[tool.mutmut] pytest_add_cli_args_test_selection``
        # in ``pyproject.toml`` (mutmut 3.7.x documented key). We do not
        # special-case argv here; the env override lives in config so
        # every invocation path (``uv run mutmut run`` directly,
        # ``gates --all`` here, CI) gets the same coverage.
        proc = subprocess.run(argv, cwd=str(root))  # noqa: S603 — argv is a fixed tuple
        stage_elapsed = time.perf_counter() - stage_start
        cumulative += stage_elapsed
        # Compare elapsed to the per-stage budget. The ``gates_all`` budget
        # is also enforced against the cumulative wall clock at the end.
        stage_budget = budgets.get(budget_key, budgets.get("gates_all", 60.0))
        over_budget = stage_elapsed > stage_budget
        if proc.returncode == 0 and over_budget:
            budget_violations.append((label, stage_elapsed, stage_budget))
        if proc.returncode != 0:
            status = f"FAIL(exit={proc.returncode})"
            failed_stage = (label, proc.returncode)
        elif over_budget:
            status = f"OVER ({stage_elapsed:.1f}s > {stage_budget:.0f}s)"
        else:
            status = "PASS"
        rows.append((str(index), label, f"{stage_elapsed:6.2f}s", status))
        if proc.returncode != 0:
            break

    total = time.perf_counter() - overall_start
    # Enforce ``gates_all`` against the cumulative wall clock as well — the
    # whole-chain budget is the union of all stage budgets in spirit.
    gates_all_budget = budgets.get("gates_all", 60.0)
    if failed_stage is None and total > gates_all_budget:
        budget_violations.append(("total", total, gates_all_budget))

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
    print(f"{'#':>3}  {'stage':<28}  {'time':>8}  {'status':<24}")
    print("-" * 78)
    for n, label, t, status in rows:
        print(f"{n:>3}  {label:<28}  {t:>8}  {status:<24}")
    print("-" * 78)
    print(f"{'total':<32}  {total:>8.2f}s")
    print("=" * 78)

    if failed_stage is not None:
        label, code = failed_stage
        print(f"总结: FAIL — stage {label!r} exited with code {code}")
        return code if code != 0 else 1
    if budget_violations:
        # Exit code 75 is EX_TEMPFAIL on BSD/macOS — used here as a sentinel
        # for "budget exceeded but stages themselves were green". CI can
        # surface this distinctly from a test FAIL.
        print("总结: FAIL — budget exceeded:")
        for label, elapsed, budget in budget_violations:
            print(f"  - {label}: {elapsed:.2f}s > {budget:.0f}s")
        return 75
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
    """Run the seven in-process gates; emit JSON array of GateResults."""
    results = run_all(root)
    payload = [_gate_result_to_dict(gr) for gr in results]
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0 if all(gr.passed for gr in results) else 1


def main(argv: list[str] | None = None) -> int:
    """Dispatch on flags:

    - ``--all`` → eight-stage shell chain (PLAN §1.3)
    - ``--json`` → seven-gate results as JSON array
    - default → legacy seven-gate serial behavior (byte-compatible)

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
                "\n  --json  print seven GateResults as JSON (machine-readable)",
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

    # Seven-gate serial path: walk every module in GATES, exit 0 iff every
    # gate PASSES. The banner says "七层" to reflect the new claims-lint
    # gate (plan 1.2) added in v1.2.0.
    print("=" * 70)
    print(f"sunxue gates — 七层门禁 ({len(GATE_NAMES)} 个)")
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
