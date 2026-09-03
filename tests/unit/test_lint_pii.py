"""Unit tests for ``sunxue_gates.lint_pii``.

Covers:
- ``PII_LINT_PATTERNS`` shape and hit behavior on synthetic payloads.
- ``scan_text`` against known leak patterns (placeholder emails,
  local agent paths, tool names).
- ``_is_path_exempt`` covering both filename and directory-prefix keys.
- ``collect_lint_files`` under a synthesized tree.
- ``scan_file`` against temporary files, including exemption pass-through.
- ``run(root)`` contract: clean repo PASSES, dirty repo FAILs.
"""

from __future__ import annotations

from pathlib import Path

from sunxue_gates.lint_pii import (
    PII_LINT_PATTERNS,
    _is_path_exempt,
    collect_lint_files,
    run,
    scan_file,
    scan_text,
)
from sunxue_gates.results import GateResult

# ---------------------------------------------------------------------------
# Pattern table shape
# ---------------------------------------------------------------------------


class TestPatternTable:
    def test_every_pattern_has_a_nonempty_label(self) -> None:
        for pat, label in PII_LINT_PATTERNS:
            assert isinstance(pat, str) and pat
            assert isinstance(label, str) and label

    def test_placeholder_local_email_is_detected(self) -> None:
        hits = scan_text("configured author: gates@sunxue.local")
        labels = {lab for lab, _ in hits}
        assert "占位邮箱 (机器身份 / 假身份)" in labels

    def test_real_personal_email_is_not_a_placeholder(self) -> None:
        # Placeholder pattern is .local-only; real domains must not
        # match (they belong to scan_security, not to this gate).
        hits = scan_text("contact: alice@example.com")
        labels = {lab for lab, _ in hits}
        assert "占位邮箱 (机器身份 / 假身份)" not in labels

    def test_hermes_path_is_detected(self) -> None:
        hits = scan_text("see ~/.hermes/memory/agents/ for the role list")
        labels = {lab for lab, _ in hits}
        assert any("~/.hermes" in lab for lab in labels)

    def test_minimax_path_is_detected(self) -> None:
        hits = scan_text("data dir: ~/.minimax/agents/mavis/")
        labels = {lab for lab, _ in hits}
        assert any("~/.minimax" in lab for lab in labels)

    def test_mavis_word_is_detected(self) -> None:
        hits = scan_text("the host agent Mavis responded")
        labels = {lab for lab, _ in hits}
        assert "工具名: Mavis" in labels

    def test_minimax_code_is_detected(self) -> None:
        hits = scan_text("run via minimax-code --all")
        labels = {lab for lab, _ in hits}
        assert "工具链名: minimax-code" in labels

    def test_clean_text_yields_no_hits(self) -> None:
        clean = (
            "This is a normal paragraph of prose.\n"
            "It contains no placeholder emails or system paths.\n"
            "All characters are ASCII letters, spaces, and simple punctuation.\n"
        )
        assert scan_text(clean) == []


# ---------------------------------------------------------------------------
# Path-based exemption
# ---------------------------------------------------------------------------


class TestPathExempt:
    def test_changelog_suppresses_placeholder_email(self) -> None:
        assert _is_path_exempt("CHANGELOG.md", "占位邮箱 (机器身份 / 假身份)") is True

    def test_changelog_does_not_suppress_tool_name(self) -> None:
        # The map lists the placeholder/system-path labels for the
        # changelog but NOT the tool-name labels — leaking a tool
        # name into the changelog is still a fail, because the
        # changelog is public-facing.
        assert _is_path_exempt("CHANGELOG.md", "工具名: Mavis") is False

    def test_notes_prefix_suppresses_all_labels(self) -> None:
        # notes/ is the meta-discussion layer; every label is allowed
        # under it.
        for _, lab in PII_LINT_PATTERNS:
            assert _is_path_exempt("notes/pitfalls.md", lab) is True
            assert _is_path_exempt("notes/sub/dir/x.md", lab) is True

    def test_arbitrary_readme_is_not_exempt(self) -> None:
        for _, lab in PII_LINT_PATTERNS:
            assert _is_path_exempt("README.md", lab) is False
            assert _is_path_exempt("references/x.md", lab) is False
            assert _is_path_exempt("examples/y.md", lab) is False

    def test_plan_md_exempts_system_paths_but_not_tool_names(self) -> None:
        # PLAN.md is the untracked local-only planning archive. It
        # legitimately names the local agent system paths it once
        # documented, so those labels are exempt. Tool-name leaks into
        # PLAN.md would still fail the gate.
        assert _is_path_exempt("PLAN.md", "本地 agent 系统路径 ~/.hermes") is True
        assert _is_path_exempt("PLAN.md", "本地 agent 系统路径 ~/.minimax") is True
        assert _is_path_exempt("PLAN.md", "占位邮箱 (机器身份 / 假身份)") is False
        assert _is_path_exempt("PLAN.md", "工具名: Mavis") is False

    def test_partial_filename_does_not_match(self) -> None:
        # 'CHANGELOG' (no .md) is not the same key as 'CHANGELOG.md'.
        assert _is_path_exempt("CHANGELOG", "占位邮箱 (机器身份 / 假身份)") is False


