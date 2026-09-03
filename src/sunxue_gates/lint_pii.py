"""Gate 8: project-specific PII / privacy guard.

Why this gate exists
====================

``scan_security`` is the **generic** PII gate — it catches email addresses,
phone numbers, API keys, and prompt-injection vectors. It is regex-only
and has no project context.

The current repository has had three recurring privacy / naming leaks that
the generic gate cannot catch, because the offending tokens are not in
its regex tables:

1. **Placeholder identity emails** of the shape ``<name>@<host>.local``
   (e.g. ``gates@sunxue.local``) — written into git config or examples
   to spoof an author identity. Once committed, they poison the
   repository's commit history and force a destructive ``filter-branch``
   rewrite to clear.

2. **Local agent system paths** of the shape ``~/.hermes`` /
   ``~/.minimax`` — these expose the user's personal AI agent
   filesystem layout. Pushed to a public repo, they reveal the full
   working environment.

3. **Tool-name references** such as ``Mavis`` / ``minimax-code`` that
   are intended to be desensitized in the public-facing README and
   examples, but are easy to slip back in during a doc edit.

Scope discipline
================

- This gate is **deliberately narrow**. Only patterns known to have
  caused real leaks in this repo are listed.
- Adding a new pattern requires editing :data:`PII_LINT_PATTERNS` AND
  an entry in :data:`_NARRATIVE_EXEMPT` (if any path should be allowed
  to mention it) AND a CHANGELOG note. The combined discipline is what
  prevents the gate from becoming a second generic-PII engine.
- ``notes/`` discussion files (``pitfalls.md``, ``learning.md``,
  ``runbook.md``, ``testing.md``) and ``CHANGELOG.md`` are exempt by
  default — they exist precisely to discuss the very tokens this gate
  guards. The exemption is path-based (not regex-based) so it cannot
  be widened by mistake.

Exemption policy
================

``_NARRATIVE_EXEMPT`` is a path-keyed dict. The key is either an exact
filename (e.g. ``"CHANGELOG.md"``) or a subdirectory prefix
(e.g. ``"notes/"``). The value is a frozenset of pattern **labels**
that are suppressed for that path. Files outside the exemption set
get every hit reported.
"""

from __future__ import annotations

import re
from pathlib import Path

from .results import CheckResult, GateResult

__all__ = [
    "PII_LINT_PATTERNS",
    "collect_lint_files",
    "scan_text",
    "scan_file",
    "run",
]


# ---------------------------------------------------------------------------
# Pattern table — project-specific, narrow, hand-curated.
# Adding a row:  (1) write the regex, (2) write a label that names the
# failure mode, (3) if any path should be allowed to mention it, add
# that path + label to _NARRATIVE_EXEMPT, (4) update CHANGELOG.
# ---------------------------------------------------------------------------

PII_LINT_PATTERNS: tuple[tuple[str, str], ...] = (
    # Placeholder identity emails — the shape that produced the
    # ``gates@sunxue.local`` author-email incident. Hard-coded ``.local``
    # TLD: legitimate personal/work emails never use it.
    (
        r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.local\b",
        "占位邮箱 (机器身份 / 假身份)",
    ),
    # Local agent system paths — these expose the user's personal AI
    # agent filesystem layout. The ``.hermes`` (sub-agent role registry)
    # and ``.minimax`` (runtime data dir) names are environment-specific
    # and have no business in a published skill.
    (
        r"(?:~|\\|\$HOME)/\.hermes(?:/[\w./-]*)?",
        "本地 agent 系统路径 ~/.hermes",
    ),
    (
        r"(?:~|\\|\$HOME)/\.minimax(?:/[\w./-]*)?",
        "本地 agent 系统路径 ~/.minimax",
    ),
    # Tool-name references — the host agent's display name and CLI
    # binary name. Both are intended to be desensitized in public-facing
    # docs; both have slipped into README during routine edits.
    # Word-bounded so legitimate substrings (e.g. ``mavis`` in a code
    # identifier) do not trip the gate.
    (
        r"\bMavis\b",
        "工具名: Mavis",
    ),
    (
        r"\bminimax-code\b",
        "工具链名: minimax-code",
    ),
)


# Path-based exemption.  A key is either an exact filename or a
# directory prefix (with trailing slash).  A value is the set of
# pattern *labels* whose hits are suppressed under that path.  PII
# and SECRET categories from ``scan_security`` are NOT affected —
# this gate is the only thing that consults this map.
_NARRATIVE_EXEMPT: dict[str, frozenset[str]] = {
    # CHANGELOG.md is the audit log of every literal we ever shipped.
    # Suppressing every label there would defeat the audit; instead we
    # suppress only the placeholder-email and system-path labels, which
    # appear verbatim in older entries (rewriting history again to
    # strip them is more destructive than admitting they exist).
    "CHANGELOG.md": frozenset(
        {
            "占位邮箱 (机器身份 / 假身份)",
            "本地 agent 系统路径 ~/.hermes",
            "本地 agent 系统路径 ~/.minimax",
        }
    ),
    # PLAN.md is the local-only planning archive (already untracked
    # per .gitignore, retained on disk for personal reference). It
    # legitimately cites the local agent system paths it once
    # documented. Suppress the system-path labels so the archive can
    # keep its historical references without triggering the gate.
    "PLAN.md": frozenset(
        {
            "本地 agent 系统路径 ~/.hermes",
            "本地 agent 系统路径 ~/.minimax",
        }
    ),
    # The notes/ tree is the meta-discussion layer — it is allowed to
    # name the offending tokens, because naming them is the whole point
    # of those files.  Each file in notes/ is a deliberate narrative
    # about one of the leaks this gate prevents.
    "notes/": frozenset(
        {
            "占位邮箱 (机器身份 / 假身份)",
            "本地 agent 系统路径 ~/.hermes",
            "本地 agent 系统路径 ~/.minimax",
            "工具名: Mavis",
            "工具链名: minimax-code",
        }
    ),
}


