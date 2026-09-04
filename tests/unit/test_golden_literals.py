"""Unit tests for the literal-provenance golden (plan 1.1).

Threat model
============

The five ``src/sunxue_gates/*.py`` golden modules covered by
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
"unusual" (``<|im_start|>`` → ``<im_start|>`` or ``<|im_start|>`` → "", etc.).
A test that re-states the literal as a Python string in
``tests/**/*.py`` would therefore suffer from the same vulnerability it is
trying to detect. This test deliberately does NOT: it compares every
runtime value against ``tests/golden/literals.json``, which stores ONLY
the SHA-256 + UTF-8 hex of each string, never plaintext.

Triage discipline when a src table changes
=========================================

If you intentionally edit one of the golden-locked src tables, the test will go
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

Type contract
=============

The golden JSON has a precise structural contract that the reader side
enforces through a single validating parser (``_load_golden``). After
parsing, every keyed lookup is against a typed shape (``HashLeaf``
``TypedDict`` + concrete ``list[HashLeaf]`` / ``list[list[HashLeaf]]``
per module table), so basedpyright + ty can catch index-into-``object``
mistakes without resorting to raw ``Any`` casts.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "golden" / "literals.json"


# ---------------------------------------------------------------------------
# Precise structural types (match tests/golden/gen_golden.py exactly).
# ---------------------------------------------------------------------------


if TYPE_CHECKING:
    from typing import TypedDict

    class HashLeaf(TypedDict):
        """One hash-leaf entry as parsed from ``literals.json``."""

        sha256: str
        hex_utf8: str

    class GoldenDRILLS(TypedDict, total=True):
        """``sunxue_gates.injection_drill.DRILLS`` shape after validation."""

        id: list[HashLeaf]
        name: list[HashLeaf]
        vector: list[HashLeaf]
        keywords: list[list[HashLeaf]]

    class GoldenTABLES(TypedDict, total=True):
        """``sunxue_gates.tables`` golden shape (audit-v4 N5)."""

        MUTATION_SYNONYMS: list[list[HashLeaf]]
        MUTATION_SPLIT_WORDS: HashLeaf
        MUTATION_SOFTEN_REPLACEMENTS: list[list[HashLeaf]]
        KNOWN_UV_SUBCOMMANDS: list[list[HashLeaf]]

    class GoldenModule(TypedDict, total=True):
        """Generic module-table wrapper: ``module_name -> {table_name: ...}``.

        The value types vary per module; concrete narrowing happens in
        the per-test helpers below.
        """

    class GoldenTop(TypedDict, total=True):
        """Top-level golden shape, including the audited ``module`` keys."""

        sunxue_gates_injection_drill: GoldenDRILLS  # actually "sunxue_gates.injection_drill"
else:
    HashLeaf = dict
    GoldenTABLES = dict


MOD_KEYS: tuple[str, ...] = (
    "sunxue_gates.injection_drill",
    "sunxue_gates.scan_security",
    "sunxue_gates.mutation_drill",
    "sunxue_gates.regression_output",
    # audit-v4 N5 (v1.3.1): the cluster-A tables relocated into tables.py
    # and the lint_pii pattern table join the hash contract.
    "sunxue_gates.tables",
    "sunxue_gates.lint_pii",
)
SCAN_TABLE_KEYS: tuple[str, ...] = (
    "PII_PATTERNS",
    "SECRET_PATTERNS",
    "INJECTION_PATTERNS",
    "ITER_PATTERNS",
)
REGRESSION_FLAT_KEYS: tuple[str, ...] = ("DEG_ADV", "EMO_DIRECT")
DRILL_FLAT_KEYS: tuple[str, ...] = ("id", "name", "vector")
DRILLS_KEY = "DRILLS"
SERVER_POLYPHONY_KEY = "SERVER_POLYPHONY_WORDS"


# ---------------------------------------------------------------------------
# Leaf decoder + validating loader (single boundary where JSON's loose shape
# is collapsed into the typed shape the rest of this module uses).
# ---------------------------------------------------------------------------


def _decode(leaf: HashLeaf | Mapping[str, str]) -> str:
    """Decode one ``{sha256, hex_utf8}`` leaf back to its plaintext runtime string.

    We assert the SHA-256 matches the hex payload BEFORE decoding so a
    rounding bug or bit-flip in the golden does not silently pass.
    """
    # The walker's leaf branch receives an opaque ``object`` from
    # ``_assert_tree_equal``; after ``isinstance(golden_tree, dict)`` we
    # use ``Mapping[str, str]`` (covariant) so the unknown-key dict from
    # the walker is structurally a valid input here at the static type level.
    raw = bytes.fromhex(leaf["hex_utf8"])
    expected = hashlib.sha256(raw).hexdigest()
    if leaf["sha256"] != expected:
        raise AssertionError(
            "golden leaf sha256 disagrees with its hex_utf8 payload "
            f"(sha256={leaf['sha256']!r}, payload_len={len(raw)})"
        )
    return raw.decode("utf-8")


def _parse_leaf(node: object, path: str) -> HashLeaf:
    """Validate that ``node`` is exactly ``{sha256: str, hex_utf8: str}`` and return it."""
    if not isinstance(node, dict):
        raise AssertionError(f"{path}: expected dict leaf, got {type(node).__name__}")
    keys = set(node.keys())
    if keys != {"sha256", "hex_utf8"}:
        raise AssertionError(f"{path}: unknown leaf shape, keys={sorted(keys)}")
    s = node["sha256"]
    h = node["hex_utf8"]
    if not isinstance(s, str):
        raise AssertionError(f"{path}.sha256: expected str, got {type(s).__name__}")
    if not isinstance(h, str):
        raise AssertionError(f"{path}.hex_utf8: expected str, got {type(h).__name__}")
    return {"sha256": s, "hex_utf8": h}


def _parse_leaf_list(node: object, path: str) -> list[HashLeaf]:
    """Validate that ``node`` is a ``list[HashLeaf]`` (no nesting)."""
    if not isinstance(node, list):
        raise AssertionError(f"{path}: expected list, got {type(node).__name__}")
    return [_parse_leaf(v, f"{path}[{i}]") for i, v in enumerate(node)]


def _parse_leaf_list_list(node: object, path: str) -> list[list[HashLeaf]]:
    """Validate that ``node`` is a ``list[list[HashLeaf]]`` (one level of nesting)."""
    if not isinstance(node, list):
        raise AssertionError(f"{path}: expected list, got {type(node).__name__}")
    out: list[list[HashLeaf]] = []
    for i, v in enumerate(node):
        out.append(_parse_leaf_list(v, f"{path}[{i}]"))
    return out


def _parse_pair_table(node: object, path: str) -> list[list[HashLeaf]]:
    """Validate ``node`` as a list of exactly-``[HashLeaf, HashLeaf]`` rows.

    Used by the audit-v4 N5 modules (tables.py pair tables, KNOWN_UV
    sorted key-value pairs, lint_pii pattern/label rows).
    """
    if not isinstance(node, list):
        raise AssertionError(f"{path}: expected list, got {type(node).__name__}")
    out: list[list[HashLeaf]] = []
    for i, row in enumerate(node):
        p = f"{path}[{i}]"
        if not isinstance(row, list) or len(row) != 2:
            raise AssertionError(f"{p}: expected [leaf, leaf] pair")
        out.append([_parse_leaf(row[0], f"{p}[0]"), _parse_leaf(row[1], f"{p}[1]")])
    return out


def _parse_tables_module(node: object, path: str) -> GoldenTABLES:
    """Validate the ``sunxue_gates.tables`` golden shape (audit-v4 N5)."""
    if not isinstance(node, dict):
        raise AssertionError(f"{path}: expected dict, got {type(node).__name__}")
    expected = {
        "MUTATION_SYNONYMS",
        "MUTATION_SPLIT_WORDS",
        "MUTATION_SOFTEN_REPLACEMENTS",
        "KNOWN_UV_SUBCOMMANDS",
    }
    got = set(node.keys())
    if got != expected:
        raise AssertionError(f"{path}: keys={sorted(got)} expected={sorted(expected)}")
    return {
        "MUTATION_SYNONYMS": _parse_pair_table(
            node["MUTATION_SYNONYMS"], f"{path}.MUTATION_SYNONYMS"
        ),
        "MUTATION_SPLIT_WORDS": _parse_leaf(
            node["MUTATION_SPLIT_WORDS"], f"{path}.MUTATION_SPLIT_WORDS"
        ),
        "MUTATION_SOFTEN_REPLACEMENTS": _parse_pair_table(
            node["MUTATION_SOFTEN_REPLACEMENTS"], f"{path}.MUTATION_SOFTEN_REPLACEMENTS"
        ),
        "KNOWN_UV_SUBCOMMANDS": _parse_pair_table(
            node["KNOWN_UV_SUBCOMMANDS"], f"{path}.KNOWN_UV_SUBCOMMANDS"
        ),
    }


def _parse_pii_module(node: object, path: str) -> dict[str, list[list[HashLeaf]]]:
    """Validate the ``sunxue_gates.lint_pii`` golden shape (audit-v4 N5)."""
    if not isinstance(node, dict):
        raise AssertionError(f"{path}: expected dict, got {type(node).__name__}")
    if set(node.keys()) != {"PII_LINT_PATTERNS"}:
        raise AssertionError(f"{path}: keys={sorted(node.keys())} expected=['PII_LINT_PATTERNS']")
    return {
        "PII_LINT_PATTERNS": _parse_pair_table(
            node["PII_LINT_PATTERNS"], f"{path}.PII_LINT_PATTERNS"
        )
    }


def _parse_drills(node: object, path: str) -> GoldenDRILLS:
    """Validate the DRILLS sub-table shape."""
    if not isinstance(node, dict):
        raise AssertionError(f"{path}: expected dict, got {type(node).__name__}")
    expected = {"id", "name", "vector", "keywords"}
    got = set(node.keys())
    if got != expected:
        raise AssertionError(f"{path}: keys={sorted(got)} expected={sorted(expected)}")
    return {
        "id": _parse_leaf_list(node["id"], f"{path}.id"),
        "name": _parse_leaf_list(node["name"], f"{path}.name"),
        "vector": _parse_leaf_list(node["vector"], f"{path}.vector"),
        "keywords": _parse_leaf_list_list(node["keywords"], f"{path}.keywords"),
    }


def _parse_pattern_table(node: object, path: str) -> list[list[HashLeaf]]:
    """Validate that ``node`` is a ``list[list[HashLeaf]]`` of `(pattern, label)` pairs."""
    if not isinstance(node, list):
        raise AssertionError(f"{path}: expected list, got {type(node).__name__}")
    out: list[list[HashLeaf]] = []
    for i, row in enumerate(node):
        if not isinstance(row, list):
            raise AssertionError(f"{path}[{i}]: expected list, got {type(row).__name__}")
        if len(row) != 2:
            raise AssertionError(f"{path}[{i}]: expected 2 leaves, got {len(row)}")
        out.append([_parse_leaf(row[0], f"{path}[{i}][0]"), _parse_leaf(row[1], f"{path}[{i}][1]")])
    return out


def _parse_scan_module(node: object, path: str) -> dict[str, list[list[HashLeaf]]]:
    """Validate the ``sunxue_gates.scan_security`` shape."""
    if not isinstance(node, dict):
        raise AssertionError(f"{path}: expected dict, got {type(node).__name__}")
    got = set(node.keys())
    expected = set(SCAN_TABLE_KEYS)
    if got != expected:
        raise AssertionError(f"{path}: keys={sorted(got)} expected={sorted(expected)}")
    return {k: _parse_pattern_table(node[k], f"{path}.{k}") for k in SCAN_TABLE_KEYS}


def _parse_flat_string_module(
    node: object, path: str, table_keys: tuple[str, ...]
) -> dict[str, list[HashLeaf]]:
    """Validate modules with flat ``table_name -> list[HashLeaf]`` shape."""
    if not isinstance(node, dict):
        raise AssertionError(f"{path}: expected dict, got {type(node).__name__}")
    got = set(node.keys())
    expected = set(table_keys)
    if got != expected:
        raise AssertionError(f"{path}: keys={sorted(got)} expected={sorted(expected)}")
    return {k: _parse_leaf_list(node[k], f"{path}.{k}") for k in table_keys}


class _ValidatedGoldenShape:
    """Container for the typed golden payload parsed from ``literals.json``.

    Holds the validated module sub-tables (five golden modules since
    audit-v4 N5) in attributes typed as the concrete classes the
    validator produced, so the test classes can index them with full
    static coverage.
    """

    def __init__(
        self,
        *,
        drills: GoldenDRILLS,
        scan: dict[str, list[list[HashLeaf]]],
        mutation: dict[str, list[HashLeaf]],
        regression: dict[str, list[HashLeaf] | list[list[HashLeaf]]],
        tables: GoldenTABLES,
        pii: dict[str, list[list[HashLeaf]]],
        meta: dict[str, object],
    ) -> None:
        self.drills: GoldenDRILLS = drills
        self.scan: dict[str, list[list[HashLeaf]]] = scan
        self.mutation: dict[str, list[HashLeaf]] = mutation
        # ``regression`` has one nested-list entry (SERVER_POLYPHONY_WORDS);
        # the other two are flat. Narrowing happens where the value is read.
        self.regression: dict[str, list[HashLeaf] | list[list[HashLeaf]]] = regression
        self.tables: GoldenTABLES = tables
        self.pii: dict[str, list[list[HashLeaf]]] = pii
        self.meta: dict[str, object] = meta


def _load_golden() -> _ValidatedGoldenShape:
    """Parse ``tests/golden/literals.json`` into the validated typed shape.

    All the untyped ``dict[str, object]`` / ``dict[str, ...]`` indexing
    that would confuse basedpyright / ty is collapsed into one
    boundary here; downstream callers see only the typed sub-tables.
    """
    assert GOLDEN_PATH.exists(), f"missing golden: {GOLDEN_PATH} — run gen_golden.py first"
    with GOLDEN_PATH.open(encoding="utf-8") as fh:
        raw: object = json.load(fh)
    if not isinstance(raw, dict):
        raise AssertionError(f"golden root must be dict, got {type(raw).__name__}")
    root: dict[str, object] = raw
    meta_obj = root.get("_meta")
    if not isinstance(meta_obj, dict):
        raise AssertionError("golden._meta: expected dict")
    for mod_key in MOD_KEYS:
        if mod_key not in root:
            raise AssertionError(f"golden missing module: {mod_key}")
    return _ValidatedGoldenShape(
        drills=_parse_drills(
            root["sunxue_gates.injection_drill"], "$.sunxue_gates.injection_drill"
        ),
        scan=_parse_scan_module(root["sunxue_gates.scan_security"], "$.sunxue_gates.scan_security"),
        mutation=_parse_flat_string_module(
            root["sunxue_gates.mutation_drill"],
            "$.sunxue_gates.mutation_drill",
            ("KEY_PHRASES", "HARD_KEYWORDS"),
        ),
        # ``_parse_flat_string_module`` returns ``dict[str, list[HashLeaf]]``,
        # but ``SERVER_POLYPHONY_WORDS`` is actually a flat string list, so
        # the dict invariance rule for ``_ValidatedGoldenShape`` needs
        # widening via ``cast`` (the runtime shape is checked by the
        # per-table test below).
        regression=cast(  # type: ignore[arg-type]
            "dict[str, list[HashLeaf] | list[list[HashLeaf]]]",
            _parse_flat_string_module(
                root["sunxue_gates.regression_output"],
                "$.sunxue_gates.regression_output",
                REGRESSION_FLAT_KEYS + (SERVER_POLYPHONY_KEY,),
            ),
        ),
        tables=_parse_tables_module(root["sunxue_gates.tables"], "$.sunxue_gates.tables"),
        pii=_parse_pii_module(root["sunxue_gates.lint_pii"], "$.sunxue_gates.lint_pii"),
        meta=meta_obj,
    )


# ---------------------------------------------------------------------------
# Tree-equality walker: runtime tree (object) vs golden tree (leaf-typed).
# ---------------------------------------------------------------------------


def _assert_tree_equal(
    runtime_tree: object,
    golden_tree: object,
    path: tuple[str, ...],
) -> None:
    """Walk two trees in lockstep; raise with a precise ``path`` on the first mismatch.

    The ``golden_tree`` parameter is structurally the same recursive
    shape as ``runtime_tree`` (e.g. ``list[HashLeaf]`` / ``list[list[HashLeaf]]``)
    but at the static type level we type it as ``object`` because the
    shape varies between callsites (the per-test helpers below narrow
    the static type at each callsite, before this generic walk).
    """
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


# ---------------------------------------------------------------------------
# Runtime-side probes (mirror the src tables exactly).
# ---------------------------------------------------------------------------


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


def _runtime_patterns(mod_name: str, name: str) -> tuple[tuple[str, str], ...]:
    mod = importlib.import_module(mod_name)
    return tuple(getattr(mod, name))


def _runtime_flat(mod_name: str, name: str) -> tuple[str, ...]:
    mod = importlib.import_module(mod_name)
    return tuple(getattr(mod, name))


def _runtime_server_polyphony_words() -> tuple[str, ...]:
    """Return the local ``words`` tuple inside ``count_server_polyphony``."""
    reg = importlib.import_module("sunxue_gates.regression_output")
    fn = reg.count_server_polyphony
    candidates = [c for c in fn.__code__.co_consts if isinstance(c, tuple) and len(c) > 3]
    assert len(candidates) == 1, (
        f"server-polyphony table discovery broken: {len(candidates)} candidates"
    )
    return tuple(candidates[0])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGoldenFileShape:
    """Sanity: the golden file has the expected top-level modules and version."""

    def test_meta_present(self) -> None:
        g = _load_golden()
        assert g.meta["generator"] == "tests/golden/gen_golden.py"
        assert g.meta["schema_version"] == 1

    def test_all_modules_present(self) -> None:
        g = _load_golden()
        # All golden modules already validated by ``_load_golden``
        # (four gate modules + tables.py + lint_pii since audit-v4 N5).
        assert g.drills["id"]
        assert g.scan["PII_PATTERNS"]
        assert g.mutation["KEY_PHRASES"]
        assert g.regression["DEG_ADV"]

    def test_no_plaintext_in_golden(self) -> None:
        """Every golden leaf under the module tables MUST be the ``{sha256, hex_utf8}`` shape.

        The ``_meta`` block is the only allowed exception (it is generator
        bookkeeping, not a marker-table entry). If a future edit drops a
        plaintext string into any module table — including accidentally
        transcribing a marker token like ``<|im_start|>`` — the test goes
        RED with the exact path.
        """
        # Validation already enforces this: any deviation raises during
        # ``_load_golden``. The remaining self-check is that we do not
        # accidentally accept a leaf whose keys differ from the canonical
        # pair. Round-trip walking confirms the leaf shape everywhere.
        g = _load_golden()

        def walk(obj: object, path: tuple[str, ...]) -> None:
            if isinstance(obj, dict):
                if set(obj.keys()) == {"sha256", "hex_utf8"}:
                    return  # canonical hash leaf
                # Otherwise structural container; recurse into each field.
                for k, v in obj.items():
                    walk(v, path + (str(k),))
                return
            if isinstance(obj, list):
                for i, v in enumerate(obj):
                    walk(v, path + (f"[{i}]",))
                return
            raise AssertionError(f"non-leaf at {'/'.join(path)}: type={type(obj).__name__}")

        # The four module tables only (the meta block is exempt).
        walk(g.drills, ("drills",))
        walk(g.scan, ("scan",))
        walk(g.mutation, ("mutation",))
        walk(g.regression, ("regression",))


class TestInjectionDrillGolden:
    def test_drills_field_by_field(self) -> None:
        g = _load_golden()
        drills: GoldenDRILLS = g.drills
        ids, names, vectors, keywords = _runtime_drills()

        # ids/name/vector are flat string-list; keywords is list of (tuple of strings).
        _assert_tree_equal(ids, drills["id"], ("DRILLS", "id"))
        _assert_tree_equal(names, drills["name"], ("DRILLS", "name"))
        _assert_tree_equal(vectors, drills["vector"], ("DRILLS", "vector"))
        _assert_tree_equal(keywords, drills["keywords"], ("DRILLS", "keywords"))


class TestScanSecurityGolden:
    def test_pii_patterns(self) -> None:
        g = _load_golden()
        golden = g.scan["PII_PATTERNS"]
        runtime = _runtime_patterns("sunxue_gates.scan_security", "PII_PATTERNS")
        _assert_tree_equal(runtime, golden, ("PII_PATTERNS",))

    def test_secret_patterns(self) -> None:
        g = _load_golden()
        golden = g.scan["SECRET_PATTERNS"]
        runtime = _runtime_patterns("sunxue_gates.scan_security", "SECRET_PATTERNS")
        _assert_tree_equal(runtime, golden, ("SECRET_PATTERNS",))

    def test_injection_patterns(self) -> None:
        g = _load_golden()
        golden = g.scan["INJECTION_PATTERNS"]
        runtime = _runtime_patterns("sunxue_gates.scan_security", "INJECTION_PATTERNS")
        _assert_tree_equal(runtime, golden, ("INJECTION_PATTERNS",))

    def test_iter_patterns_concat(self) -> None:
        g = _load_golden()
        golden = g.scan["ITER_PATTERNS"]
        runtime = _runtime_patterns("sunxue_gates.scan_security", "ITER_PATTERNS")
        _assert_tree_equal(runtime, golden, ("ITER_PATTERNS",))


class TestMutationDrillGolden:
    def test_key_phrases(self) -> None:
        g = _load_golden()
        golden = g.mutation["KEY_PHRASES"]
        runtime = _runtime_flat("sunxue_gates.mutation_drill", "KEY_PHRASES")
        _assert_tree_equal(runtime, golden, ("KEY_PHRASES",))

    def test_hard_keywords(self) -> None:
        g = _load_golden()
        golden = g.mutation["HARD_KEYWORDS"]
        runtime = _runtime_flat("sunxue_gates.mutation_drill", "HARD_KEYWORDS")
        _assert_tree_equal(runtime, golden, ("HARD_KEYWORDS",))


class TestRegressionOutputGolden:
    def test_deg_adv(self) -> None:
        g = _load_golden()
        golden = g.regression["DEG_ADV"]
        runtime = _runtime_flat("sunxue_gates.regression_output", "DEG_ADV")
        _assert_tree_equal(runtime, golden, ("DEG_ADV",))

    def test_emo_direct(self) -> None:
        g = _load_golden()
        golden = g.regression["EMO_DIRECT"]
        runtime = _runtime_flat("sunxue_gates.regression_output", "EMO_DIRECT")
        _assert_tree_equal(runtime, golden, ("EMO_DIRECT",))

    def test_tables_module_round_trip(self) -> None:
        """audit-v4 N5: tables.py 的 4 张表逐字符串与 golden 解码相等。"""
        g = _load_golden()
        tables = importlib.import_module("sunxue_gates.tables")

        syn = [[_decode(a), _decode(b)] for a, b in g.tables["MUTATION_SYNONYMS"]]
        assert syn == [list(p) for p in tables.MUTATION_SYNONYMS]

        assert _decode(g.tables["MUTATION_SPLIT_WORDS"]) == tables.MUTATION_SPLIT_WORDS

        soft = [[_decode(a), _decode(b)] for a, b in g.tables["MUTATION_SOFTEN_REPLACEMENTS"]]
        assert soft == [list(p) for p in tables.MUTATION_SOFTEN_REPLACEMENTS]

        uv = [[_decode(k), _decode(v)] for k, v in g.tables["KNOWN_UV_SUBCOMMANDS"]]
        assert dict(uv) == tables.KNOWN_UV_SUBCOMMANDS

    def test_pii_module_round_trip(self) -> None:
        """audit-v4 N5 / v3-F3 收口：lint_pii 词表进 golden 后逐对相等。"""
        g = _load_golden()
        lint_pii = importlib.import_module("sunxue_gates.lint_pii")
        rows = [[_decode(pat), _decode(label)] for pat, label in g.pii["PII_LINT_PATTERNS"]]
        assert rows == [list(p) for p in lint_pii.PII_LINT_PATTERNS]

    def test_server_polyphony_words(self) -> None:
        g = _load_golden()
        poly_leaves: list[HashLeaf] = cast("list[HashLeaf]", g.regression["SERVER_POLYPHONY_WORDS"])
        runtime = _runtime_server_polyphony_words()
        _assert_tree_equal(runtime, poly_leaves, ("SERVER_POLYPHONY_WORDS",))


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

        def walk(obj: object, path: tuple[str, ...]) -> None:
            if isinstance(obj, dict):
                if set(obj.keys()) != {"sha256", "hex_utf8"}:
                    return  # not a hash leaf (e.g. _meta); skip
                payload = bytes.fromhex(obj["hex_utf8"])
                expected = hashlib.sha256(payload).hexdigest()
                if expected != obj["sha256"]:
                    raise AssertionError(f"sha256 mismatch on leaf at {'/'.join(path)}")
                return
            if isinstance(obj, list):
                for i, v in enumerate(obj):
                    walk(v, path + (f"[{i}]",))

        walk(g.drills, ("drills",))
        walk(g.scan, ("scan",))
        walk(g.mutation, ("mutation",))
        walk(g.regression, ("regression",))

    def test_known_anchors_have_real_corpus(self) -> None:
        """Self-check: the corpus we compare against actually contains strings.

        If a future refactor shrinks one of the source tables to empty,
        the field-by-field walk above would happily pass on two empty
        lists. This test catches that degenerate case by requiring at least
        N entries in the headline tables.
        """
        g = _load_golden()
        assert len(g.drills["id"]) == 5
        assert len(g.mutation["HARD_KEYWORDS"]) >= 5
        assert len(g.regression["DEG_ADV"]) >= 5
        assert len(g.regression["EMO_DIRECT"]) >= 5
        assert len(g.scan["INJECTION_PATTERNS"]) >= 5
        # audit-v4 N5: keep the new modules honest too.
        assert len(g.tables["MUTATION_SYNONYMS"]) >= 3
        assert len(g.tables["KNOWN_UV_SUBCOMMANDS"]) >= 5
        assert len(g.pii["PII_LINT_PATTERNS"]) >= 3
