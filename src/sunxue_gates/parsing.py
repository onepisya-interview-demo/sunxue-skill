"""Shared parsing helpers used by multiple gates.

Pure functions only — no I/O at import time.
"""

from __future__ import annotations

import re
from pathlib import Path

__all__ = ["parse_frontmatter", "classify_doc", "count_h2"]

# Split a fenced YAML frontmatter block at the start of a markdown file.
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
# Single-line ``key: value`` entry (value may be empty).
_KV_LINE_RE = re.compile(r"^(\S+):\s*(.*)$")
# Multi-line literal-block entry ``key: |\n`` followed by indented lines.
_BLOCK_RE = re.compile(r"^(\S+):\s*\|\s*\n((?:  .*\n?)+)", re.MULTILINE)


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Parse a minimal YAML frontmatter block.

    Supports single-line ``key: value`` entries and literal-block (``|``) entries.
    Returns ``None`` if no ``---`` block is present at the start of ``text``.
    """
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        return None
    body = match.group(1)
    out: dict[str, str] = {}

    # First pass: literal blocks take precedence over single-line entries.
    for key, block in _BLOCK_RE.findall(body):
        out[key] = " ".join(line.strip() for line in block.splitlines())

    # Second pass: single-line ``key: value``.
    for line in body.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        kv = _KV_LINE_RE.match(line)
        if kv is None:
            continue
        key, value = kv.group(1), kv.group(2)
        if key in out:
            # Already populated from a literal block — skip.
            continue
        if not value.strip():
            # Empty value: leave as empty string; caller can decide what to do.
            out.setdefault(key, "")
            continue
        out[key] = value.strip().strip('"').strip("'")

    return out


def classify_doc(path: Path) -> str:
    """Return ``'SKILL'`` for the top-level ``SKILL.md`` and ``'reference'`` otherwise."""
    return "SKILL" if path.name == "SKILL.md" else "reference"


_H2_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


def count_h2(text: str) -> int:
    """Count level-2 headings (``## ``) in ``text``."""
    return len(_H2_HEADING_RE.findall(text))
