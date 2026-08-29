"""Gate 4: token budget — chars/3 estimate + cold-start timing.

Soft limits (used as fail thresholds):
- ``SKILL.md`` single file ≤ 8_500 tokens.
- ``references/`` total ≤ 16_000 tokens.
- Single reference ≤ 4_000 tokens.

Examples are reported for information only.
"""

from __future__ import annotations

import time
from pathlib import Path

from .results import CheckResult, GateResult

__all__ = ["CHARS_PER_TOKEN", "SOFT_LIMIT", "est_tokens", "run"]

CHARS_PER_TOKEN: int = 3  # empirical, approximates English tokenization for Chinese-heavy text.

SOFT_LIMIT: dict[str, int] = {
    "SKILL.md": 8_500,
    "references_total": 16_000,
    "reference_single": 4_000,
}


def est_tokens(n_chars: int) -> int:
    """Estimate tokens via ``n_chars // CHARS_PER_TOKEN``."""
    return n_chars // CHARS_PER_TOKEN


def run(root: Path) -> GateResult:
    """Run the token-budget gate against ``root``."""
    skill_md = root / "SKILL.md"
    references_dir = root / "references"
    examples_dir = root / "examples"

    all_checks: list[CheckResult] = []
    over = 0
    cold_ms: float | None = None

    # 1) SKILL.md single file
    if skill_md.exists():
        t0 = time.perf_counter()
        text = skill_md.read_text(encoding="utf-8")
        t1 = time.perf_counter()
        cold_ms = (t1 - t0) * 1000
        size = len(text)
        tok = est_tokens(size)
        limit = SOFT_LIMIT["SKILL.md"]
        ok = tok <= limit
        tag = "OK" if ok else "OVER"
        msg = f"\n[SKILL.md] chars={size}  est_tokens={tok}  上限={limit}  [{tag}]"
        all_checks.append(
            CheckResult(
                name="SKILL.md",
                passed=ok,
                message=msg,
                detail={"size": size, "tokens": tok, "limit": limit},
            )
        )
        if not ok:
            over += 1
    else:
        all_checks.append(
            CheckResult(name="SKILL.md", passed=False, message=f"\n[MISS] {skill_md} 不存在")
        )
        over += 1

    # 2) references/ aggregate
    if references_dir.exists():
        total_chars = 0
        total_tok = 0
        per_file = 0
        for ref in sorted(references_dir.glob("*.md")):
            text = ref.read_text(encoding="utf-8")
            size = len(text)
            tok = est_tokens(size)
            total_chars += size
            total_tok += tok
            single_limit = SOFT_LIMIT["reference_single"]
            ok = tok <= single_limit
            if not ok:
                per_file += 1
            tag = "OK" if ok else "OVER"
            ref_msg = (
                f"  - {ref.name}  chars={size}  est_tokens={tok}  上限={single_limit}  [{tag}]"
            )
            all_checks.append(
                CheckResult(
                    name=f"references/{ref.name}",
                    passed=ok,
                    message=ref_msg,
                    detail={"size": size, "tokens": tok, "limit": single_limit},
                )
            )
        total_limit = SOFT_LIMIT["references_total"]
        ok = total_tok <= total_limit
        tag = "OK" if ok else "OVER"
        total_msg = (
            f"  -- 合计  chars={total_chars}  est_tokens={total_tok}  上限={total_limit}  [{tag}]"
        )
        all_checks.append(
            CheckResult(
                name="references/total",
                passed=ok,
                message=total_msg,
                detail={"chars": total_chars, "tokens": total_tok, "limit": total_limit},
            )
        )
        over += per_file + (0 if ok else 1)
    else:
        all_checks.append(
            CheckResult(
                name="references",
                passed=True,
                message=f"\n[WARN] references/ 目录不存在: {references_dir}",
                detail={"present": False},
            )
        )

    # 3) examples/ (info only — never increments the FAIL counter)
    if examples_dir.exists():
        ex_total = 0
        ex_count = 0
        for ex in sorted(examples_dir.glob("*.md")):
            text = ex.read_text(encoding="utf-8")
            tok = est_tokens(len(text))
            ex_total += tok
            ex_count += 1
            all_checks.append(
                CheckResult(
                    name=f"examples/{ex.name}",
                    passed=True,
                    message=f"  - {ex.name}  est_tokens={tok}  [INFO]",
                    detail={"tokens": tok},
                )
            )
        all_checks.append(
            CheckResult(
                name="examples/total",
                passed=True,
                message=f"  -- 合计  文件={ex_count}  est_tokens={ex_total}  [INFO]",
                detail={"count": ex_count, "tokens": ex_total},
            )
        )
    else:
        all_checks.append(
            CheckResult(
                name="examples",
                passed=True,
                message=f"\n[examples/] 不存在: {examples_dir}",
                detail={"present": False},
            )
        )

    # 4) cold-start timing (informational; never fails the gate)
    if cold_ms is not None:
        all_checks.append(
            CheckResult(
                name="cold-start",
                passed=True,
                message=f"\n[cold-start] SKILL.md read + 估算耗时: {cold_ms:.2f} ms",
                detail={"milliseconds": cold_ms},
            )
        )
    else:
        all_checks.append(
            CheckResult(
                name="cold-start",
                passed=True,
                message="\n[cold-start] 不可用 (SKILL.md 缺失)",
                detail={"available": False},
            )
        )

    passed = over == 0
    summary = "PASS (全部 token 在软上限内)" if passed else f"FAIL (超限 {over} 项)"
    return GateResult(
        name="token_budget",
        passed=passed,
        details=tuple(all_checks),
        summary=f"总结: {summary}",
    )
