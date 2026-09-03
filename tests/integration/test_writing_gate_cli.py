"""Integration tests for ``scripts/writing_gate.py``.

Covers:
- CLI exit code contract: 0 on a known-pass example, 2 on a synthetic
  failing draft, with stderr carrying the failure summary.
- Stdout shape: PASS/FAIL/INFO per-metric lines + deferred-INFO block.
- ``--mode judgment`` downgrades the writing-specific counters to INFO
  (synthesis §1.2 半可判 — these are 概率判定+确定性行刑 hybrid).
- Unknown / missing draft argument handling.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


# Repo root — discovered by walking up from this test file until we
# find a directory that is the *real* sunxue-skill repo root, not a
# mutmut sandbox.
#
# mutmut 3.x's runner copies ``pyproject.toml`` + ``src/`` + ``tests/``
# under a ``mutants/`` directory and ``chdir``s into it before
# invoking pytest. A naive ``pyproject.toml + src/`` check would
# match ``mutants/`` and resolve SCRIPT to the wrong path. The
# disambiguator is the ``scripts/`` directory: it lives only at the
# real repo root, never in the mutmut sandbox.
def _find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (
            (candidate / "pyproject.toml").is_file()
            and (candidate / "src").is_dir()
            and (candidate / "scripts").is_dir()
        ):
            return candidate
    raise RuntimeError(
        f"could not locate repo root (no pyproject.toml + src/ + scripts/ above {start})"
    )


REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
SCRIPT = REPO_ROOT / "scripts" / "writing_gate.py"


def _run(args: list[str], *, stdin_text: str | None = None) -> subprocess.CompletedProcess[str]:
    """Invoke the CLI with ``args`` and capture stdout/stderr separately."""
    return subprocess.run(  # noqa: S603 — intentional CLI invocation in tests
        [sys.executable, str(SCRIPT), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        input=stdin_text,
    )


class TestCliContract:
    def test_pass_example_exits_zero(self) -> None:
        # 巴菲特午餐 is a known-pass example (every metric green under
        # the writing tier). Run it as the canary.
        proc = _run(["examples/writing-巴菲特午餐.md"])
        assert proc.returncode == 0, proc.stdout + "\n--stderr--\n" + proc.stderr
        # Stdout is the per-metric block the agent must paste verbatim.
        assert "[OK] 数字" in proc.stdout
        assert "[OK] 结尾直接提问" in proc.stdout
        # 档 2 deferred items are surfaced as INFO so the user sees
        # the gap rather than discovering it after the fact.
        assert "档 2 待补" in proc.stdout
        assert "第 10 项 打破节拍句位置" in proc.stdout
        # Stderr is silent on the happy path — the failure summary
        # block is reserved for failures.
        assert "FAIL" not in proc.stderr

    def test_synthetic_bad_draft_exits_two(self, tmp_path: Path) -> None:
        # Craft a draft that fails every strict metric: too few
        # numbers, lots of degree adverbs, lots of emotional outburst,
        # excessive punctuation, zero 服务者, zero 物件 callback, etc.
        bad = tmp_path / "bad.md"
        bad.write_text(
            "这篇文章非常非常地好！我的心好痛苦呀，泪流满面！"
            "这是不是最好的感情？？？真的是太爱了！！"
            "我沉默了。我说我好难过。我说我好痛苦。\n",
            encoding="utf-8",
        )
        proc = _run([str(bad)])
        assert proc.returncode == 2, proc.stdout + "\n--stderr--\n" + proc.stderr
        # Stdout shows the per-metric failures.
        assert "[FAIL] 数字" in proc.stdout
        assert "[FAIL] 程度副词" in proc.stdout
        # Stderr carries the human/hook-readable failure summary.
        assert "writing_gate FAIL" in proc.stderr
        assert "Return to SKILL.md step 6" in proc.stderr
        # Each failure surfaces by name in stderr.
        assert "数字" in proc.stderr
        assert "程度副词" in proc.stderr

    def test_missing_file_exits_two(self) -> None:
        proc = _run(["does-not-exist.md"])
        assert proc.returncode == 2
        assert "draft not found" in proc.stderr

    def test_judgment_mode_relaxes_writing_metrics_to_info(self) -> None:
        # Under --mode judgment, the writing-specific technique
        # counters (「我说好」类, 「我沉默了」类, 服务者复调, 物件
        # callback, 闭环句, 场景切换) should be reported as [INFO]
        # rather than strict. Run the same example that passes
        # writing — under judgment it must still exit 0 because the
        # relaxations remove the strict floor.
        proc = _run(["--mode", "judgment", "examples/writing-巴菲特午餐.md"])
        assert proc.returncode == 0, proc.stdout + "\n--stderr--\n" + proc.stderr
        # The relaxed counters show up as [INFO] lines.
        assert "[INFO] 「我说好」类" in proc.stdout
        assert "[INFO] 服务者复调" in proc.stdout

    def test_banner_is_first_three_lines(self) -> None:
        proc = _run(["examples/writing-巴菲特午餐.md"])
        first_lines = proc.stdout.splitlines()[:3]
        assert first_lines[0].startswith("=== writing_gate")
        assert "draft:" in first_lines[1]
        assert "mode:" in first_lines[2]


class TestReRunDeterminism:
    def test_repeat_runs_produce_identical_stdout(self) -> None:
        # The whole point of the script (synthesis §0) is that
        # ``同一脚本同一输入必得同一输出`` — re-running on the same
        # draft must produce byte-identical stdout (and stderr).
        args = ["examples/writing-巴菲特午餐.md"]
        a = _run(args)
        b = _run(args)
        assert a.stdout == b.stdout
        assert a.stderr == b.stderr
        assert a.returncode == b.returncode
