"""Gate 2: SAST scan for PII, secrets, and prompt-injection vectors.

Scans every markdown file under ``root`` (skill root, ``references/``,
``examples/``) and the top-level ``README.md``. A single hard hit (PII, secret,
or known injection vector) flips the gate to FAIL.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

from .results import CheckResult, GateResult

__all__ = [
    "PII_PATTERNS",
    "SECRET_PATTERNS",
    "INJECTION_PATTERNS",
    "collect_scan_files",
    "scan_file",
    "run",
]

# (pattern, human label) — applied with re.finditer on full text.
PII_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\b1[3-9]\d{9}\b", "中国手机号"),
    (r"\b\d{17}[\dXx]\b", "中国身份证"),
    # Card numbers (16-19 contiguous digits) — exempted when bordered by path separators.
    (r"(?<![\w/])\d{16,19}(?![\w/])", "疑似银行卡号 (16-19 位连续数字)"),
    (r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]{2,}", "邮箱"),
)

SECRET_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI / Anthropic API key"),
    (r"ghp_[A-Za-z0-9]{30,}", "GitHub PAT"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"-----BEGIN [A-Z ]+PRIVATE KEY-----", "私钥"),
)

INJECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"忽略(以上|之前|上面)(的|所有)?(指示|指令|内容)", "中文注入: '忽略以上指示'"),
    (r"ignore (all|previous|above) (instructions|prompts)", "英文注入: ignore previous"),
    (r"你现在是[^\n]{0,30}角色", "角色劫持: '你现在是...角色'"),
    (r"<\|im_start\|>", "ChatML 注入: <|im_start|>"),
    (r"<\|im_end\|>", "ChatML 注入: <|im_end|>"),
    (r"\[INST\]", "Llama 注入: [INST]"),
    (r"<<SYS>>", "Llama 系统段: <<SYS>>"),
    (r"\{\{.*system.*\}\}", "模板注入: {{...system...}}"),
)

_SCAN_SUBDIRS: tuple[str, ...] = ("", "references", "examples")


def collect_scan_files(root: Path) -> list[tuple[str, Path]]:
    """Return ``[(label, path), ...]`` for every file the security gate scans."""
    files: list[tuple[str, Path]] = []
    for sub in _SCAN_SUBDIRS:
        base = root / sub if sub else root
        if not base.exists():
            continue
        for p in sorted(base.glob("*.md")):
            label = (sub + "/") + p.name if sub else p.name
            files.append((label, p))
    return files


def _scan_text(text: str) -> list[tuple[str, str]]:
    """Apply all PII / SECRET / INJECTION regexes to ``text``; return all hard hits."""
    hits: list[tuple[str, str]] = []
    for pat, label in PII_PATTERNS:
        for m in re.finditer(pat, text):
            hits.append((label, m.group()[:40]))
    for pat, label in SECRET_PATTERNS:
        for m in re.finditer(pat, text):
            hits.append((label, m.group()[:40]))
    for pat, label in INJECTION_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            hits.append((label, m.group()[:40]))
    return hits


def scan_file(label: str, path: Path) -> tuple[list[CheckResult], bool]:
    """Scan a single file; return ``(checks, present)``."""
    if not path.exists():
        return (
            [CheckResult(name=label, passed=False, message=f"[MISS] {label}: 文件不存在")],
            False,
        )
    text = path.read_text(encoding="utf-8")
    hits = _scan_text(text)
    if hits:
        messages = [f"[{label}] 硬命中 {len(hits)} 条"]
        messages.extend(f"  - {label_}: {val!r}" for label_, val in hits)
        hit_detail = [{"label": hit_label, "value": hit_val} for hit_label, hit_val in hits]
        check = CheckResult(
            name=label,
            passed=False,
            message="\n".join(messages),
            detail={"hits": hit_detail},
        )
        return ([check], True)

    return (
        [CheckResult(name=label, passed=True, message=f"[{label}] 干净 (无 PII / SECRET / 注入)")],
        True,
    )


def run(root: Path) -> GateResult:
    """Run the security-scan gate against ``root``."""
    files = collect_scan_files(root)
    all_checks: list[CheckResult] = []
    for label, path in files:
        checks, _ = scan_file(label, path)
        all_checks.extend(checks)

    failures = sum(1 for c in all_checks if not c.passed)
    passed = failures == 0
    summary = (
        f"PASS (无硬命中, 扫描 {len(files)} 个文件)" if passed else f"FAIL (硬命中 {failures} 条)"
    )
    return GateResult(
        name="scan_security",
        passed=passed,
        details=tuple(all_checks),
        summary=f"扫描完成: {summary}",
    )


# Re-exported for callers that want to iterate pattern triples explicitly.
ITER_PATTERNS: Iterable[tuple[str, str]] = (
    *((p, label) for p, label in PII_PATTERNS),
    *((p, label) for p, label in SECRET_PATTERNS),
    *((p, label) for p, label in INJECTION_PATTERNS),
)
