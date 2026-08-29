"""Hypothesis property tests for ``sunxue_gates``.

Each test states a REAL invariant in a comment above the body. max_examples
is capped at 100 to keep the suite fast; ``deadline=None`` because Chinese
text generation plus regex work can exceed the default 200ms deadline.
"""

from __future__ import annotations

import string

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from sunxue_gates.mutation_drill import mutate_soften, mutate_split, mutate_synonym
from sunxue_gates.parsing import classify_doc, count_h2, parse_frontmatter
from sunxue_gates.regression_output import count_degree, count_numbers
from sunxue_gates.scan_security import _scan_text
from sunxue_gates.token_budget import est_tokens

# ---------------------------------------------------------------
# Custom strategies
# ---------------------------------------------------------------

# A bounded alphabet of safe characters for "benign text": ASCII letters,
# digits, spaces, common punctuation. Avoids accidentally triggering the
# regex detectors.
_safe_ascii = st.text(
    alphabet=st.sampled_from(string.ascii_letters + string.digits + " .,:;-'\n"),
    min_size=0,
    max_size=400,
)


# ---------------------------------------------------------------
# Property 1: est_tokens monotone in chars and equals chars // 3
# ---------------------------------------------------------------


# Invariant: est_tokens(n) == n // 3 for every n >= 0 (definition).
@given(st.integers(min_value=0, max_value=10_000_000))
@settings(max_examples=100, deadline=None)
def test_est_tokens_equals_floor_div(n: int) -> None:
    assert est_tokens(n) == n // 3


# Invariant: est_tokens is monotone non-decreasing in chars.
# We feed a SORTED sequence so the assertion has a chance to hold.
@given(st.lists(st.integers(min_value=0, max_value=1_000_000), min_size=2, max_size=50).map(sorted))
def test_est_tokens_monotone_in_chars(ns: list[int]) -> None:
    for a, b in zip(ns, ns[1:], strict=False):
        assert est_tokens(a) <= est_tokens(b)


# ---------------------------------------------------------------
# Property 2: frontmatter parser never raises on arbitrary text
# ---------------------------------------------------------------


# Invariant: parse_frontmatter is total — it returns None or a dict and
# never raises, regardless of the input shape.
@given(st.text(min_size=0, max_size=2000))
@settings(max_examples=100, deadline=None)
def test_parse_frontmatter_never_raises(text: str) -> None:
    out = parse_frontmatter(text)
    assert out is None or isinstance(out, dict)
    if out is not None:
        for k, v in out.items():
            assert isinstance(k, str)
            assert isinstance(v, str)


