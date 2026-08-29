"""Literal-provenance golden generator (plan 1.1).

Walks every pure-string keyword/pattern table in the four gate modules
(:mod:`sunxue_gates.injection_drill`, :mod:`sunxue_gates.scan_security`,
:mod:`sunxue_gates.mutation_drill`, :mod:`sunxue_gates.regression_output`),
hashes each string with SHA-256 + encodes it as UTF-8 hex, and writes
``tests/golden/literals.json``.

The golden file contains ONLY ``sha256`` + ``hex_utf8`` fields — never
plaintext. The matching test
(:mod:`tests.unit.test_golden_literals`) decodes the hex back and compares
the runtime table against the golden field-by-field (exact string equality,
order, nesting, counts).

Re-run this generator whenever one of the four source tables changes
(``regenerating golden is part of triage discipline``). Then re-run pytest
to refresh the test contract.

Usage (from repo root)::

    UV_CACHE_DIR=$PWD/.cache/uv uv run python tests/golden/gen_golden.py
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import time
from pathlib import Path

# Make src/ importable without an editable install (mirrors conftest.py).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _hash_string(s: str) -> dict[str, str]:
    """Return ``{sha256, hex_utf8}`` for the given Python string."""
    raw = s.encode("utf-8")
    return {"sha256": hashlib.sha256(raw).hexdigest(), "hex_utf8": raw.hex()}


def _hash_tree(value: object) -> object:
    """Recursively encode any tree of strings / tuples / lists.

    - ``str`` -> ``{"sha256": ..., "hex_utf8": ...}``
    - ``tuple`` / ``list`` -> recurse over elements, preserving order and nesting

    The test asserts the runtime tree equals the golden tree after decoding
    hex back to ``str`` for every leaf. This keeps the "contains marker
    token" guard testable without storing any plaintext in the golden file.
    """
    if isinstance(value, str):
        return _hash_string(value)
    if isinstance(value, (tuple, list)):
        return [_hash_tree(v) for v in value]
    raise TypeError(
        f"_hash_tree: unsupported value {type(value).__name__!r} — "
        "golden tables must be pure strings or sequences of strings"
    )


def _drill_module() -> dict[str, object]:
    """Harvest the injection_drill DRILLS table (tuple of Drill dataclasses)."""
    from sunxue_gates import injection_drill

    fields: dict[str, list[object]] = {"id": [], "name": [], "vector": [], "keywords": []}
    for d in injection_drill.DRILLS:
        fields["id"].append(_hash_string(d.id))
        fields["name"].append(_hash_string(d.name))
        fields["vector"].append(_hash_string(d.vector))
        fields["keywords"].append(_hash_tree(d.keywords))
    return {"DRILLS": fields}


def _pattern_module() -> dict[str, object]:
    """Harvest the scan_security pattern tables (tuples of (regex, label) pairs)."""
    from sunxue_gates import scan_security

    def harvest(table: tuple[tuple[str, str], ...]) -> list[list[dict[str, str]]]:
        return [[_hash_string(pattern), _hash_string(label)] for pattern, label in table]

    return {
        "PII_PATTERNS": harvest(scan_security.PII_PATTERNS),
        "SECRET_PATTERNS": harvest(scan_security.SECRET_PATTERNS),
        "INJECTION_PATTERNS": harvest(scan_security.INJECTION_PATTERNS),
        "ITER_PATTERNS": harvest(scan_security.ITER_PATTERNS),
    }


def _flat_string_tables(
    module_name: str,
    *table_names: str,
    extras: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> dict[str, list[dict[str, str]]]:
    """Harvest a module's flat ``tuple[str, ...]`` tables by attribute name."""
    mod = importlib.import_module(module_name)
    out: dict[str, list[dict[str, str]]] = {}
    for n in table_names:
        table: tuple[str, ...] = getattr(mod, n)
        out[n] = [_hash_string(s) for s in table]
    for n, table in extras:
        out[n] = [_hash_string(s) for s in table]
    return out


def _server_polyphony_table() -> list[dict[str, str]]:
    """Reach the ``words = (...)`` tuple inside count_server_polyphony.

    This role-word list is defined as a local in that function — the only
    pure-string table in regression_output that is not a module-level
    constant. We pull it via ``co_consts[1]`` (the only tuple in that
    code object). If that table ever moves to a module-level constant,
    swap to ``_flat_string_tables("sunxue_gates.regression_output", "WORDS")``.
    """
    from sunxue_gates import regression_output

    fn = regression_output.count_server_polyphony
    candidates = [c for c in fn.__code__.co_consts if isinstance(c, tuple) and len(c) > 3]
    if len(candidates) != 1:
        raise RuntimeError(
            "Expected exactly one tuple of strings in "
            "regression_output.count_server_polyphony.__code__.co_consts; "
            f"got {len(candidates)} — update _server_polyphony_table()."
        )
    words: tuple[str, ...] = candidates[0]
    return [_hash_string(w) for w in words]


def _counts(obj: object) -> int:
    """Total number of leaf string entries (for the operator summary line)."""
    if isinstance(obj, list):
        return sum(_counts(v) for v in obj)
    if isinstance(obj, dict):
        return sum(_counts(v) for v in obj.values())
    if isinstance(obj, tuple):  # pragma: no cover - we don't produce tuples
        return sum(_counts(v) for v in obj)
    if isinstance(obj, str):  # pragma: no cover - we don't keep raw strs
        return 1
    return 0


def main() -> int:
    """Walk all four modules; write ``tests/golden/literals.json``."""
    injection: dict[str, object] = _drill_module()
    security: dict[str, object] = _pattern_module()
    mutation: dict[str, object] = _flat_string_tables(
        "sunxue_gates.mutation_drill", "KEY_PHRASES", "HARD_KEYWORDS"
    )
    regression: dict[str, object] = {
        **_flat_string_tables("sunxue_gates.regression_output", "DEG_ADV", "EMO_DIRECT"),
        "SERVER_POLYPHONY_WORDS": _server_polyphony_table(),
    }

    payload: dict[str, object] = {
        "_meta": {
            "generator": "tests/golden/gen_golden.py",
            "schema_version": 1,
            "note": (
                "This file stores ONLY sha256 + hex_utf8 of every pure-string "
                "token in the four keyword/pattern tables. Plaintext is "
                "banned in tests/** (LLM-transcription corruption guard)."
            ),
        },
        "sunxue_gates.injection_drill": injection,
        "sunxue_gates.scan_security": security,
        "sunxue_gates.mutation_drill": mutation,
        "sunxue_gates.regression_output": regression,
    }

    out_path = Path(__file__).resolve().parent / "literals.json"
    # Atomic-write pattern guarded against index.lock collision; retry twice.
    attempts = 0
    while True:
        try:
            tmp = out_path.with_suffix(out_path.suffix + ".tmp")
            with tmp.open("x", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=False)
                fh.write("\n")
            os.replace(tmp, out_path)
            break
        except FileExistsError:
            attempts += 1
            if attempts >= 3:
                raise
            time.sleep(2)

    print(f"Wrote {out_path}")
    print(f"  injection_drill:   {_counts(injection)} leaf strings")
    print(f"  scan_security:     {_counts(security)} leaf strings")
    print(f"  mutation_drill:    {_counts(mutation)} leaf strings")
    print(f"  regression_output: {_counts(regression)} leaf strings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
