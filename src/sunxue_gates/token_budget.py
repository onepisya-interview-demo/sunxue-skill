"""Gate 4: token budget — chars/3 estimate + cold-start timing.

Soft limits (used as fail thresholds):
- `SKILL.md` single file ≤ 8_500 tokens.
- `references/` total ≤ 22_000 tokens (v1.2.0 bump 16_000 → 22_000, CHANGELOG 1.2.0 §34).
- Single reference ≤ 4_000 tokens.

Examples are reported for information only.

Precision switch (plan 3.3):
- `SUNXUE_PRECISE=1` enables tiktoken-based counting when the `tiktoken`
  package is importable (installed via `uv sync --extra precise`).
- Without tiktoken, the gate always falls back to `chars / 3` heuristic and
  emits `estimate=heuristic` in the per-file message so the operator can
  see why the count is conservative.
- Default behavior (env unset) is identical to v1.1.0 — heuristic everywhere,
  no mode tag emitted.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Protocol

from .results import CheckResult, GateResult


class _TiktokenEncoding(Protocol):
    """Minimal duck-typed surface we use from a tiktoken ``Encoding``.

    ``tiktoken`` is an optional dependency (installed via
    ``uv sync --extra precise``); the Protocol gives basedpyright / ty a
    concrete shape without making the runtime import mandatory.
    """

    def encode(self, text: str) -> list[int]: ...


__all__ = [
    "CHARS_PER_TOKEN",
    "SOFT_LIMIT",
    "est_tokens",
    "est_tokens_text",
    "is_precise_active",
    "run",
]

CHARS_PER_TOKEN: int = 3  # empirical, approximates English tokenization for Chinese-heavy text.

SOFT_LIMIT: dict[str, int] = {
    "SKILL.md": 8_500,
    "references_total": 22_000,
    "reference_single": 4_000,
}


# ---------------------------------------------------------------------------
# Precision switch (plan 3.3)
# ---------------------------------------------------------------------------
# `SUNXUE_PRECISE=1` opts into tiktoken counting when the dependency is
# importable. The flag is captured via `os.environ` at call time (not at
# import time) so tests can flip it via `monkeypatch.setenv`.
_TIKTOKEN_ENCODING: _TiktokenEncoding | None = None
_TIKTOKEN_IMPORT_ERROR: BaseException | None = None


def _try_load_tiktoken() -> _TiktokenEncoding | None:
    """Return a cached tiktoken encoding, or `None` if tiktoken is not installed.

    Result is memoized at module level — the encoding load is cheap relative
    to the per-file encode cost, but importing the package is not free, so we
    do it once and reuse the encoding handle.
    """
    global _TIKTOKEN_ENCODING, _TIKTOKEN_IMPORT_ERROR  # noqa: PLW0603
    if _TIKTOKEN_ENCODING is not None or _TIKTOKEN_IMPORT_ERROR is not None:
        return _TIKTOKEN_ENCODING
    try:
        import tiktoken  # type: ignore[import-not-found]
    except ImportError as e:
        _TIKTOKEN_IMPORT_ERROR = e
        return None
    # cl100k_base is the tokenizer used by GPT-3.5/4 generations; it's a
    # reasonable default for Chinese-heavy skill text and is what tiktoken
    # ships first-class without needing a downloadable extra.
    _TIKTOKEN_ENCODING = tiktoken.get_encoding("cl100k_base")
    return _TIKTOKEN_ENCODING


def is_precise_active() -> bool:
    """Return `True` iff `SUNXUE_PRECISE=1` is set AND tiktoken is importable.

    Pure function (reads env at call time) so callers can flip the env var
    via `monkeypatch.setenv` and re-evaluate without re-importing the module.
    """
    return os.environ.get("SUNXUE_PRECISE") == "1" and _try_load_tiktoken() is not None


def est_tokens(n_chars: int) -> int:
    """Estimate tokens via `n_chars // CHARS_PER_TOKEN`.

    Public contract kept stable for v1.1.0 callers / tests. For precise
    counting, prefer `est_tokens_text` which dispatches on the
    `SUNXUE_PRECISE` switch.
    """
    return n_chars // CHARS_PER_TOKEN


def est_tokens_text(text: str) -> tuple[int, str]:
    """Estimate tokens for `text`; return `(count, mode)`.

    `mode` is `"precise"` when tiktoken is importable and the
    `SUNXUE_PRECISE` switch is set, `"heuristic"` otherwise.
    Callers surface the mode in user-facing messages so the operator can
    see which estimator was used.
    """
    enc = _try_load_tiktoken() if os.environ.get("SUNXUE_PRECISE") == "1" else None
    if enc is not None:
        return len(enc.encode(text)), "precise"
    return len(text) // CHARS_PER_TOKEN, "heuristic"


def run(root: Path) -> GateResult:
    """Run the token-budget gate against `root`."""
    skill_md = root / "SKILL.md"
    references_dir = root / "references"
    examples_dir = root / "examples"

    all_checks: list[CheckResult] = []
    over = 0
    cold_ms: float | None = None
    precise = is_precise_active()
    # A precise mode header is emitted once at the top so the operator
    # knows the rest of the report used tiktoken. When heuristic is used
    # and the switch is on, we emit a per-file estimate tag instead.
    if precise:
        all_checks.append(
            CheckResult(
                name="mode",
                passed=True,
                message="\n[mode] SUNXUE_PRECISE=1 — counting with tiktoken (cl100k_base)",
                detail={"mode": "precise", "switch": "SUNXUE_PRECISE", "value": "1"},
            )
        )

    # 1) SKILL.md single file
    if skill_md.exists():
        t0 = time.perf_counter()
        text = skill_md.read_text(encoding="utf-8")
        t1 = time.perf_counter()
        cold_ms = (t1 - t0) * 1000
        size = len(text)
        if precise:
            tok, mode = est_tokens_text(text)
        else:
            tok = est_tokens(size)
            mode = "heuristic"
        limit = SOFT_LIMIT["SKILL.md"]
        ok = tok <= limit
        tag = "OK" if ok else "OVER"
        msg = f"\n[SKILL.md] chars={size}  est_tokens={tok}  estimate={mode}  上限={limit}  [{tag}]"
        all_checks.append(
            CheckResult(
                name="SKILL.md",
                passed=ok,
                message=msg,
                detail={"size": size, "tokens": tok, "limit": limit, "mode": mode},
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
        mode = "heuristic"  # overwritten below if precise is on
        for ref in sorted(references_dir.glob("*.md")):
            text = ref.read_text(encoding="utf-8")
            size = len(text)
            if precise:
                tok, mode = est_tokens_text(text)
            else:
                tok = est_tokens(size)
                mode = "heuristic"
            total_chars += size
            total_tok += tok
            single_limit = SOFT_LIMIT["reference_single"]
            ok = tok <= single_limit
            if not ok:
                per_file += 1
            tag = "OK" if ok else "OVER"
            ref_msg = (
                f"  - {ref.name}  chars={size}  est_tokens={tok}  "
                f"estimate={mode}  上限={single_limit}  [{tag}]"
            )
            all_checks.append(
                CheckResult(
                    name=f"references/{ref.name}",
                    passed=ok,
                    message=ref_msg,
                    detail={"size": size, "tokens": tok, "limit": single_limit, "mode": mode},
                )
            )
        total_limit = SOFT_LIMIT["references_total"]
        ok = total_tok <= total_limit
        tag = "OK" if ok else "OVER"
        total_msg = (
            f"  -- 合计  chars={total_chars}  est_tokens={total_tok}  "
            f"estimate={mode}  上限={total_limit}  [{tag}]"
        )
        all_checks.append(
            CheckResult(
                name="references/total",
                passed=ok,
                message=total_msg,
                detail={
                    "chars": total_chars,
                    "tokens": total_tok,
                    "limit": total_limit,
                    "mode": mode,
                },
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
