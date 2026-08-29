"""Gate 1: structural lint for skill files.

Checks per-file:
- ``SKILL.md`` must carry a YAML frontmatter with ``name`` and ``description``.
- File size must not exceed the per-kind limit (25_000 for SKILL, 12_000 for refs).
- ``SKILL.md`` must hit all three required section groups.
- ``## `` heading count must not exceed :data:`MAX_H2_HEADINGS`.

Returns a :class:`GateResult` whose ``passed`` flag is True iff all sub-checks
across all files passed.
"""

from __future__ import annotations

import re
from pathlib import Path

from .parsing import classify_doc, count_h2, parse_frontmatter
from .results import CheckResult, GateResult

__all__ = [
    "run",
    "REQUIRED_FRONTMATTER",
    "REQUIRED_SECTION_GROUPS",
    "SIZE_LIMITS",
    "MAX_H2_HEADINGS",
]

REQUIRED_FRONTMATTER: tuple[str, ...] = ("name", "description")

# Three required section groups: matched as raw regex, any alternation hit suffices.
REQUIRED_SECTION_GROUPS: tuple[str, ...] = (
    "第一原则|心法|写作引擎|判断引擎|方法论",
    "触发词|触发|适用于|命中",
    "红线|铁律|禁令|绝对禁令|不要",
)

SIZE_LIMITS: dict[str, int] = {
    "SKILL": 25_000,
    "reference": 12_000,
}

MAX_H2_HEADINGS: int = 80


def _check_one(label: str, path: Path) -> tuple[list[CheckResult], bool]:
    """Run all sub-checks on a single file; return (checks, present)."""
    if not path.exists():
        return (
            [CheckResult(name=label, passed=False, message=f"[MISS] {label}: {path} 不存在")],
            False,
        )

    text = path.read_text(encoding="utf-8")
    size = len(text)
    kind = classify_doc(path)
    limit = SIZE_LIMITS[kind]

    header = f"=== {label} ({kind}, {size} chars, 上限 {limit}) ==="
    checks: list[CheckResult] = [CheckResult(name=f"{label}.header", passed=True, message=header)]

    # 1) Frontmatter (SKILL only)
    if kind == "SKILL":
        fm = parse_frontmatter(text)
        if fm is None:
            checks.append(
                CheckResult(
                    name=f"{label}.frontmatter",
                    passed=False,
                    message="  [FAIL] 缺 YAML frontmatter (--- 块)",
                    detail={"present": False},
                )
            )
        else:
            checks.append(
                CheckResult(
                    name=f"{label}.frontmatter",
                    passed=True,
                    message="  [OK] frontmatter 已解析",
                    detail={"present": True, "keys": sorted(fm.keys())},
                )
            )
            for key in REQUIRED_FRONTMATTER:
                value = fm.get(key, "")
                ok = bool(str(value).strip())
                preview = str(value)[:60].replace("\n", " ")
                suffix = "..." if len(str(value)) > 60 else ""
                tag = "OK" if ok else "FAIL"
                msg = f"  [{tag}] frontmatter.{key} = {preview}{suffix}"
                checks.append(
                    CheckResult(
                        name=f"{label}.frontmatter.{key}",
                        passed=ok,
                        message=msg,
                        detail={"value_preview": preview},
                    )
                )

    # 2) Size
    size_ok = size <= limit
    size_tag = "OK" if size_ok else "FAIL"
    size_op = "<=" if size_ok else ">"
    checks.append(
        CheckResult(
            name=f"{label}.size",
            passed=size_ok,
            message=f"  [{size_tag}] 体积 {size} {size_op} {limit}",
            detail={"size": size, "limit": limit, "overflow": max(0, size - limit)},
        )
    )

    # 3) Required sections (SKILL only)
    if kind == "SKILL":
        for group in REQUIRED_SECTION_GROUPS:
            hit = re.search(group, text) is not None
            checks.append(
                CheckResult(
                    name=f"{label}.section",
                    passed=hit,
                    message=f"  [{'OK' if hit else 'FAIL'}] 必含章节命中 /{group}/"
                    if hit
                    else f"  [FAIL] 必含章节未命中 /{group}/",
                    detail={"group": group},
                )
            )

    # 4) Heading granularity
    h2_count = count_h2(text)
    h2_ok = h2_count <= MAX_H2_HEADINGS
    h2_tag = "OK" if h2_ok else "FAIL"
    h2_op = "<=" if h2_ok else ">"
    checks.append(
        CheckResult(
            name=f"{label}.h2_count",
            passed=h2_ok,
            message=f"  [{h2_tag}] 二级标题数 {h2_count} {h2_op} {MAX_H2_HEADINGS}",
            detail={"h2_count": h2_count, "limit": MAX_H2_HEADINGS},
        )
    )

    return checks, True


def run(root: Path) -> GateResult:
    """Run the structural lint gate against ``root`` (the skill repo root)."""
    skill_md = root / "SKILL.md"
    references_dir = root / "references"

    all_checks: list[CheckResult] = []

    skill_checks, _ = _check_one("SKILL.md", skill_md)
    all_checks.extend(skill_checks)

    if references_dir.exists():
        for ref in sorted(references_dir.glob("*.md")):
            ref_checks, _ = _check_one(f"references/{ref.name}", ref)
            all_checks.extend(ref_checks)
    else:
        all_checks.append(
            CheckResult(
                name="references",
                passed=True,
                message=f"\n[WARN] references/ 目录不存在: {references_dir}",
                detail={"present": False},
            )
        )

    failures = sum(1 for c in all_checks if not c.passed)
    passed = failures == 0
    summary = "PASS (所有检查通过)" if passed else f"FAIL (失败 {failures} 项)"

    return GateResult(
        name="lint_structure",
        passed=passed,
        details=tuple(all_checks),
        summary=f"总结: {summary}",
    )
