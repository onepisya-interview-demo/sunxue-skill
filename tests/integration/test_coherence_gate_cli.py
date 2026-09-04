"""Integration tests for ``scripts/coherence_gate.py``.

Covers:
- CLI exit code contract: 0 on a known-pass fixture, 2 on a known-fail
  fixture (broken.md), with stdout carrying the per-issue report.
- Per-checker detection: timeline regression, frequency regression,
  re-run determinism (synthesis §0 — same script same input same output).
- ``--json`` extraction shape.
- Missing-file argument handling.
- Defensive cases: relative-time expressions ("一年 / 明年 / 再撑一年")
  must not produce false positives.

Fixtures live under ``tests/integration/fixtures/``:
- coherence_broken.md — 3 deliberate fact conflicts (timeline × 2 + frequency × 1)
- coherence_fixed.md — broken.md after manual repair; must pass cleanly

These two fixtures are the regression baseline for §7.2's 档 2 machine
layer. **Do not edit them to "fix" failing tests** — if the script
loses the ability to detect these three conflicts, the test SHOULD
fail and the script is the thing that needs fixing.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._helpers import REPO_ROOT, run_script

SCRIPT = REPO_ROOT / "scripts" / "coherence_gate.py"
FIXTURES = REPO_ROOT / "tests" / "integration" / "fixtures"


def _run(args: list[str], *, stdin_text: str | None = None):
    """Thin shim so the existing test bodies keep using ``_run`` unchanged."""
    return run_script(SCRIPT, args, stdin_text=stdin_text)


class TestCliContract:
    def test_fixed_fixture_exits_zero(self) -> None:
        """coherence_fixed.md (post-repair draft) must pass with exit 0."""
        proc = _run([str(FIXTURES / "coherence_fixed.md")])
        assert proc.returncode == 0, proc.stdout + "\n--stderr--\n" + proc.stderr
        # Stdout must show all three auto-checks passed.
        assert "[OK] 数字交叉验证通过" in proc.stdout
        assert "[OK] 时间线单调性通过" in proc.stdout
        assert "[OK] 频次 vs 总量自洽" in proc.stdout
        # No failure tokens on the happy path.
        assert "FAIL" not in proc.stdout
        assert "FAIL" not in proc.stderr

    def test_broken_fixture_exits_two_with_timeline_and_frequency(self) -> None:
        """coherence_broken.md must fail with at least 1 timeline + 1
        frequency issue — these are the 2026-09-04 regression baseline.

        We assert the **types** of issue the gate must catch rather
        than exact counts: future script tweaks (e.g. new checks) may
        legitimately add issues, but breaking the ability to detect
        timeline or frequency regressions in this fixture is a real
        regression and must fail the test.
        """
        proc = _run([str(FIXTURES / "coherence_broken.md")])
        assert proc.returncode == 2, proc.stdout + "\n--stderr--\n" + proc.stderr
        # Must catch at least one of each: timeline + frequency.
        assert proc.stdout.count("[TIMELINE]") >= 1, (
            f"expected ≥1 TIMELINE issue, got {proc.stdout.count('[TIMELINE]')}\n"
            f"stdout: {proc.stdout}"
        )
        assert proc.stdout.count("[FREQUENCY]") >= 1, (
            f"expected ≥1 FREQUENCY issue, got {proc.stdout.count('[FREQUENCY]')}\n"
            f"stdout: {proc.stdout}"
        )
        # Stderr carries the human/hook-readable failure summary.
        assert "coherence_gate FAIL" in proc.stderr
        assert "Return to SKILL.md" in proc.stderr

    def test_missing_file_exits_two(self) -> None:
        proc = _run(["does-not-exist.md"])
        assert proc.returncode == 2
        assert "draft not found" in proc.stderr

    def test_json_mode_emits_valid_json(self) -> None:
        proc = _run(["--json", str(FIXTURES / "coherence_fixed.md")])
        assert proc.returncode == 0, proc.stdout + "\n--stderr--\n" + proc.stderr
        # Stdout is JSON only (no human banner).
        payload = json.loads(proc.stdout)
        assert "numbers" in payload
        assert "dates" in payload
        assert "frequencies" in payload
        # Each list element is a dict with expected keys.
        for n in payload["numbers"]:
            assert {"value", "unit", "pos"} <= set(n.keys())
        for d in payload["dates"]:
            assert {"year", "month", "pos"} <= set(d.keys())
        for f in payload["frequencies"]:
            assert {"value", "unit", "pos"} <= set(f.keys())

    def test_banner_is_first_three_lines(self) -> None:
        proc = _run([str(FIXTURES / "coherence_fixed.md")])
        first_lines = proc.stdout.splitlines()[:3]
        assert first_lines[0].startswith("=== coherence_gate")
        assert "draft:" in first_lines[1]
        assert "numbers:" in first_lines[2]

    def test_relative_time_expressions_do_not_trigger_timeline_check(self, tmp_path: Path) -> None:
        """Guard against the 1-2 year false positive that bit the first cut.

        Phrases like 「明年」 and 「再撑一年」 are relative-time expressions
        and must NOT be compared against the date span — only ≥3 year
        claims count as total-span claims.
        """
        draft = tmp_path / "relative.md"
        # 2020 → 2023 is 3 years, but the only "X 年" mentions are
        # relative (一年 = "one more year"). No total-span conflict.
        draft.write_text(
            "2020 年某个下午,我加了她微信。\n"
            "她说,我们再撑一年。\n"
            "2021 年我说,加这个项目就要把明年的钱拿出来。\n"
            "她说,好。\n"
            "2023 年 11 月 9 日,我们分开了。\n",
            encoding="utf-8",
        )
        proc = _run([str(draft)])
        # Should NOT report a timeline issue — only "一年" appears,
        # which is excluded by the ≥3 year filter.
        assert "[TIMELINE]" not in proc.stdout, (
            f"false positive on relative time expression:\n{proc.stdout}"
        )

    def test_timeline_only_conflict_exits_two(self, tmp_path: Path) -> None:
        """Synthetic draft with only a timeline conflict — verify the
        timeline checker fires in isolation.
        """
        draft = tmp_path / "timeline_only.md"
        # 2018 + "三年" = 2021 claimed, but 2018 → 2023 = 5 years.
        draft.write_text(
            "2018 年某个下午,我加了她微信。\n2023 年 11 月 9 日,我们分开了。\n三年异地。\n",
            encoding="utf-8",
        )
        proc = _run([str(draft)])
        assert proc.returncode == 2
        assert "[TIMELINE]" in proc.stdout
        assert "[FREQUENCY]" not in proc.stdout

    def test_frequency_only_conflict_exits_two(self, tmp_path: Path) -> None:
        """Synthetic draft with only a frequency conflict."""
        draft = tmp_path / "frequency_only.md"
        # "每两天一次" → 182 次/年, but only 18 total / 3 years = 6/年.
        draft.write_text(
            "2020 年某个下午,我加了她微信。\n"
            "2023 年 11 月 9 日,我们分开了。\n"
            "三年异地,每两天见一次。\n"
            "总共 18 次见面。\n",
            encoding="utf-8",
        )
        proc = _run([str(draft)])
        assert proc.returncode == 2
        assert "[FREQUENCY]" in proc.stdout
        assert "[TIMELINE]" not in proc.stdout


class TestReRunDeterminism:
    def test_repeat_runs_produce_identical_stdout(self) -> None:
        """Same script + same input → same output (synthesis §0).

        Critical for cross-host replay-ability: a CI run must reproduce
        the agent's local result byte-for-byte.
        """
        args = [str(FIXTURES / "coherence_broken.md")]
        a = _run(args)
        b = _run(args)
        assert a.stdout == b.stdout, (
            f"non-deterministic stdout:\n---run 1---\n{a.stdout}\n---run 2---\n{b.stdout}"
        )
        assert a.stderr == b.stderr
        assert a.returncode == b.returncode
