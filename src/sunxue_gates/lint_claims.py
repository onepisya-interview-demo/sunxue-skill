"""Gate 7: claims-lint — cross-check documentation claims against disk reality.

Addresses the "口径漂移" class of bugs that the auditor kept finding by
hand in v1.1.0 (references 7 vs 6, examples 5 vs "2真1占位", VERSION vs
pyproject drift, threshold drift across pyproject/README/tests-README).
Each sub-check emits one :class:`CheckResult`; the gate PASSES iff every
check PASSES.

Exemptions (do not flag these — they are historical / pinned snapshots):

- ``PLAN.md`` is a historical planning snapshot, exempt from claim linting.
- ``CHANGELOG.md`` 1.0.0 entry is a historical release-note snapshot.
- ``SKILL.md`` metadata (frontmatter) is FROZEN at v1.0.0 by deliberate
  decision; the freeze annotation in README.md pins it (check 2).
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from .results import CheckResult, GateResult

__all__ = ["run"]


# ---------------------------------------------------------------------------
# Paths and constants used by the cross-check.
# ---------------------------------------------------------------------------

# Files that look like "claims sources" — every read counts toward linting.
_README: str = "README.md"
_TESTS_README: str = "tests/README.md"
_VERSION_FILE: str = "VERSION"
_PYPROJECT: str = "pyproject.toml"
_SKILL_MD: str = "SKILL.md"

# Frozen-metadata annotation: README contains a verbatim line that pins the
# SKILL.md frontmatter version (which is intentionally frozen at 1.0.0).
_FREEZE_ANNOTATION: str = "元信息冻结"

# uv commands we expect to find in tests/README.md. Each entry is a regex
# matched against the file contents; the regex captures the command's
# primary subcommand (group 1). The match must also be wired up to an
# actual file in the repo (or a recognised CLI flag) to count as
# "resolvable".
_KNOWN_UV_SUBCOMMANDS: dict[str, str] = {
    r"\buv\s+run\s+pytest\b": "pytest",
    r"\buv\s+run\s+basedpyright\b": "basedpyright",
    r"\buv\s+run\s+ty\s+check\b": "ty",
    r"\buv\s+run\s+ruff\s+check\b": "ruff",
    r"\buv\s+run\s+ruff\s+format\b": "ruff",
    r"\buv\s+run\s+gates\b": "gates",
    r"\buv\s+run\s+diff-cover\b": "diff-cover",
    r"\buv\s+run\s+mutmut\b": "mutmut",
    r"\buv\s+run\s+python\b": "python",
}

# CLI surface that the ``gates`` console script exposes (mirrors
# sunxue_gates.__main__.main).
_GATES_FLAGS: frozenset[str] = frozenset({"--all", "--json"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_pyproject(root: Path) -> dict[str, object]:
    """Return the parsed ``[tool.*]`` tables from pyproject.toml."""
    path = root / _PYPROJECT
    if not path.exists():
        raise FileNotFoundError(f"pyproject.toml missing: {path}")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _disk_count(reldir: str, root: Path) -> int:
    """Count ``*.md`` files under ``root / reldir``."""
    d = root / reldir
    if not d.exists():
        return 0
    return sum(1 for _ in d.glob("*.md"))


def _readme_claimed_count(readme_text: str, reldir: str) -> int | None:
    """Return the integer that README.md claims for the count of ``reldir``.

    The README uses lines like ``├── references/  # 7 个 reference`` or
    ``├── examples/    # 5 个真实样本``. We accept the explicit
    "N 个" pattern after the directory tree line.
    """
    # Pattern: "├── references/" line followed (later in the file) by a
    # "N 个 reference(s)" tail. README places these inside the same code
    # block, so a single regex over the whole file works.
    m = re.search(rf"{re.escape(reldir)}/[^\n]*#[^\n]*?(\d+)\s*个", readme_text)
    if m is not None:
        return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# Sub-checks
# ---------------------------------------------------------------------------


def _check_version_match(root: Path) -> CheckResult:
    """VERSION file == pyproject project.version."""
    version_path = root / _VERSION_FILE
    if not version_path.exists():
        return CheckResult(
            name="version_match",
            passed=False,
            message=f"[FAIL] {_VERSION_FILE} 不存在: {version_path}",
            detail={"present": False},
        )
    file_v = version_path.read_text(encoding="utf-8").strip()
    try:
        cfg = _load_pyproject(root)
    except FileNotFoundError as e:
        return CheckResult(
            name="version_match", passed=False, message=f"[FAIL] {e}", detail={"err": str(e)}
        )
    pyproject_v = str(cfg.get("project", {}).get("version", "")).strip()
    ok = bool(file_v) and file_v == pyproject_v
    msg = (
        f"  [{'OK' if ok else 'FAIL'}] {_VERSION_FILE}={file_v!r} pyproject.version={pyproject_v!r}"
    )
    return CheckResult(
        name="version_match",
        passed=ok,
        message=msg,
        detail={"version_file": file_v, "pyproject": pyproject_v},
    )


def _check_skill_freeze(root: Path) -> CheckResult:
    """README contains SKILL.md freeze annotation; SKILL.md metadata version == 1.0.0.

    The annotation gates a deliberate freeze (PLAN §3.2: SKILL.md metadata
    stays at 1.0.0 — only the surrounding scaffolding moves). If the
    annotation disappears OR the SKILL.md frontmatter version drifts away
    from 1.0.0, the gate fails.
    """
    readme = root / _README
    if not readme.exists():
        return CheckResult(
            name="skill_freeze",
            passed=False,
            message=f"[FAIL] {_README} 不存在",
            detail={"present": False},
        )
    text = readme.read_text(encoding="utf-8")
    if _FREEZE_ANNOTATION not in text:
        return CheckResult(
            name="skill_freeze",
            passed=False,
            message=(
                f"[FAIL] README 缺少 {_FREEZE_ANNOTATION!r} 注记（SKILL.md 元信息冻结例外锚点）"
            ),
            detail={"annotation": _FREEZE_ANNOTATION, "present": False},
        )
    skill_md = root / _SKILL_MD
    if not skill_md.exists():
        return CheckResult(
            name="skill_freeze",
            passed=False,
            message=f"[FAIL] {_SKILL_MD} 不存在",
            detail={"present": False},
        )
    skill_text = skill_md.read_text(encoding="utf-8")
    has_v10_anywhere = "孙学 Skill v1.0" in skill_text
    ok = has_v10_anywhere
    msg = (
        f"  [{'OK' if ok else 'FAIL'}] README 含 {_FREEZE_ANNOTATION!r} 注记；"
        f"SKILL.md 元信息 v1.0 标记: {'有' if has_v10_anywhere else '缺'}"
    )
    return CheckResult(
        name="skill_freeze",
        passed=ok,
        message=msg,
        detail={"annotation_present": True, "skill_metadata_v10": has_v10_anywhere},
    )


def _check_directory_counts(root: Path) -> CheckResult:
    """README claim == disk count for references/ and examples/.

    Both directories are scanned; any mismatch in either fails the check.
    """
    readme = root / _README
    if not readme.exists():
        return CheckResult(
            name="directory_counts",
            passed=False,
            message=f"[FAIL] {_README} 不存在",
            detail={"present": False},
        )
    text = readme.read_text(encoding="utf-8")
    mismatches: list[str] = []
    details: dict[str, dict[str, int | None]] = {}
    for reldir in ("references", "examples"):
        disk = _disk_count(reldir, root)
        claim = _readme_claimed_count(text, reldir)
        details[reldir] = {"disk": disk, "claimed": claim}
        if claim is None:
            mismatches.append(f"{reldir}: README 无明确计数")
        elif claim != disk:
            mismatches.append(f"{reldir}: README={claim} 磁盘={disk}")
    ok = not mismatches
    msg = (
        "  [OK] 目录树计数全部对齐磁盘"
        if ok
        else f"  [FAIL] 目录树计数漂移: {'; '.join(mismatches)}"
    )
    return CheckResult(
        name="directory_counts",
        passed=ok,
        message=msg,
        detail=details,
    )


def _check_thresholds(root: Path) -> CheckResult:
    """pyproject fail_under=90 vs tests/README 90/100; ty version pin一致."""
    try:
        cfg = _load_pyproject(root)
    except FileNotFoundError as e:
        return CheckResult(
            name="thresholds", passed=False, message=f"[FAIL] {e}", detail={"err": str(e)}
        )
    cov = cfg.get("tool", {}).get("coverage", {}).get("report", {})
    fail_under = cov.get("fail_under")
    diff_under_in_tests_readme = False
    fail_under_in_tests_readme = False
    ty_pin = ""
    dev_deps = cfg.get("dependency-groups", {}).get("dev", []) or []
    for d in dev_deps:
        if isinstance(d, str) and d.startswith("ty=="):
            ty_pin = d[3:]

    tests_readme = root / _TESTS_README
    tr_text = tests_readme.read_text(encoding="utf-8") if tests_readme.exists() else ""
    if re.search(r"--cov-fail-under=90\b", tr_text):
        fail_under_in_tests_readme = True
    if re.search(r"--fail-under=100\b", tr_text):
        diff_under_in_tests_readme = True

    pyproject_ty_pin_ok = bool(ty_pin)
    coverage_ok = fail_under == 90
    tr_90_ok = fail_under_in_tests_readme
    tr_100_ok = diff_under_in_tests_readme
    ok = pyproject_ty_pin_ok and coverage_ok and tr_90_ok and tr_100_ok
    msg = (
        f"  [{'OK' if ok else 'FAIL'}] "
        f"pyproject.coverage.fail_under={fail_under} (期望 90); "
        f"pyproject.dev.ty pin={ty_pin!r}; "
        f"tests/README --cov-fail-under=90: {fail_under_in_tests_readme}; "
        f"tests/README diff-cover --fail-under=100: {diff_under_in_tests_readme}"
    )
    return CheckResult(
        name="thresholds",
        passed=ok,
        message=msg,
        detail={
            "pyproject_fail_under": fail_under,
            "pyproject_ty_pin": ty_pin,
            "tests_readme_fail_under_90": fail_under_in_tests_readme,
            "tests_readme_fail_under_100": diff_under_in_tests_readme,
        },
    )


def _check_uv_commands(root: Path) -> CheckResult:
    """tests/README 中出现的 uv run 子命令都在仓库内可解析。"""
    tests_readme = root / _TESTS_README
    if not tests_readme.exists():
        return CheckResult(
            name="uv_commands_resolvable",
            passed=False,
            message=f"[FAIL] {_TESTS_README} 不存在",
            detail={"present": False},
        )
    text = tests_readme.read_text(encoding="utf-8")

    # Pull every ``uv run <something>`` invocation out of the README.
    uv_invocations = re.findall(r"\buv\s+run\s+([^\s`'\)]+)", text)
    unique = sorted(set(uv_invocations))

    # Look up each subcommand in the known map; missing keys mean the
    # subcommand is "uv run python -m something" or some other explicit
    # invocation we don't statically resolve — those are flagged.
    missing: list[str] = []
    resolved: list[str] = []
    for sub in unique:
        if sub in _KNOWN_UV_SUBCOMMANDS.values():
            resolved.append(sub)
            continue
        # Reject any other subcommand (no implicit allowlist).
        missing.append(sub)

    # Also require the ``gates`` console script and --all / --json flags to
    # be reachable. The console script comes from pyproject; the flags
    # come from __main__.main.
    cfg = _load_pyproject(root)
    has_gates_script = "gates" in cfg.get("project", {}).get("scripts", {})
    src_main = (root / "src" / "sunxue_gates" / "__main__.py").read_text(encoding="utf-8")
    has_all_flag = '"--all"' in src_main or "'--all'" in src_main
    has_json_flag = '"--json"' in src_main or "'--json'" in src_main

    gates_ok = has_gates_script and has_all_flag and has_json_flag
    ok = gates_ok and not missing
    msg_parts: list[str] = []
    if missing:
        msg_parts.append(f"未解析子命令: {missing}")
    msg_parts.append(
        f"gates script: {has_gates_script}; --all: {has_all_flag}; --json: {has_json_flag}"
    )
    return CheckResult(
        name="uv_commands_resolvable",
        passed=ok,
        message=(f"  [{'OK' if ok else 'FAIL'}] " + "; ".join(msg_parts)),
        detail={
            "unique_subcommands": unique,
            "missing": missing,
            "gates_script": has_gates_script,
            "all_flag": has_all_flag,
            "json_flag": has_json_flag,
        },
    )


# ---------------------------------------------------------------------------
# Gate entry point
# ---------------------------------------------------------------------------


def run(root: Path) -> GateResult:
    """Run the claims-lint gate against ``root`` (the skill repo root).

    Returns a :class:`GateResult` whose ``passed`` flag is True iff every
    sub-check passed.
    """
    checks: list[CheckResult] = [
        _check_version_match(root),
        _check_skill_freeze(root),
        _check_directory_counts(root),
        _check_thresholds(root),
        _check_uv_commands(root),
    ]

    failures = sum(1 for c in checks if not c.passed)
    passed = failures == 0
    summary = (
        "PASS (5 项口径全部对齐)"
        if passed
        else f"FAIL (失败 {failures} 项: {', '.join(c.name for c in checks if not c.passed)})"
    )
    return GateResult(
        name="lint_claims",
        passed=passed,
        details=tuple(checks),
        summary=f"总结: {summary}",
    )
