"""Gate 5: jailbreak drill — verifies the SKILL describes defenses against 5 vectors.

Drill vectors and their keywords live in :data:`DRILLS`. A vector PASSES when at
least 2 of its keywords appear in either the SKILL ``description`` field or the
full SKILL body.

The literal keyword / vector strings are extracted to
:mod:`sunxue_gates.tables` (plan 2.1) so mutmut does not mass-mutate them.
This module re-exports ``DRILLS`` and ``Drill`` so the golden test and any
caller that imports ``from sunxue_gates.injection_drill import DRILLS``
keep working with no change.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .parsing import parse_frontmatter
from .results import CheckResult, GateResult
from .tables import DRILLS, Drill

__all__ = ["Drill", "DRILLS", "run"]


def _hit_keywords(keywords: Iterable[str], haystack: str) -> list[str]:
    """Return the subset of ``keywords`` that appear in ``haystack``."""
    return [kw for kw in keywords if kw in haystack]


def run(root: Path) -> GateResult:
    """Run the injection-drill gate against ``root``."""
    skill_md = root / "SKILL.md"

    if not skill_md.exists():
        return GateResult(
            name="injection_drill",
            passed=False,
            details=(
                CheckResult(name="SKILL.md", passed=False, message=f"[MISS] {skill_md} 不存在"),
            ),
            summary=f"总结: FAIL ([MISS] {skill_md} 不存在)",
        )

    text = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(text) or {}
    desc = str(fm.get("description", ""))

    all_checks: list[CheckResult] = [
        CheckResult(
            name="description_length",
            passed=True,
            message=f"description 长度: {len(desc)} 字符",
            detail={"length": len(desc)},
        ),
        CheckResult(
            name="skill_length",
            passed=True,
            message=f"SKILL.md 总长度: {len(text)} 字符",
            detail={"length": len(text)},
        ),
    ]

    failures = 0
    for drill in DRILLS:
        hits = _hit_keywords(drill.keywords, desc) + [
            f"[body] {kw}"
            for kw in _hit_keywords(drill.keywords, text)
            if kw not in _hit_keywords(drill.keywords, desc)
        ]
        ok = len(hits) >= 2
        if not ok:
            failures += 1
        all_checks.append(
            CheckResult(
                name=f"drill.{drill.id}",
                passed=ok,
                message=(
                    f"[{drill.id}] {drill.name}  -> {'PASS' if ok else 'FAIL'}  "
                    f"(命中 {len(hits)}/{len(drill.keywords)} 关键词)\n"
                    f"     向量: {drill.vector}\n"
                    f"     命中: {hits if hits else '(无)'}"
                ),
                detail={
                    "vector": drill.vector,
                    "hits": hits,
                    "required": 2,
                },
            )
        )

    passed = failures == 0
    summary = "PASS (5 个向量防护均到位)" if passed else f"FAIL ({failures} 个向量防护缺失)"
    return GateResult(
        name="injection_drill",
        passed=passed,
        details=tuple(all_checks),
        summary=f"总结: {summary}",
    )
