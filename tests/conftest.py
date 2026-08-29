"""Shared pytest fixtures for the sunxue-gates test suite.

Provides:
- ``skill_root`` — absolute path to the skill repo root (parent of ``src/``).
- ``in_src_path`` — context manager that adds ``src/`` to ``sys.path`` so tests
  can ``import sunxue_gates`` without an editable install.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

# Repo layout: <repo>/tests/conftest.py → <repo>/tests → <repo>
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"


@contextmanager
def _in_src_path():
    p = str(SRC_DIR)
    inserted = p not in sys.path
    if inserted:
        sys.path.insert(0, p)
    try:
        yield
    finally:
        if inserted:
            try:
                sys.path.remove(p)
            except ValueError:  # pragma: no cover - defensive
                pass


@pytest.fixture(scope="session")
def skill_root() -> Path:
    """Return the absolute path to the skill repo root."""
    return REPO_ROOT


@pytest.fixture(autouse=True)
def _auto_src_path():
    """Ensure ``import sunxue_gates`` resolves from ``src/`` for every test."""
    with _in_src_path():
        yield