# ---------------------------------------------------------------------------
# collect_lint_files
# ---------------------------------------------------------------------------


class TestCollectFiles:
    def test_finds_markdown_and_python(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("ok", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("ok", encoding="utf-8")
        (tmp_path / "x.py").write_text("ok", encoding="utf-8")
        (tmp_path / "x.txt").write_text("ok", encoding="utf-8")  # not scanned
        refs = tmp_path / "references"
        refs.mkdir()
        (refs / "r.md").write_text("ok", encoding="utf-8")
        ex = tmp_path / "examples"
        ex.mkdir()
        (ex / "e.md").write_text("ok", encoding="utf-8")
        files = collect_lint_files(tmp_path)
        names = {label for label, _ in files}
        assert "README.md" in names
        assert "pyproject.toml" in names
        assert "x.py" in names
        assert "x.txt" not in names
        assert "references/r.md" in names
        assert "examples/e.md" in names

    def test_skips_gate_own_source(self, tmp_path: Path) -> None:
        # The src/ tree is the gate code itself; scanning it would
        # produce self-hits on every pattern that is documented in
        # the module's docstring.
        src = tmp_path / "src" / "sunxue_gates"
        src.mkdir(parents=True)
        (src / "lint_pii.py").write_text("contains Mavis in docstring", encoding="utf-8")
        files = collect_lint_files(tmp_path)
        assert all("src/sunxue_gates" not in str(p) for _, p in files)


# ---------------------------------------------------------------------------
# scan_file
# ---------------------------------------------------------------------------


class TestScanFile:
    def test_clean_file_passes(self, tmp_path: Path) -> None:
        p = tmp_path / "clean.md"
        p.write_text("hello world\n", encoding="utf-8")
        checks, present = scan_file("clean.md", p, "clean.md")
        assert present is True
        assert all(c.passed for c in checks)

    def test_placeholder_email_in_readme_fails(self, tmp_path: Path) -> None:
        p = tmp_path / "README.md"
        p.write_text("configured: gates@sunxue.local\n", encoding="utf-8")
        checks, present = scan_file("README.md", p, "README.md")
        assert present is True
        assert any(not c.passed for c in checks)

    def test_notes_file_passes_despite_placeholder_email(self, tmp_path: Path) -> None:
        p = tmp_path / "pitfalls.md"
        p.write_text(
            "the bad pattern was gates@sunxue.local — what we did wrong\n",
            encoding="utf-8",
        )
        checks, present = scan_file("notes/pitfalls.md", p, "notes/pitfalls.md")
        assert present is True
        # The label is in the narrative-exempt set for notes/, so the
        # file passes; the suppression count is recorded so the
        # auditor still sees the dropped hit.
        assert all(c.passed for c in checks)
        check = checks[0]
        assert "叙事豁免丢弃 1 条" in check.message
        assert check.detail["narrative_exempt_suppressed"] == 1

    def test_changelog_email_exempt_but_tool_name_fails(self, tmp_path: Path) -> None:
        p = tmp_path / "CHANGELOG.md"
        p.write_text(
            "older entry referenced gates@sunxue.local — clean now\n"
            "current entry mentions Mavis by mistake\n",
            encoding="utf-8",
        )
        checks, present = scan_file("CHANGELOG.md", p, "CHANGELOG.md")
        assert present is True
        # One label was suppressed (the email), one survived (the
        # tool name); the file fails the gate.
        assert any(not c.passed for c in checks)
        check = next(c for c in checks if not c.passed)
        surviving_labels = [d["label"] for d in check.detail["hits"]]
        assert "工具名: Mavis" in surviving_labels
        assert "占位邮箱 (机器身份 / 假身份)" not in surviving_labels

    def test_missing_file_reports_miss(self, tmp_path: Path) -> None:
        checks, present = scan_file("ghost.md", tmp_path / "ghost.md", "ghost.md")
        assert present is False
        assert not checks[0].passed


# ---------------------------------------------------------------------------
# run(root)
# ---------------------------------------------------------------------------


class TestRunGate:
    def test_passes_on_clean_repo(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("clean\n", encoding="utf-8")
        (tmp_path / "SKILL.md").write_text("---\nname: x\n---\nclean\n", encoding="utf-8")
        gr = run(tmp_path)
        assert isinstance(gr, GateResult)
        assert gr.passed is True

    def test_fails_when_readme_contains_placeholder_email(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("configured: gates@sunxue.local\n", encoding="utf-8")
        gr = run(tmp_path)
        assert gr.passed is False

    def test_fails_when_hermes_path_leaks(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "see ~/.hermes/memory/agents for the role list\n", encoding="utf-8"
        )
        gr = run(tmp_path)
        assert gr.passed is False

    def test_passes_when_only_notes_mention_the_tokens(self, tmp_path: Path) -> None:
        notes = tmp_path / "notes"
        notes.mkdir()
        (notes / "pitfalls.md").write_text(
            "the leak was gates@sunxue.local in old commits\n", encoding="utf-8"
        )
        (tmp_path / "README.md").write_text("clean readme\n", encoding="utf-8")
        gr = run(tmp_path)
        assert gr.passed is True

    def test_gate_name_matches_module(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("clean\n", encoding="utf-8")
        gr = run(tmp_path)
        assert gr.name == "lint_pii"
