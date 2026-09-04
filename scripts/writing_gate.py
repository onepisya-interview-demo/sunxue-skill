#!/usr/bin/env python3
"""writing_gate.py — standalone delivery-side gate for sunxue skill drafts.

WHY THIS SCRIPT EXISTS (synthesis §0 / §4.1)
=============================================

The 16 hard-metric counters already live in
``sunxue_gates.regression_output`` (used by the dev-side ``gates --all``
to check ``examples/``). What is missing is a single-file runner that
applies those SAME counters to a freshly-written draft and emits a
PASS/FAIL line per metric, so:

1. **L1 in SKILL.md can become "produce evidence"** rather than
   "self-evaluate": the rule is now "run this script, paste its raw
   stdout verbatim" — the user / CI can re-run the same script on the
   same draft and verify the conclusion independently.
2. **A future Claude Code ``Stop`` hook** (档 2, NOT this script) can
   invoke the same script as a sub-process and refuse to end the turn
   on a non-zero exit. The script is host-agnostic by design — it has
   no dependency on Claude Code, hooks, or any agent runtime.

This script is therefore the **single source of truth** for the
delivery-time contract. Both humans and machines read the same stdout.

EXIT CODE CONTRACT (synthesis §1.1 公理 4)
==========================================

exit 0  all strict metrics pass              → "deliverable"
exit 1  RESERVED (unused today: every INFO-level relaxation already
        returns 0; kept so 档 2 can introduce "soft-OK" without a
        breaking change — do not build on it yet)
exit 2  one or more strict metrics failed, bad args, or missing draft
        → "block, return to step 6"

stderr is reserved for the failure summary so a Stop hook can echo it
back to the agent (Claude Code's Stop event does exactly that).
stdout is the per-metric line the agent must paste verbatim.

CROSS-HOST HONESTY NOTE
=======================

The script works on every host with Python 3.11+ and the sunxue-gates
package installed. What varies between hosts is HOW the exit code is
consumed:

- Claude Code: frontmatter ``hooks.Stop`` → ``scripts/stop_gate.py``
  wrapper around this script.
- Other hosts (Cursor / Codex / ZCode / raw CLI): no such hook;
  deliverability reduces to "agent runs the script, pastes the
  output, human / CI replays it" — i.e. verification instead of
  interception. Lower enforcement tier, identical determinism.

USAGE
=====

::

    python3 scripts/writing_gate.py <draft.md> [--mode writing|judgment|meta|yingxue]

UNKNOWN METRICS / FUTURE WORK
=============================

档 1 of the synthesis ships 17 of the 19 documented metrics. The two
that are NOT yet implemented (and that the gate reports as INFO):

- 第 10 项 打破节拍句"恰好 1 次 @ 80% 位置" — requires the agent to
  nominate a candidate sentence in-band; hybrid probability+determinism
  (synthesis §1.2 半可判). Implementation deferred to 档 2.
- 第 14 项 遗留物清单 ≥5 且降序 — needs end-of-text list extraction
  (synthesis §1.2 句法/结构). Implementation deferred to 档 2.

The script emits an explicit ``[INFO] metric-NN: ...`` line for each,
so the user can see the gap rather than discovering it after the fact.

档 1 also defers the ``--whitelist`` argument (虚构红线, 第 16 项).
When absent, the gate fails closed: any draft that names a number not
in the user-supplied whitelist is blocked. To be useful, a real
deployment needs the agent to feed a whitelist from the user prompt
落地 — that is 档 2 work.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Single source of truth: reuse the counters and the tier table.  Do NOT
# duplicate counter implementations into this script (synthesis §4.1
# 复用策略 — duplicating would create drift; the project already has
# a ``golden literal`` test guarding against exactly that for
# ``SERVER_POLYPHONY_WORDS``).
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

try:
    from sunxue_gates.regression_output import (  # noqa: E402  (sys.path tweak above)
        Mode,
        _check_text,
        _merge_expect,
    )
except ImportError as exc:  # F10 (v1.3.1): bare python3 outside the repo venv
    sys.stderr.write(
        "writing_gate: cannot import sunxue_gates. Run from the repo with "
        "`uv run python scripts/writing_gate.py ...` (or `uv sync` / "
        f"`pip install -e .` first).\n  underlying error: {exc}\n"
    )
    raise SystemExit(2) from exc

# Metrics known to the script today: 17 total (matches the EXPECT
# table / regression_output docstring). Items 1-15 are the original
# 技法 counters plus 闭环句候选; 16-17 (场景切换 / 结尾直接提问) are
# strict writing-tier checks. The 档 2 placeholders are NOT here —
# they live in _DEFERRED_INFO below and emit INFO lines only.
_TIER_INFO_NOTE = "(机器判不了，走 SKILL.md 第 8 步)"
_KNOWN_METRICS: tuple[str, ...] = (
    "数字",
    "程度副词",
    "情绪直述",
    "感叹号",
    "省略号",
    "破折号",
    "引号",
    "排比",
    "反问",
    "比喻",
    "「我说好」类",
    "「我沉默了」类",
    "服务者复调",
    "物件 callback 标记",
    "闭环句候选",
    "场景切换",
    "结尾直接提问",
)
_DEFERRED_INFO: tuple[tuple[str, str], ...] = (
    (
        "第 10 项 打破节拍句位置",
        "档 2: 需 agent 标注候选句后机器验'恰好 1 次 @ 80% 位置'",
    ),
    (
        "第 14 项 遗留物清单",
        "档 2: 尾段列表抽取 + 长度 ≥ 5 且降序",
    ),
    (
        "第 16 项 虚构红线",
        "档 2: --whitelist 选项（缺省 fail-closed）",
    ),
    ("致命自检", _TIER_INFO_NOTE),
    ("最后一问 / 朗读测试", _TIER_INFO_NOTE),
    ("闭环句『量级逐次放大』", _TIER_INFO_NOTE),
)


def _banner(draft: Path, mode: Mode) -> str:
    return (
        f"=== writing_gate (档 1 周末档最小可用) ===\n"
        f"  draft: {draft}\n"
        f"  mode:  {mode}\n"
        f"  known metrics: {len(_KNOWN_METRICS)} (deferred: {len(_DEFERRED_INFO)})\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="writing_gate",
        description=(
            "Apply the sunxue skill 17 hard metrics to a draft. "
            "Exit 0 = pass, 2 = strict fail (exit 1 reserved). "
            "Re-run on the same draft to verify."
        ),
    )
    parser.add_argument("draft", type=Path, help="Path to the draft .md file")
    parser.add_argument(
        "--mode",
        choices=("writing", "judgment", "meta", "yingxue"),
        default="writing",
        help="Which tier of EXPECT_BY_MODE to apply (default: writing). "
        "yingxue wired in v1.3.1 (audit-v4 CR-N1) — EXPECT_BY_MODE had "
        "the tier since v1.2.1.",
    )
    args = parser.parse_args(argv)

    if not args.draft.exists():
        sys.stderr.write(f"writing_gate: draft not found: {args.draft}\n")
        return 2

    text = args.draft.read_text(encoding="utf-8")
    mode: Mode = args.mode
    tier_expect = _merge_expect(mode)

    print(_banner(args.draft, mode))

    # 1) Run every known metric through the existing _check_text.
    checks = _check_text(label=args.draft.name, text=text, expect=tier_expect, mode=mode)
    # Print the banner line and the per-metric lines exactly as
    # _check_text produced them. The agent must paste THIS output.
    for c in checks:
        print(c.message)

    # 2) Emit INFO lines for the 档 2 deferred items so the user
    # sees the gap rather than finding it later.
    print()
    print("=== 档 2 待补 (INFO only) ===")
    for name, note in _DEFERRED_INFO:
        print(f"  [INFO] {name}: -- ({note})")

    # 3) Compute the exit code.
    strict_failures = [c for c in checks if not c.passed and c.detail.get("op") != "info"]
    if strict_failures:
        sys.stderr.write(
            f"\nwriting_gate FAIL: {len(strict_failures)} strict metric(s) failed.\n"
            f"  Return to SKILL.md step 6 (写) and address each failure below.\n"
        )
        for c in strict_failures:
            sys.stderr.write(f"  - {c.name}: {c.message.strip()}\n")
        return 2
    # exit 1 reserved for "soft OK" — a future "info-only relaxation
    # that we still want humans to notice" channel. Today every metric
    # is either strict-pass or INFO-relaxed, so exit 1 is unused; we
    # keep the contract defined so 档 2 can introduce it without a
    # breaking change.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
