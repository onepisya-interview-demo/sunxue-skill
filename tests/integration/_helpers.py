"""Shared helpers for ``tests/integration/`` CLI tests.

v1.3.0 cluster B F19-F20: prior to this module, every integration test
file redefined ``_find_repo_root`` + ``_run`` with byte-identical
implementations (copy-pasted from the first writer). Two consequences:

1. The mutmut-sandbox disambiguator logic (look for ``scripts/`` to
   distinguish the real repo from a ``mutants/`` checkout) had to be
   kept in sync by hand across the two files; any drift would let a
   test silently resolve to the wrong script path.
2. Adding a third integration test file meant another copy of the same
   30 lines.

Centralising them here also gives the helper a single owner: any future
   "find repo root" tweak (e.g. honouring ``SUNXUE_REPO_ROOT`` env
   var) only needs to land once.

The helpers are deliberately small and dependency-free — they only
   import ``pathlib``, ``subprocess``, ``sys`` so importing this module
   from any integration test stays cheap.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    """Walk up until we find the real sunxue-skill repo root.

    The disambiguator is the ``scripts/`` directory: it lives only at
    the real repo root, never in the mutmut sandbox (mutmut 3.x copies
    pyproject.toml + src/ + tests/ but not scripts/). Without this
    guard, a naive ``pyproject.toml + src/`` check would match
    ``mutants/`` and resolve SCRIPT to the wrong path.
    """
    for candidate in [start, *start.parents]:
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src").is_dir()
            and (candidate / "scripts").is_dir()
        ):
            return candidate
    raise RuntimeError(
        f"could not locate repo root (no pyproject.toml + src/ + scripts/ above {start})"
    )


REPO_ROOT: Path = find_repo_root(Path(__file__).resolve().parent)


def run_script(
    script: Path, args: list[str], *, stdin_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Invoke the CLI script with ``args`` and capture stdout/stderr separately.

    ``script`` is the absolute path to the script under test (typically
    one of ``scripts/coherence_gate.py`` / ``scripts/writing_gate.py``).
    The 30s timeout is a defensive ceiling for hung subprocesses — the
    longest single-script test today is well under 5s.
    """
    return subprocess.run(  # noqa: S603 — intentional CLI invocation in tests
        [sys.executable, str(script), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        input=stdin_text,
    )
