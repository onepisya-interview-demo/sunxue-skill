"""Unit tests for the claims-lint 7th gate (plan 1.2).

The five sub-checks each have a happy path plus at least one failure
mode. The happy-path tests rely on the real repo tree, so they pin the
existing claim wiring (VERSION == pyproject, README freeze annotation,
README directory counts == disk, pyproject thresholds == README claims,
tests/README uv commands == installed CLI). The failure-mode tests use
tmp_path to build a self-contained skill root, so they exercise the
gate's reporting without disturbing the live repo.
"""

from __future__ import annotations

import re
from pathlib import Path

from sunxue_gates.lint_claims import (
    _check_directory_counts,
    _check_skill_freeze,
    _check_thresholds,
    _check_uv_commands,
    _check_version_match,
    _count_top_level_md,
    run,
)
from sunxue_gates.results import GateResult


def _write_minimal_skill(tmp_path: Path) -> Path:
    """Drop the minimum file set that lint_claims reads into tmp_path."""
    (tmp_path / "VERSION").write_text("1.2.3\n", encoding="utf-8")
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\n"
        'name = "sunxue-gates"\n'
        'version = "1.2.3"\n'
        'description = "test fixture"\n'
        'requires-python = ">=3.11"\n'
        "[project.scripts]\n"
        'gates = "sunxue_gates.__main__:main"\n'
        "[dependency-groups]\n"
        'dev = ["ty==0.0.75"]\n'
        "[tool.coverage.report]\n"
        "fail_under = 90\n",
        encoding="utf-8",
    )
    (tmp_path / "references").mkdir()
    (tmp_path / "examples").mkdir()
    (tmp_path / "SKILL.md").write_text(
        "---\nname: sunxue\ndescription: test\n---\n# 孙学 Skill v1.0\n",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# sunxue\n\n"
        "> 元信息冻结：SKILL.md 自 v1.0 起冻结。\n\n"
        "```\n"
        "├── references/                       # 0 个 reference\n"
        "└── examples/                         # 0 个真实样本\n"
        "```\n",
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "README.md").write_text(
        "# tests/README\n"
        "\n"
        "| 命令 |\n"
        "|------|\n"
        "| `uv run pytest` |\n"
        "| `uv run basedpyright` |\n"
        "| `uv run ty check .` |\n"
        "| `uv run ruff check .` |\n"
        "| `uv run ruff format .` |\n"
        "| `uv run gates` |\n"
        "| `uv run diff-cover coverage.xml --fail-under=100` |\n"
        "| `uv run pytest --cov=sunxue_gates --cov-fail-under=90` |\n"
        "| `uv run mutmut run` |\n"
        "| `uv run python -m sunxue_gates` |\n",
        encoding="utf-8",
    )
    # Stub __main__.py so the gates-flag check has something to read.
    src_main_dir = tmp_path / "src" / "sunxue_gates"
    src_main_dir.mkdir(parents=True)
    (src_main_dir / "__main__.py").write_text('"--all"\n"--json"\n', encoding="utf-8")
    return tmp_path


class TestLiveRepoClaims:
    """These tests assume the real skill repo and pin its existing claims."""

    def test_live_version_match(self, skill_root: Path) -> None:
        check = _check_version_match(skill_root)
        assert check.passed is True
        assert check.name == "version_match"

    def test_live_skill_freeze(self, skill_root: Path) -> None:
        check = _check_skill_freeze(skill_root)
        assert check.passed is True

    def test_live_directory_counts(self, skill_root: Path) -> None:
        check = _check_directory_counts(skill_root)
        assert check.passed is True, check.message
        assert "references" in check.detail
        assert "examples" in check.detail

    def test_live_thresholds(self, skill_root: Path) -> None:
        check = _check_thresholds(skill_root)
        assert check.passed is True, check.message

    def test_live_uv_commands(self, skill_root: Path) -> None:
        check = _check_uv_commands(skill_root)
        assert check.passed is True, check.message

    def test_live_full_gate_passes(self, skill_root: Path) -> None:
        gr = run(skill_root)
        assert isinstance(gr, GateResult)
        assert gr.passed is True, "\n".join(c.message for c in gr.details if not c.passed)

    def test_gate_emits_five_subchecks(self, skill_root: Path) -> None:
        gr = run(skill_root)
        assert len(gr.details) == 5
        expected = {
            "version_match",
            "skill_freeze",
            "directory_counts",
            "thresholds",
            "uv_commands_resolvable",
        }
        assert {c.name for c in gr.details} == expected


