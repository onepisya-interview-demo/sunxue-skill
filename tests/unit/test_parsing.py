"""Unit tests for ``sunxue_gates.parsing``.

Covers:
- ``parse_frontmatter`` — happy paths (single-line + literal block), edge cases
  (no block, empty body, comments, quoted values), and round-trip behavior.
- ``classify_doc`` — SKILL vs reference discrimination.
- ``count_h2`` — heading counting (positive + negative cases).

These exercise the pure helpers; no filesystem or globals.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sunxue_gates.parsing import classify_doc, count_h2, parse_frontmatter

# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_returns_none_without_leading_delimiter(self) -> None:
        assert parse_frontmatter("no frontmatter here\n") is None

    def test_returns_none_when_block_unterminated(self) -> None:
        assert parse_frontmatter("---\nname: x\n") is None

    def test_parses_single_line_entries(self) -> None:
        text = "---\nname: alpha\ndescription: hi\n---\nbody"
        out = parse_frontmatter(text)
        assert out == {"name": "alpha", "description": "hi"}

    def test_strips_double_quotes(self) -> None:
        text = '---\nname: "alpha with spaces"\n---\n'
        assert parse_frontmatter(text) == {"name": "alpha with spaces"}

    def test_strips_single_quotes(self) -> None:
        text = "---\nname: 'beta'\n---\n"
        assert parse_frontmatter(text) == {"name": "beta"}

    def test_empty_value_kept_as_empty_string(self) -> None:
        text = "---\nname: \n---\n"
        out = parse_frontmatter(text)
        assert out == {"name": ""}

    def test_literal_block_takes_precedence_over_single_line(self) -> None:
        # Single-line ``description`` plus literal block for the same key.
        text = "---\nname: alpha\ndescription: |\n  line one\n  line two\n---\n"
        out = parse_frontmatter(text)
        assert out is not None
        assert out["name"] == "alpha"
        # Literal block value is a single space-joined string.
        assert "line one" in out["description"]
        assert "line two" in out["description"]

    def test_skips_comment_lines(self) -> None:
        text = "---\n# this is a comment\nname: alpha\n# trailing comment\n---\n"
        out = parse_frontmatter(text)
        assert out == {"name": "alpha"}

    def test_round_trip_preserves_required_keys(self) -> None:
        """A well-formed frontmatter parses consistently on two passes."""
        text = "---\nname: alpha\ndescription: beta\n---\nbody"
        first = parse_frontmatter(text)
        second = parse_frontmatter(text)
        assert first == second
        assert first is not None
        assert set(first) >= {"name", "description"}

    def test_body_after_block_is_ignored(self) -> None:
        text = (
            "---\nname: alpha\n---\n"
            "# heading\n"
            "name: not_frontmatter\n"  # must NOT leak into the parsed dict
        )
        out = parse_frontmatter(text)
        assert out == {"name": "alpha"}


# ---------------------------------------------------------------------------
# classify_doc
# ---------------------------------------------------------------------------


class TestClassifyDoc:
    @pytest.mark.parametrize(
        "path, expected",
        [
            (Path("SKILL.md"), "SKILL"),
            (Path("references/foo.md"), "reference"),
            (Path("examples/bar.md"), "reference"),
            (Path("nested/path/something.md"), "reference"),
        ],
    )
    def test_classification(self, path: Path, expected: str) -> None:
        assert classify_doc(path) == expected


# ---------------------------------------------------------------------------
# count_h2
# ---------------------------------------------------------------------------


class TestCountH2:
    def test_zero_on_empty(self) -> None:
        assert count_h2("") == 0

    def test_counts_simple_h2(self) -> None:
        text = "\n## first\nbody\n## second\n## third\n"
        assert count_h2(text) == 3

    def test_ignores_h1_and_h3(self) -> None:
        text = "# h1\n## h2\n### h3\n#### h4\n## another h2\n"
        assert count_h2(text) == 2

    def test_no_h2_returns_zero(self) -> None:
        text = "just body text\nno headings here\n"
        assert count_h2(text) == 0