# Files scanned — same surface as scan_security.  The two gates are
# kept in lockstep so a leak in a new directory surfaces in both.
_SCAN_SUBDIRS: tuple[str, ...] = ("", "references", "examples")
# File extensions the gate cares about.  Markdown first (the skill
# body is .md); Python second (pyproject authors block is the only
# place a placeholder email has been known to slip in).
_SCAN_GLOBS: tuple[str, ...] = ("*.md", "*.py", "*.toml")


def _is_path_exempt(rel: str, label: str) -> bool:
    """Return True if ``rel`` is in the narrative-exempt set for ``label``.

    ``rel`` is a forward-slash path relative to the gate root, e.g.
    ``"notes/pitfalls.md"`` or ``"README.md"``.  The map is consulted
    in declaration order; a directory-prefix match is exact (no
    ``**`` glob), so adding a new directory is a deliberate act.
    """
    # Exact filename match — fast path.
    name = rel.rsplit("/", 1)[-1]
    if name in _NARRATIVE_EXEMPT and label in _NARRATIVE_EXEMPT[name]:
        return True
    # Directory prefix match.
    for prefix, labels in _NARRATIVE_EXEMPT.items():
        if not prefix.endswith("/"):
            continue
        if rel.startswith(prefix) and label in labels:
            return True
    return False


def collect_lint_files(root: Path) -> list[tuple[str, Path]]:
    """Return ``[(label, path), ...]`` for every file the lint_pii gate scans.

    Mirrors :func:`sunxue_gates.scan_security.collect_scan_files` so the
    two gates agree on the scan surface — but adds ``.py`` and ``.toml``
    because placeholder identities have historically appeared in
    ``pyproject.toml``'s ``authors`` list.

    The scan surface deliberately excludes ``src/`` (this gate's own
    package source): the regex patterns and their labels live there in
    source-code form, so a self-scan would always false-positive on
    every pattern's documentation.
    """
    files: list[tuple[str, Path]] = []
    for sub in _SCAN_SUBDIRS:
        base = root / sub if sub else root
        if not base.exists():
            continue
        for glob in _SCAN_GLOBS:
            for p in sorted(base.glob(glob)):
                label = (sub + "/") + p.name if sub else p.name
                files.append((label, p))
    return files


def scan_text(text: str) -> list[tuple[str, str]]:
    """Apply every PII_LINT regex to ``text``; return all hard hits."""
    hits: list[tuple[str, str]] = []
    for pat, label in PII_LINT_PATTERNS:
        for m in re.finditer(pat, text):
            hits.append((label, m.group()[:60]))
    return hits


def scan_file(label: str, path: Path, rel: str) -> tuple[list[CheckResult], bool]:
    """Scan a single file; return ``(checks, present)``.

    ``rel`` is the path relative to the gate root (e.g.
    ``"references/foo.md"``) — used to consult the narrative-exempt
    map.  Files outside the map get every hit reported; files inside
    the map have the whitelisted labels' hits silently dropped before
    the failure check.
    """
    if not path.exists():
        return (
            [CheckResult(name=label, passed=False, message=f"[MISS] {label}: 文件不存在")],
            False,
        )
    text = path.read_text(encoding="utf-8")
    raw_hits = scan_text(text)
    # Apply path-based exemption: drop hits whose label is whitelisted
    # for this path.  This is a strict, opt-in whitelist — labels not
    # listed for this path still fail the gate.
    before = len(raw_hits)
    kept = [(lab, val) for lab, val in raw_hits if not _is_path_exempt(rel, lab)]
    suppressed = before - len(kept)
    if kept:
        messages = [f"[{label}] 命中 {len(kept)} 条项目专属 PII 关键词"]
        if suppressed:
            messages.append(f"  (叙事豁免丢弃 {suppressed} 条)")
        messages.extend(f"  - {lab_}: {val!r}" for lab_, val in kept)
        hit_detail = [{"label": lab_, "value": val_} for lab_, val_ in kept]
        detail: dict[str, object] = {"hits": hit_detail}
        if suppressed:
            detail["narrative_exempt_suppressed"] = suppressed
        check = CheckResult(
            name=label,
            passed=False,
            message="\n".join(messages),
            detail=detail,
        )
        return ([check], True)
    msg_suffix = f" (叙事豁免丢弃 {suppressed} 条)" if suppressed else ""
    return (
        [
            CheckResult(
                name=label,
                passed=True,
                message=f"[{label}] 干净 (无项目专属 PII){msg_suffix}",
                detail=({"narrative_exempt_suppressed": suppressed} if suppressed else {}),
            )
        ],
        True,
    )


def run(root: Path) -> GateResult:
    """Run the project-PII lint gate against ``root``."""
    files = collect_lint_files(root)
    all_checks: list[CheckResult] = []
    for label, path in files:
        rel = str(path.relative_to(root))
        checks, _ = scan_file(label, path, rel)
        all_checks.extend(checks)
    failures = sum(1 for c in all_checks if not c.passed)
    passed = failures == 0
    summary = (
        f"PASS (无项目专属 PII, 扫描 {len(files)} 个文件)"
        if passed
        else f"FAIL (硬命中 {failures} 个文件)"
    )
    return GateResult(
        name="lint_pii",
        passed=passed,
        details=tuple(all_checks),
        summary=f"项目 PII 扫描完成: {summary}",
    )