class TestVersionMatch:
    def test_pass_when_match(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        check = _check_version_match(tmp_path)
        assert check.passed is True

    def test_fail_when_mismatch(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        (tmp_path / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        check = _check_version_match(tmp_path)
        assert check.passed is False
        assert check.detail["version_file"] == "9.9.9"
        assert check.detail["pyproject"] == "1.2.3"

    def test_fail_when_version_missing(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        (tmp_path / "VERSION").unlink()
        check = _check_version_match(tmp_path)
        assert check.passed is False
        assert check.detail["present"] is False

    def test_fail_when_pyproject_missing(self, tmp_path: Path) -> None:
        # ``_check_version_match`` reads ``pyproject.toml`` to get the
        # declared project version. When the file is absent, the helper
        # catches the ``FileNotFoundError`` raised by ``_load_pyproject``
        # and surfaces it as a structured failure with ``detail.err``
        # rather than letting the exception escape (pins lines 126-127).
        _write_minimal_skill(tmp_path)
        (tmp_path / "pyproject.toml").unlink()
        check = _check_version_match(tmp_path)
        assert check.passed is False
        assert check.name == "version_match"
        assert "pyproject.toml" in check.detail["err"]
        assert "[FAIL]" in check.message


class TestSkillFreeze:
    def test_pass_when_annotation_and_v10_present(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        check = _check_skill_freeze(tmp_path)
        assert check.passed is True

    def test_fail_when_annotation_missing(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        (tmp_path / "README.md").write_text("# sunxue\n", encoding="utf-8")
        check = _check_skill_freeze(tmp_path)
        assert check.passed is False
        assert check.detail["present"] is False

    def test_fail_when_skill_md_drifts(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        (tmp_path / "SKILL.md").write_text(
            "---\nname: sunxue\ndescription: drift\n---\n# 孙学 Skill v9.9\n",
            encoding="utf-8",
        )
        check = _check_skill_freeze(tmp_path)
        assert check.passed is False
        assert check.detail["skill_metadata_v10"] is False

    def test_fail_when_skill_md_missing(self, tmp_path: Path) -> None:
        # ``_check_skill_freeze`` first checks the README's freeze
        # annotation, then opens SKILL.md to verify the v1.0 marker
        # text is still present. When SKILL.md is absent the helper
        # must short-circuit with a structured failure (pins line 171)
        # instead of raising FileNotFoundError on the read.
        _write_minimal_skill(tmp_path)
        (tmp_path / "SKILL.md").unlink()
        check = _check_skill_freeze(tmp_path)
        assert check.passed is False
        assert check.name == "skill_freeze"
        assert check.detail == {"present": False}
        assert "不存在" in check.message


class TestDirectoryCounts:
    def test_pass_when_readme_matches_disk(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        check = _check_directory_counts(tmp_path)
        assert check.passed is True

    def test_fail_when_readme_overcounts(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        (tmp_path / "references" / "extra.md").write_text("x", encoding="utf-8")
        check = _check_directory_counts(tmp_path)
        assert check.passed is False
        assert check.detail["references"]["disk"] == 1
        assert check.detail["references"]["claimed"] == 0

    def test_fail_when_readme_undercounts(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        (tmp_path / "README.md").write_text(
            "# sunxue\n"
            "\n"
            "> 元信息冻结：SKILL.md 自 v1.0 起冻结。\n\n"
            "```\n"
            "├── references/                       # 5 个 reference\n"
            "└── examples/                         # 0 个真实样本\n"
            "```\n",
            encoding="utf-8",
        )
        check = _check_directory_counts(tmp_path)
        assert check.passed is False
        assert check.detail["references"]["claimed"] == 5
        assert check.detail["references"]["disk"] == 0

    def test_count_top_level_md_returns_zero_for_missing_dir(self, tmp_path: Path) -> None:
        # ``_count_top_level_md`` is the helper that powers directory-count checks.
        # When the target directory does not exist, the helper must
        # return 0 rather than raising — the gate's report then records
        # ``disk=0`` for that subdir and the README's claimed count is
        # compared against zero. Pins the early-return branch (line 88).
        assert _count_top_level_md("references", tmp_path) == 0
        assert _count_top_level_md("examples", tmp_path) == 0
        # Sanity: an existing empty directory also counts as zero.
        (tmp_path / "empty_dir").mkdir()
        assert _count_top_level_md("empty_dir", tmp_path) == 0
        # Sanity: a non-empty directory counts the .md files inside.
        d = tmp_path / "full_dir"
        d.mkdir()
        (d / "a.md").write_text("x", encoding="utf-8")
        (d / "b.md").write_text("x", encoding="utf-8")
        (d / "c.txt").write_text("x", encoding="utf-8")  # non-.md is ignored
        assert _count_top_level_md("full_dir", tmp_path) == 2


class TestThresholds:
    def test_pass_when_all_consistent(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        check = _check_thresholds(tmp_path)
        assert check.passed is True

    def test_fail_when_coverage_threshold_wrong(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        pyproject_text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
        new_text = pyproject_text.replace("fail_under = 90", "fail_under = 80")
        (tmp_path / "pyproject.toml").write_text(new_text, encoding="utf-8")
        check = _check_thresholds(tmp_path)
        assert check.passed is False
        assert check.detail["pyproject_fail_under"] == 80

    def test_fail_when_ty_pin_missing(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        pyproject_text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
        new_text = pyproject_text.replace('dev = ["ty==0.0.75"]', 'dev = ["ty"]')
        (tmp_path / "pyproject.toml").write_text(new_text, encoding="utf-8")
        check = _check_thresholds(tmp_path)
        assert check.passed is False
        assert check.detail["pyproject_ty_pin"] == ""


class TestUvCommands:
    def test_pass_when_all_resolvable(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        # __main__.py stub is part of the fixture; overwrite to assert both flags.
        (tmp_path / "src" / "sunxue_gates" / "__main__.py").write_text(
            '"--all"\n"--json"\n', encoding="utf-8"
        )
        check = _check_uv_commands(tmp_path)
        assert check.passed is True, check.message

    def test_fail_when_subcommand_unknown(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        (tmp_path / "tests" / "README.md").write_text("| `uv run nonesuch` |\n", encoding="utf-8")
        check = _check_uv_commands(tmp_path)
        assert check.passed is False
        assert "nonesuch" in check.detail["missing"]

    def test_fail_when_gates_script_missing(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
        text = re.sub(r"\[project\.scripts\][^\[]*", "", text)
        (tmp_path / "pyproject.toml").write_text(text, encoding="utf-8")
        check = _check_uv_commands(tmp_path)
        assert check.passed is False
        assert check.detail["gates_script"] is False


class TestGateWiring:
    def test_gate_yields_five_subchecks(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        gr = run(tmp_path)
        assert gr.name == "lint_claims"
        assert len(gr.details) == 5

    def test_gate_fail_summary_lists_failed_names(self, tmp_path: Path) -> None:
        _write_minimal_skill(tmp_path)
        (tmp_path / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("# sunxue\n", encoding="utf-8")
        gr = run(tmp_path)
        assert gr.passed is False
        assert "version_match" in gr.summary
        assert "skill_freeze" in gr.summary
