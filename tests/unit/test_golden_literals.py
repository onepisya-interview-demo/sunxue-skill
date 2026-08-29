"""Unit tests for the literal-provenance golden (plan 1.1).

Threat model
============

The four ``src/sunxue_gates/*.py`` modules covered by
``tests/golden/literals.json`` carry hot-literal marker tokens
(ChatML ``<|im_start|>``, Llama ``[INST]`` / ``<<SYS>>``,
template ``{{system_prompt}}``, the always-substring ``""`` empty-string
keyword that caused the ``D3`` incident, etc.). They MUST stay verbatim
because the gates match them by ``in`` / ``re.finditer`` semantics —
swallowing a single character flips a guard from "always pass" to "silent
false positive" without any code change (the D3 baseline corruption that
this plan exists to catch).

If a future edit transcribes those literals through a language model, the
model is known to silently strip or rewrite tokens whose shapes it judges
"unusual" (``<|im_start|>`` → ``<im_start>`` or ``<|im_start>`` → "", etc.).
A test that re-states the literal as a Python string in
``tests/**/*.py`` would therefore suffer from the same vulnerability it is
trying to detect. This test deliberately does NOT: it compares every
runtime value against ``tests/golden/literals.json``, which stores ONLY
the SHA-256 + UTF-8 hex of each string, never plaintext.

Triage discipline when a src table changes
=========================================

If you intentionally edit one of the four src tables, the test will go
RED with a ``field_mismatch`` (hex no longer matches the runtime string).
That is the desired signal. To acknowledge the change:

1. Re-run the generator: ``uv run python tests/golden/gen_golden.py``
2. Re-run pytest: ``uv run pytest tests/unit/test_golden_literals.py``
3. Inspect the literal-provenance diff (``git diff tests/golden/literals.json``)
   and confirm every flipped leaf is something you meant to change.

Discipline: the diff of ``literals.json`` is the audit log of which
strings moved in the source tables. This is the "regenerating golden is
part of triage discipline" contract documented in the generator's
docstring.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "golden" / "literals.json"


# ---------------------------------------------------------------------------
# Helpers (intentionally free of any marker-token plaintext)
# ---------------------------------------------------------------------------


def _decode(leaf: dict[str, str]) -> str:
    """Decode one ``{sha256, hex_utf8}`` leaf back to its plaintext runtime string.

    We assert the SHA-256 matches the hex payload BEFORE decoding so a
    rounding bug or bit-flip in the golden does not silently pass.
    """
    raw = bytes.fromhex(leaf["hex_utf8"])
    expected = hashlib.sha256(raw).hexdigest()
    if leaf["sha256"] != expected:
        raise AssertionError(
            "golden leaf sha256 disagrees with its hex_utf8 payload "
            f"(sha256={leaf['sha256']!r}, payload_len={len(raw)})"
        )
    return raw.decode("utf-8")


def _assert_tree_equal(runtime_tree: object, golden_tree: object, path: tuple[str, ...]) -> None:
    """Walk two trees in lockstep; raise with a precise ``path`` on the first mismatch."""
    if isinstance(golden_tree, list):
        if not isinstance(runtime_tree, (list, tuple)):
            raise AssertionError(
                f"type mismatch at {'/'.join(path)}: runtime={type(runtime_tree).__name__} "
                f"expected list/tuple"
            )
        if len(runtime_tree) != len(golden_tree):
            raise AssertionError(
                f"length mismatch at {'/'.join(path)}: "
                f"runtime={len(runtime_tree)} golden={len(golden_tree)}"
            )
        for i, (rt, gt) in enumerate(zip(runtime_tree, golden_tree, strict=True)):
            _assert_tree_equal(rt, gt, path + (f"[{i}]",))
        return

    if isinstance(golden_tree, dict):
        # Hash leaf shape: {"sha256": ..., "hex_utf8": ...}
        if set(golden_tree.keys()) != {"sha256", "hex_utf8"}:
            raise AssertionError(
                f"unknown leaf shape at {'/'.join(path)}: keys={sorted(golden_tree.keys())}"
            )
        if not isinstance(runtime_tree, str):
            raise AssertionError(
                f"leaf type mismatch at {'/'.join(path)}: "
                f"runtime={type(runtime_tree).__name__} expected str"
            )
        golden_str = _decode(golden_tree)
        if runtime_tree != golden_str:
            raise AssertionError(
                f"field_mismatch at {'/'.join(path)}:\n"
                f"  runtime ({len(runtime_tree)} chars): {runtime_tree!r}\n"
                f"  golden  ({len(golden_str)} chars): {golden_str!r}\n"
                f"  runtime sha256: {hashlib.sha256(runtime_tree.encode()).hexdigest()}\n"
                f"  golden  sha256: {golden_tree['sha256']}"
            )
        return

    raise AssertionError(
        f"unexpected golden node at {'/'.join(path)}: type={type(golden_tree).__name__}"
    )


def _runtime_drills() -> tuple[list[str], list[str], list[str], list[tuple[str, ...]]]:
    """Return ``(ids, names, vectors, keywords)`` for the runtime DRILLS table."""
    inj = importlib.import_module("sunxue_gates.injection_drill")
    ids: list[str] = []
    names: list[str] = []
    vectors: list[str] = []
    keywords: list[tuple[str, ...]] = []
    for d in inj.DRILLS:
        ids.append(d.id)
        names.append(d.name)
        vectors.append(d.vector)
        keywords.append(tuple(d.keywords))
    return ids, names, vectors, keywords


def _runtime_patterns(mod_name: str, *names: str) -> dict[str, tuple[tuple[str, str], ...]]:
    mod = importlib.import_module(mod_name)
    return {n: tuple(getattr(mod, n)) for n in names}


def _runtime_flat(mod_name: str, *names: str) -> dict[str, tuple[str, ...]]:
    mod = importlib.import_module(mod_name)
    return {n: tuple(getattr(mod, n)) for n in names}


def _runtime_server_polyphony_words() -> tuple[str, ...]:
    """Return the local ``words`` tuple inside ``count_server_polyphony``."""
    reg = importlib.import_module("sunxue_gates.regression_output")
    fn = reg.count_server_polyphony
    candidates = [c for c in fn.__code__.co_consts if isinstance(c, tuple) and len(c) > 3]
    assert len(candidates) == 1, (
        f"server-polyphony table discovery broken: {len(candidates)} candidates"
    )
    return tuple(candidates[0])


def _load_golden() -> dict[str, object]:
    assert GOLDEN_PATH.exists(), f"missing golden: {GOLDEN_PATH} — run gen_golden.py first"
    with GOLDEN_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGoldenFileShape:
    """Sanity: the golden file has the expected top-level modules and version."""

    def test_meta_present(self) -> None:
        g = _load_golden()
        assert "_meta" in g
        assert g["_meta"]["generator"] == "tests/golden/gen_golden.py"
        assert g["_meta"]["schema_version"] == 1

    def test_all_four_modules_present(self) -> None:
        g = _load_golden()
        for mod in (
            "sunxue_gates.injection_drill",
            "sunxue_gates.scan_security",
            "sunxue_gates.mutation_drill",
            "sunxue_gates.regression_output",
        ):
            assert mod in g, f"golden missing module {mod}"

    def test_no_plaintext_in_golden(self) -> None:
        """Every golden leaf under the four module tables MUST be the ``{sha256, hex_utf8}`` shape.

        The ``_meta`` block is the only allowed exception (it is generator
        bookkeeping, not a marker-table entry). If a future edit drops a
        plaintext string into any module table — including accidentally
        transcribing a marker token like ``<|im_start|>`` — the test goes
        RED with the exact path.
        """
        g = _load_golden()
        bad: list[str] = []
        MODULE_KEYS = {
            "sunxue_gates.injection_drill",
            "sunxue_gates.scan_security",
            "sunxue_gates.mutation_drill",
            "sunxue_gates.regression_output",
        }

        def walk(node: object, path: str) -> None:
            if isinstance(node, dict):
                keys = set(node.keys())
                if keys == {"sha256", "hex_utf8"}:
                    return  # hash-leaf
                # Otherwise structural container; recurse.
                for k, v in node.items():
                    walk(v, f"{path}.{k}")
                return
            if isinstance(node, list):
                for i, v in enumerate(node):
                    walk(v, f"{path}[{i}]")
                return
            bad.append(f"{path}: raw {type(node).__name__} at non-leaf position")

        # Only audit the module tables — _meta is generator bookkeeping by
        # design and is exempt from the "hash-leaf only" rule.
        for mod_key in MODULE_KEYS:
            walk(g[mod_key], f"$.{mod_key}")
        assert not bad, "golden contains non-hash leaves under a module table:\n" + "\n".join(bad)


class TestInjectionDrillGolden:
    def test_drills_field_by_field(self) -> None:
        g = _load_golden()
        golden: dict[str, list[dict[str, str]]] = g["sunxue_gates.injection_drill"]["DRILLS"]
        ids, names, vectors, keywords = _runtime_drills()

        # ids/name/vector are flat string-list; keywords is list of (tuple of strings).
        _assert_tree_equal(ids, golden["id"], ("DRILLS", "id"))
        _assert_tree_equal(names, golden["name"], ("DRILLS", "name"))
        _assert_tree_equal(vectors, golden["vector"], ("DRILLS", "vector"))
        _assert_tree_equal(keywords, golden["keywords"], ("DRILLS", "keywords"))


class TestScanSecurityGolden:
    def test_pii_patterns(self) -> None:
        g = _load_golden()
        golden = g["sunxue_gates.scan_security"]["PII_PATTERNS"]
        runtime = _runtime_patterns("sunxue_gates.scan_security", "PII_PATTERNS")["PII_PATTERNS"]
        _assert_tree_equal(runtime, golden, ("PII_PATTERNS",))

    def test_secret_patterns(self) -> None:
        g = _load_golden()
        golden = g["sunxue_gates.scan_security"]["SECRET_PATTERNS"]
        runtime = _runtime_patterns("sunxue_gates.scan_security", "SECRET_PATTERNS")[
            "SECRET_PATTERNS"
        ]
        _assert_tree_equal(runtime, golden, ("SECRET_PATTERNS",))

    def test_injection_patterns(self) -> None:
        g = _load_golden()
        golden = g["sunxue_gates.scan_security"]["INJECTION_PATTERNS"]
        runtime = _runtime_patterns("sunxue_gates.scan_security", "INJECTION_PATTERNS")[
            "INJECTION_PATTERNS"
        ]
        _assert_tree_equal(runtime, golden, ("INJECTION_PATTERNS",))

    def test_iter_patterns_concat(self) -> None:
        g = _load_golden()
        golden = g["sunxue_gates.scan_security"]["ITER_PATTERNS"]
        runtime = _runtime_patterns("sunxue_gates.scan_security", "ITER_PATTERNS")["ITER_PATTERNS"]
        _assert_tree_equal(runtime, golden, ("ITER_PATTERNS",))


class TestMutationDrillGolden:
    def test_key_phrases(self) -> None:
        g = _load_golden()
        golden = g["sunxue_gates.mutation_drill"]["KEY_PHRASES"]
        runtime = _runtime_flat("sunxue_gates.mutation_drill", "KEY_PHRASES")["KEY_PHRASES"]
        _assert_tree_equal(runtime, golden, ("KEY_PHRASES",))

    def test_hard_keywords(self) -> None:
        g = _load_golden()
        golden = g["sunxue_gates.mutation_drill"]["HARD_KEYWORDS"]
        runtime = _runtime_flat("sunxue_gates.mutation_drill", "HARD_KEYWORDS")["HARD_KEYWORDS"]
        _assert_tree_equal(runtime, golden, ("HARD_KEYWORDS",))


class TestRegressionOutputGolden:
    def test_deg_adv(self) -> None:
        g = _load_golden()
        golden = g["sunxue_gates.regression_output"]["DEG_ADV"]
        runtime = _runtime_flat("sunxue_gates.regression_output", "DEG_ADV")["DEG_ADV"]
        _assert_tree_equal(runtime, golden, ("DEG_ADV",))

    def test_emo_direct(self) -> None:
        g = _load_golden()
        golden = g["sunxue_gates.regression_output"]["EMO_DIRECT"]
        runtime = _runtime_flat("sunxue_gates.regression_output", "EMO_DIRECT")["EMO_DIRECT"]
        _assert_tree_equal(runtime, golden, ("EMO_DIRECT",))

    def test_server_polyphony_words(self) -> None:
        g = _load_golden()
        golden = g["sunxue_gates.regression_output"]["SERVER_POLYPHONY_WORDS"]
        runtime = _runtime_server_polyphony_words()
        _assert_tree_equal(runtime, golden, ("SERVER_POLYPHONY_WORDS",))


# ---------------------------------------------------------------------------
# Sensitive-bit pin (single-byte contract)
# ---------------------------------------------------------------------------


class TestSingleByteContract:
    """The gate cares about EXACT string equality.

    These tests intentionally pin a single-byte contract: the runtime is
    str-equal to the golden leaf, and the golden leaf is sha256-equal to
    its hex payload. Either assertion fails the moment any byte is
    flipped in either the golden file or the source table.
    """

    def test_leaf_sha256_matches_payload(self) -> None:
        g = _load_golden()
        bad: list[str] = []

        def walk(node: object) -> None:
            if isinstance(node, dict):
                if set(node.keys()) == {"sha256", "hex_utf8"}:
                    payload = bytes.fromhex(node["hex_utf8"])
                    expected = hashlib.sha256(payload).hexdigest()
                    if expected != node["sha256"]:
                        bad.append("sha256 mismatch on leaf")
                    return
                for v in node.values():
                    walk(v)
                return
            if isinstance(node, list):
                for v in node:
                    walk(v)

        walk(g)
        assert not bad, "golden has sha256/hex disagreement on leaves"

    def test_known_anchors_have_real_corpus(self) -> None:
        """Self-check: the corpus we compare against actually contains strings.

        If a future refactor shrinks one of the source tables to empty,
        the field-by-field walk above would happily pass on two empty
        lists. This test catches that degenerate case by requiring at least
        N entries in the headline tables.
        """
        g = _load_golden()
        assert len(g["sunxue_gates.injection_drill"]["DRILLS"]["id"]) == 5
        assert len(g["sunxue_gates.mutation_drill"]["HARD_KEYWORDS"]) >= 5
        assert len(g["sunxue_gates.regression_output"]["DEG_ADV"]) >= 5
        assert len(g["sunxue_gates.regression_output"]["EMO_DIRECT"]) >= 5
        assert len(g["sunxue_gates.scan_security"]["INJECTION_PATTERNS"]) >= 5
