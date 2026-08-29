"""Unit tests for ``sunxue_gates.lint_structure``.

Exercises the structural-lint gate against synthesized skill trees so we can
cover both the PASS and FAIL paths without depending on the real repo.
"""

from __future__ import annotations

from pathlib import Path

from sunxue_gates.lint_structure import (
    MAX_H2_HEADINGS,
    REQUIRED_FRONTMATTER,
    REQUIRED_SECTION_GROUPS,
    SIZE_LIMITS,
    run,
)
from sunxue_gates.results import GateResult


def _write_skill(tmp_path: Path, body: str) -> None:
    text = "---\nname: x\ndescription: y\n---\n" + body
    (tmp_path / "SKILL.md").write_text(text, encoding="utf-8")


class TestConstants:
    def test_required_frontmatter_keys(self) -> None:
        assert "name" in REQUIRED_FRONTMATTER
        assert "description" in REQUIRED_FRONTMATTER

    def test_three_required_section_groups(self) -> None:
        assert len(REQUIRED_SECTION_GROUPS) == 3

    def test_size_limits_split_by_kind(self) -> None:
        assert SIZE_LIMITS["SKILL"] > SIZE_LIMITS["reference"]

    def test_max_h2_headings_is_positive(self) -> None:
        assert MAX_H2_HEADINGS > 0


class TestRunGate:
    def test_pass_on_minimal_valid_skill(self, tmp_path: Path) -> None:
        # Body that hits all three required section groups and stays under
        # every limit.
        body = "第一原则\n触发词\n红线\n"
        _write_skill(tmp_path, body)
        gr = run(tmp_path)
        assert isinstance(gr, GateResult)
        assert gr.passed is True

    def test_fail_when_skill_missing(self, tmp_path: Path) -> None:
        gr = run(tmp_path)
        assert gr.passed is False

    def test_fail_when_frontmatter_missing(self, tmp_path: Path) -> None:
        # Body hits all section groups but no frontmatter at all.
        body = "第一原则\n触发词\n红线\n"
        (tmp_path / "SKILL.md").write_text(body, encoding="utf-8")
        gr = run(tmp_path)
        assert gr.passed is False
        # The frontmatter.check is one of the failing checks.
        assert any(".frontmatter" in c.name and not c.passed for c in gr.details)

    def test_fail_when_required_section_group_missing(self, tmp_path: Path) -> None:
        # Frontmatter present, but no 'red-line' keyword anywhere.
        body = "第一原则\n触发词\n其他无关内容\n"
        _write_skill(tmp_path, body)
        gr = run(tmp_path)
        assert gr.passed is False
        # At least one of the section checks fails.
        assert any(".section" in c.name and not c.passed for c in gr.details)

    def test_fail_when_skill_over_size_limit(self, tmp_path: Path) -> None:
        # Generate content just past SIZE_LIMITS['SKILL'].
        limit = SIZE_LIMITS["SKILL"]
        body = "第一原则\n触发词\n红线\n" + ("a" * (limit + 100))
        _write_skill(tmp_path, body)
        gr = run(tmp_path)
        assert gr.passed is False
        assert any(c.name.endswith(".size") and not c.passed for c in gr.details)

    def test_fail_when_h2_count_exceeds_limit(self, tmp_path: Path) -> None:
        # Generate MAX_H2_HEADINGS + 5 H2 lines.
        body = "第一原则\n触发词\n红线\n" + (
            "\n".join(f"## heading {i}" for i in range(MAX_H2_HEADINGS + 5)) + "\n"
        )
        _write_skill(tmp_path, body)
        gr = run(tmp_path)
        assert gr.passed is False
        assert any(c.name.endswith(".h2_count") and not c.passed for c in gr.details)

    def test_references_directory_optional(self, tmp_path: Path) -> None:
        body = "第一原则\n触发词\n红线\n"
        _write_skill(tmp_path, body)
        # No references/ directory at all.
        gr = run(tmp_path)
        assert gr.passed is True

    def test_references_file_validated(self, tmp_path: Path) -> None:
        body = "第一原则\n触发词\n红线\n"
        _write_skill(tmp_path, body)
        refs = tmp_path / "references"
        refs.mkdir()
        # Reference under the limit and without required section groups
        # (section groups apply only to SKILL, so a tiny ref should pass).
        (refs / "tiny.md").write_text("small content\n", encoding="utf-8")
        gr = run(tmp_path)
        assert gr.passed is True

    def test_references_file_too_large(self, tmp_path: Path) -> None:
        body = "第一原则\n触发词\n红线\n"
        _write_skill(tmp_path, body)
        refs = tmp_path / "references"
        refs.mkdir()
        (refs / "big.md").write_text("a" * (SIZE_LIMITS["reference"] + 100), encoding="utf-8")
        gr = run(tmp_path)
        assert gr.passed is False
        assert any("references/big.md.size" in c.name and not c.passed for c in gr.details)
