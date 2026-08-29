"""Gate 6: mutation drill — verifies hard-metric keywords survive 3 mutate operators.

For each of 5 key instructions extracted from ``SKILL.md`` (matched on the
5 :data:`KEY_PHRASES`), three mutations are applied:
- M1 synonym replacement
- M2 sentence split
- M3 softening (强 → 弱)

The mutation PASSES iff the resulting sentence still hits ≥ 1 of the
hard-metric keywords in :data:`HARD_KEYWORDS`, OR the original sentence hit
zero (nothing to lose).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

from .results import CheckResult, GateResult

__all__ = [
    "KEY_PHRASES",
    "HARD_KEYWORDS",
    "mutate_synonym",
    "mutate_split",
    "mutate_soften",
    "MUTATORS",
    "extract_key_sentences",
    "hit_count",
    "run",
]

KEY_PHRASES: tuple[str, ...] = (
    "必须",
    "不要",
    "改成",
    "出庭作证",
    "判断一个句子是否合格",
)

HARD_KEYWORDS: tuple[str, ...] = (
    "数字",
    "服务者",
    "物件",
    "闭环",
    "沉默",
    "排比",
    "反问",
    "程度副词",
    "情绪",
    "比喻",
    "场景切换",
    "我说好",
    "遗留物",
)

_SPLIT_MARKERS = re.compile(r"([，。；])")


def mutate_synonym(text: str) -> str:
    """Replace strong-mood words with neutral synonyms (M1)."""
    table = (
        ("必须", "务必"),
        ("不要", "请勿"),
        ("应该", "宜"),
        ("改写", "改写成"),
    )
    out = text
    for a, b in table:
        out = out.replace(a, b)
    return out


def mutate_split(text: str) -> str:
    """Split the sentence at the first comma/period/semicolon, joining with '也就是说,' (M2)."""
    parts = _SPLIT_MARKERS.split(text, maxsplit=1)
    if len(parts) >= 3:
        head, sep, tail = parts[0], parts[1], "".join(parts[2:])
        return f"{head}{sep} 也就是说, {tail}"
    return text + " 这一条不要忘。"


def mutate_soften(text: str) -> str:
    """Soften strong words into suggestions (M3)."""
    table = (
        ("必须", "建议"),
        ("务必", "尽量"),
        ("请勿", "尽量不要"),
        ("不要", "尽量不要"),
        ("严禁", "不推荐"),
        ("应该", "可以"),
    )
    out = text
    for a, b in table:
        out = out.replace(a, b)
    return out


MUTATORS: tuple[tuple[str, Callable[[str], str]], ...] = (
    ("M1 同义词", mutate_synonym),
    ("M2 拆句", mutate_split),
    ("M3 软化", mutate_soften),
)


def extract_key_sentences(text: str, max_n: int = 5) -> list[str]:
    """Return up to ``max_n`` sentences from ``text`` containing :data:`KEY_PHRASES`."""
    sents = re.split(r"(?<=[。！？\n])\s*", text)
    out: list[str] = []
    used: set[int] = set()
    for phrase in KEY_PHRASES:
        for s in sents:
            if phrase in s and 20 <= len(s) <= 200 and id(s) not in used:
                out.append(s.strip())
                used.add(id(s))
                break
        if len(out) >= max_n:
            break
    return out


def hit_count(text: str) -> int:
    """Return how many :data:`HARD_KEYWORDS` appear in ``text`` (deduped)."""
    return sum(1 for kw in HARD_KEYWORDS if kw in text)


def run(root: Path) -> GateResult:
    """Run the mutation-drill gate against ``root``."""
    skill_md = root / "SKILL.md"

    if not skill_md.exists():
        return GateResult(
            name="mutation_drill",
            passed=False,
            details=(
                CheckResult(name="SKILL.md", passed=False, message=f"[MISS] {skill_md} 不存在"),
            ),
            summary=f"总结: FAIL ([MISS] {skill_md} 不存在)",
        )

    text = skill_md.read_text(encoding="utf-8")
    sentences = extract_key_sentences(text, max_n=5)

    all_checks: list[CheckResult] = [
        CheckResult(
            name="extracted_count",
            passed=True,
            message=f"抽取关键指令 {len(sentences)} 条",
            detail={"count": len(sentences)},
        ),
        CheckResult(
            name="base_hits",
            passed=True,
            message=f"基线硬指标关键词命中数: {hit_count(text)}",
            detail={"base_hits": hit_count(text)},
        ),
    ]

    if not sentences:
        all_checks.append(
            CheckResult(
                name="no_sentences",
                passed=True,
                message="[WARN] 未抽到任何关键指令, 按 PASS 处理 (无变异对象)",
                detail={"empty": True},
            )
        )
        return GateResult(
            name="mutation_drill",
            passed=True,
            details=tuple(all_checks),
            summary="[WARN] 未抽到任何关键指令, 按 PASS 处理 (无变异对象)",
        )

    failures = 0
    for i, sent in enumerate(sentences, 1):
        sent_hits = hit_count(sent)
        sent_preview = sent[:120]
        sent_suffix = "..." if len(sent) > 120 else ""
        all_checks.append(
            CheckResult(
                name=f"sentence.{i}.original",
                passed=True,
                message=f"\n--- 指令 {i} ---\n原句 ({sent_hits} hits): {sent_preview}{sent_suffix}",
                detail={"sentence": sent, "hits": sent_hits},
            )
        )
        for mname, mfunc in MUTATORS:
            mutated = mfunc(sent)
            m_hits = hit_count(mutated)
            ok = m_hits >= 1 or sent_hits == 0
            if not ok:
                failures += 1
            all_checks.append(
                CheckResult(
                    name=f"sentence.{i}.{mname}",
                    passed=ok,
                    message=(
                        f"  [{'PASS' if ok else 'FAIL'}] {mname} ({m_hits} hits): "
                        f"{mutated[:120]}{'...' if len(mutated) > 120 else ''}"
                    ),
                    detail={
                        "mutator": mname,
                        "hits": m_hits,
                        "mutated_preview": mutated[:120],
                    },
                )
            )

    passed = failures == 0
    summary = "PASS (所有变异后硬指标仍可命中)" if passed else f"FAIL ({failures} 项变异破坏硬约束)"
    return GateResult(
        name="mutation_drill",
        passed=passed,
        details=tuple(all_checks),
        summary=f"总结: {summary}",
    )