# Invariant: parse_frontmatter round-trips well-formed frontmatter.
@given(
    st.lists(
        st.tuples(
            st.text(
                alphabet=st.sampled_from(string.ascii_lowercase + "_"),
                min_size=1,
                max_size=10,
            ).filter(lambda s: ":" not in s and " " not in s),
            st.text(
                alphabet=st.sampled_from(string.ascii_letters + string.digits + " "),
                min_size=0,
                max_size=20,
            ),
        ),
        min_size=1,
        max_size=4,
    )
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
def test_parse_frontmatter_round_trip(pairs: list[tuple[str, str]]) -> None:
    # Build a well-formed block with unique keys (frontmatter last-write-wins).
    seen: list[str] = []
    lines: list[str] = []
    for k, v in pairs:
        if k in seen:
            continue
        seen.append(k)
        # Empty values become 'name: ' — which is allowed.
        lines.append(f"{k}: {v}")
    text = "---\n" + "\n".join(lines) + "\n---\nbody"
    out = parse_frontmatter(text)
    assert out is not None
    # Every key we wrote must appear in the parsed dict.
    for k in seen:
        assert k in out


# Invariant: classify_doc is a stable binary classifier (SKILL only if
# filename is literally SKILL.md).
@given(st.text(min_size=1, max_size=20))
def test_classify_doc_is_binary(name: str) -> None:
    out = classify_doc(__import__("pathlib").Path(name))
    assert out in {"SKILL", "reference"}


# Invariant: count_h2 is monotone in appending more '## ' headings.
@given(
    base=st.text(max_size=200),
    heads=st.lists(
        st.text(alphabet=st.sampled_from(string.ascii_lowercase + " "), min_size=1, max_size=20),
        min_size=0,
        max_size=10,
    ),
)
@settings(max_examples=100, deadline=None)
def test_count_h2_monotone_appending(base: str, heads: list[str]) -> None:
    before = count_h2(base)
    after = count_h2(base + "".join(f"\n## {h}\n" for h in heads))
    assert after >= before
    assert after >= before + len(heads)


# ---------------------------------------------------------------
# Property 3: PII/secret detectors
# ---------------------------------------------------------------


# Invariant: every synthesized Chinese mobile number is detected.
# Pattern: ``\b1[3-9]\d{9}\b`` — 11 digits total, 2nd digit in 3..9.
@given(
    st.sampled_from(list("3456789")).flatmap(
        lambda d2: st.integers(min_value=10_000_000, max_value=99_999_999).map(
            lambda rest: f"1{d2}{rest:08d}1"  # 1 + d2 + 9-digit body
        )
    )
)
@settings(max_examples=100, deadline=None)
def test_synthetic_mobile_phones_detected(phone: str) -> None:
    hits = _scan_text(f"联系 {phone} 即可。")
    assert hits, f"phone {phone!r} not detected"


# Invariant: every synthesized OpenAI-style API key is detected.
@given(
    st.text(
        alphabet=st.sampled_from(string.ascii_letters + string.digits),
        min_size=25,
        max_size=40,
    )
)
@settings(max_examples=100, deadline=None)
def test_synthetic_api_keys_detected(payload: str) -> None:
    text = f"key: sk-{payload}"
    hits = _scan_text(text)
    assert hits, f"OpenAI-style key with payload {payload!r} not detected"


# Invariant: random "benign" text yields no hits (false-positive bound).
# We restrict to ASCII letters/digits/spaces plus a curated set of CJK
# punctuation that does NOT collide with the INJECTION_PATTERNS regexes.
@given(
    st.text(
        alphabet=st.sampled_from(
            string.ascii_letters
            + string.digits
            + " .,;:'-?!()\n"
            + "的一是了我不在有他和那这就上个们来到时大里说"
            + "，。！？、；：「」『』（）"
        ),
        min_size=0,
        max_size=400,
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
def test_benign_text_yields_no_hits(text: str) -> None:
    hits = _scan_text(text)
    assert hits == [], "benign text triggered false positives: " + repr(text) + " -> " + str(hits)


# ---------------------------------------------------------------
# Property 4: mutation operators
# ---------------------------------------------------------------


# Invariant: every mutator produces output != input when the input
# contains at least one of the operator's table mappings. M2 (split)
# always changes text (inserts the conjunction or appends a marker).
# We feed inputs that contain at least one M1/M3 keyword.
MUTATOR_HITTING_INPUTS = (
    "你必须改写这一段。",  # hits M1 (必须→务必) AND M3 (必须→建议)
    "你不要用这个。",  # hits M1 (不要→请勿) AND M3 (不要→尽量不要)
)


@given(st.sampled_from(MUTATOR_HITTING_INPUTS))
@settings(max_examples=100, deadline=None)
def test_mutators_change_input(text: str) -> None:
    assert mutate_synonym(text) != text
    assert mutate_split(text) != text
    assert mutate_soften(text) != text


# Invariant: mutators are deterministic — same input → same output twice.
@given(_safe_ascii)
@settings(max_examples=100, deadline=None)
def test_mutators_deterministic(text: str) -> None:
    assert mutate_synonym(text) == mutate_synonym(text)
    assert mutate_split(text) == mutate_split(text)
    assert mutate_soften(text) == mutate_soften(text)


# Invariant: mutate_soften removes any 'strong word' that appears in its
# table from the output. We feed a sentence that contains every banned
# word and assert NONE survive.
@given(
    st.sampled_from(
        [
            "你必须这样写，不要那样写。",
            "务必请勿严禁应该改写。",
            "严禁触碰开关。",
        ]
    )
)
@settings(max_examples=100, deadline=None)
def test_soften_removes_strong_words(text: str) -> None:
    out = mutate_soften(text)
    for banned in ("必须", "务必", "请勿", "严禁"):
        # '不要' and '应该' can also appear in the softened output as
        # part of the soft replacements, so we only pin the strict ones.
        assert banned not in out, (banned, out)


# ---------------------------------------------------------------
# Property 5: commutative counters
# ---------------------------------------------------------------


# Invariant: count_numbers is invariant under sentence permutation.
# (It's a global count of digit tokens, not a sentence-wise operation.)
@given(
    st.lists(
        st.text(
            alphabet=st.sampled_from(string.ascii_letters + string.digits + " "),
            min_size=1,
            max_size=30,
        ),
        min_size=2,
        max_size=8,
    )
)
@settings(max_examples=100, deadline=None)
def test_count_numbers_permutation_invariant(sents: list[str]) -> None:
    forward = "。".join(sents)
    backward = "。".join(reversed(sents))
    assert count_numbers(forward) == count_numbers(backward)


# Invariant: count_degree is invariant under sentence permutation.
@given(
    st.lists(
        st.sampled_from(
            [
                "今天非常冷。",
                "他格外紧张。",
                "普通描述。",
                "极其严重的事。",
            ]
        ),
        min_size=2,
        max_size=8,
    )
)
@settings(max_examples=100, deadline=None)
def test_count_degree_permutation_invariant(sents: list[str]) -> None:
    forward = "\n".join(sents)
    backward = "\n".join(reversed(sents))
    assert count_degree(forward) == count_degree(backward)


# Invariant: count_numbers is monotone non-decreasing when appending
# text containing digits.
@given(
    base=st.text(alphabet=st.sampled_from(string.ascii_letters + " "), max_size=100),
    extra=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=100, deadline=None)
def test_count_numbers_monotone(base: str, extra: int) -> None:
    before = count_numbers(base)
    after = count_numbers(base + f" {extra} ")
    assert after >= before + 1  # the appended integer contributes at least 1
