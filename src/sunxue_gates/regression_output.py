"""Gate 3: output regression — verifies the 15 hard metrics in examples/.

Each example under ``examples/`` is checked against a tier-specific
EXPECT table. Three modes are supported (plan 3.1 second half):

- ``writing``: the original 17 EXPECT entries, all strict. Applied
  to samples whose filename starts with ``writing-``.
- ``judgment``: writing-specific counters
  (``「我说好」类`` / ``「我沉默了」类`` / ``服务者复调`` /
  ``物件 callback 标记`` / ``闭环句候选`` / ``场景切换`` / ``程度副词``)
  are relaxed to ``info`` (recorded but never failing). Judgment-relevant
  checks (``数字 >= 10``, ``结尾直接提问 == 1``, plus the universal
  zero-leak lint for 排比/反问/比喻/感叹号/省略号/破折号/引号/情绪直述)
  stay strict. Applied to ``judgment-*`` samples.
- ``meta``: minimum structural lint (排比 == 0, 反问 == 0 strict);
  every other counter is informational. No ``meta-*`` sample ships on
  disk; the mode is wired in for future meta samples.

Each ``CheckResult`` returned by :func:`run` carries the sample's
mode in its ``detail`` mapping so downstream consumers can attribute
failures correctly. ``GateResult.shape`` is unchanged.

The literal DEG_ADV / EMO_DIRECT / SERVER_POLYPHONY_WORDS tables live
in :mod:`sunxue_gates.tables` (plan 2.1); this module re-exports them
under their original attribute names so the golden test and direct
importers keep working.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from .results import CheckResult, GateResult

# SERVER_POLYPHONY_WORDS is imported solely to re-export it under this
# module's attribute path (the golden literal test probes
# ``regression_output.SERVER_POLYPHONY_WORDS``); the runtime code
# uses the local literal ``_WORDS`` inside ``count_server_polyphony``
# (see comment there for why the literal is duplicated).
from .tables import DEG_ADV, EMO_DIRECT, SERVER_POLYPHONY_WORDS  # noqa: F401

Mode = Literal["writing", "judgment", "meta"]

__all__ = [
    "DEG_ADV",
    "EMO_DIRECT",
    "EXPECT",
    "EXPECT_BY_MODE",
    "Mode",
    "count_numbers",
    "count_pai_bi",
    "count_fan_wen",
    "count_metaphor",
    "count_shuo_hao",
    "count_chen_mo",
    "count_server_polyphony",
    "count_object_callback",
    "count_loop_closure",
    "count_scene_break",
    "count_direct_question_end",
    "count_degree",
    "count_emo",
    "count_punct",
    "sample_files",
    "run",
]

# Default tier = writing (the original 17 EXPECT entries, all strict).
# Kept under the original name ``EXPECT`` for backward-compat: callers
# that pass ``expect=EXPECT`` (e.g. the test suite) still see the same
# dict shape; the gate's ``run`` uses the mode-aware merge below.
EXPECT: dict[str, tuple[str, int, str]] = {
    "数字": ("number", 15, ">="),
    "程度副词": ("number", 0, "=="),
    "情绪直述": ("number", 0, "=="),
    "感叹号": ("number", 0, "=="),
    "省略号": ("number", 0, "=="),
    "破折号": ("number", 0, "=="),
    "引号": ("number", 0, "=="),
    "排比": ("number", 0, "=="),
    "反问": ("number", 0, "=="),
    "比喻": ("number", 2, "<="),
    "「我说好」类": ("number", 5, ">="),
    "「我沉默了」类": ("number", 4, ">="),
    "服务者复调": ("number", 3, ">="),
    "物件 callback 标记": ("number", 1, ">="),
    "闭环句候选": ("number", 3, "=="),
    "场景切换": ("number", 6, "<="),
    "结尾直接提问": ("number", 1, "=="),
}

# Per-mode overrides keyed by the same metric labels as EXPECT.
# A value with ``op == 'info'`` is recorded in the CheckResult stream
# but never fails the gate (treated as a passing "INFO" line by
# :func:`_check_text`). Any metric *absent* from the tier dict inherits
# the value from ``EXPECT`` (writing tier) — this keeps tier tables
# small while making the relaxation explicit.
_INFO_OP = "info"

EXPECT_BY_MODE: dict[Mode, dict[str, tuple[str, int, str]]] = {
    # Writing tier is the explicit truth; we don't duplicate the 17
    # entries — falling through to EXPECT for any unspecified metric
    # means a single source of truth.
    "writing": {},
    # Judgment tier: writing-specific technique counters become INFO;
    # the structural close + the digit floor + the universal zero-leak
    # lint remain strict. ``数字`` drops to ``>= 10`` because judgment
    # samples don't pack the same density of facts as writing samples.
    "judgment": {
        "数字": ("number", 10, ">="),
        "程度副词": ("number", 0, _INFO_OP),
        "「我说好」类": ("number", 0, _INFO_OP),
        "「我沉默了」类": ("number", 0, _INFO_OP),
        "服务者复调": ("number", 0, _INFO_OP),
        "物件 callback 标记": ("number", 0, _INFO_OP),
        "闭环句候选": ("number", 0, _INFO_OP),
        "场景切换": ("number", 0, _INFO_OP),
        # 结尾直接提问 stays strict — judgment must close with a concrete
        # ask. ``结尾提问`` only becomes INFO under meta (below).
    },
    # Meta tier: minimum structural lint; almost everything is INFO.
    "meta": {
        "数字": ("number", 0, _INFO_OP),
        "程度副词": ("number", 0, _INFO_OP),
        "情绪直述": ("number", 0, _INFO_OP),
        "感叹号": ("number", 0, _INFO_OP),
        "省略号": ("number", 0, _INFO_OP),
        "破折号": ("number", 0, _INFO_OP),
        "引号": ("number", 0, _INFO_OP),
        "排比": ("number", 0, "=="),  # STRICT — no parallelism
        "反问": ("number", 0, "=="),  # STRICT — no rhetorical questions
        "比喻": ("number", 0, _INFO_OP),
        "「我说好」类": ("number", 0, _INFO_OP),
        "「我沉默了」类": ("number", 0, _INFO_OP),
        "服务者复调": ("number", 0, _INFO_OP),
        "物件 callback 标记": ("number", 0, _INFO_OP),
        "闭环句候选": ("number", 0, _INFO_OP),
        "场景切换": ("number", 0, _INFO_OP),
        "结尾直接提问": ("number", 0, _INFO_OP),
    },
}

# Each sample's mode is derived from its filename prefix. The lookup is
# local to the gate so future samples (e.g. ``meta-*`` once tester-3
# lands them) can be added without touching the four parent gates.
_PREFIX_TO_MODE: tuple[tuple[str, Mode], ...] = (
    ("writing-", "writing"),
    ("judgment-", "judgment"),
    ("meta-", "meta"),
)


def _mode_for_label(label: str) -> Mode:
    """Return the tier mode for a sample label (filename stem).

    Unknown prefixes fall back to ``"writing"`` so newly-named
    samples default to the strict tier instead of silently passing.
    """
    for prefix, mode in _PREFIX_TO_MODE:
        if label.startswith(prefix):
            return mode
    return "writing"


def _merge_expect(mode: Mode) -> dict[str, tuple[str, int, str]]:
    """Build the per-mode EXPECT table by overlaying ``EXPECT_BY_MODE[mode]``
    on top of the writing-tier :data:`EXPECT`.

    A metric missing from the tier dict inherits from the writing tier;
    a metric present in the tier dict *overrides* it (threshold change
    OR relaxation to ``info``). The merged dict is what ``_check_text``
    sees.
    """
    merged: dict[str, tuple[str, int, str]] = dict(EXPECT)
    for metric, spec in EXPECT_BY_MODE[mode].items():
        merged[metric] = spec
    return merged


def cmp(actual: int, expected: int, op: str) -> bool:
    """Apply a comparison op (``==``, ``>=``, ``<=``) and return the boolean."""
    if op == "==":
        return actual == expected
    if op == ">=":
        return actual >= expected
    if op == "<=":
        return actual <= expected
    raise ValueError(f"unsupported op: {op!r}")


def count_numbers(text: str) -> int:
    """Count Chinese-numeral + Arabic-numeral tokens together."""
    cn = len(re.findall(r"[一二三四五六七八九十百千万亿零〇壹贰叁肆伍陆柒捌玖拾佰仟]+", text))
    ar = len(re.findall(r"\b\d+(\.\d+)?\b", text))
    return cn + ar


def count_pai_bi(text: str) -> int:
    """Detect simple 3-term 顿号 parallel structure (``X、Y、Z[，。\n]``)."""
    return len(re.findall(r"、([^、\n]{1,6})、([^、\n]{1,6})、([^、\n]{1,6})[，。\n]", text))


def count_fan_wen(text: str) -> int:
    """Count rhetorical questions in the first 80%% of the body (decoupled from end-question)."""
    body = text[: int(len(text) * 0.8)] if text else text
    return len(re.findall(r"[？\?]", body))


# Metaphor connector: must appear as a complete phrase, not a single character.
# Earlier char-class matcher mis-flagged "好"/"同" inside "我说好"/"合同".
METAPHOR_PATTERN = re.compile(r"(?:仿佛|好似|犹如|貌似|如同[一-龥]{1,4}(?:般|一样|似的))")


def count_metaphor(text: str) -> int:
    """Count metaphor connector phrases using a conservative regex."""
    return len(METAPHOR_PATTERN.findall(text))


def count_shuo_hao(text: str) -> int:
    """Count the "我说好" family of phrases used to mark dialogue co-action."""
    return len(re.findall(r"我说好", text)) + len(re.findall(r"好[,，]?\s*妈妈", text))


def count_chen_mo(text: str) -> int:
    """Count the "我沉默了" / "我没有说" family of silences."""
    return len(
        re.findall(
            r"我沉默了|我没有说|我也没有说|我没有问|我也没有问|我没说话|我没吭声",
            text,
        )
    )


def count_server_polyphony(text: str) -> int:
    """Count mentions of service-worker / low-status roles."""
    # Local literal keeps the table on ``co_consts`` so the golden
    # generator + the golden literal test (which discover it via
    # ``count_server_polyphony.__code__.co_consts``) keep working
    # without any change to their discovery logic. The table is
    # duplicated here ONLY for the co_consts contract; the canonical
    # home remains :mod:`sunxue_gates.tables` (``SERVER_POLYPHONY_WORDS``).
    # The golden literal test enforces byte-level equality between the
    # two views (regenerating ``tests/golden/literals.json`` after a
    # table change will fail loudly if the literal drifts). We don't
    # add an in-function assert because mutmut mutates every string
    # and would constantly trip the guard.
    _WORDS: tuple[str, ...] = (
        "工人",
        "摊主",
        "助理",
        "摄影",
        "导播",
        "化妆",
        "前台",
        "清洁工",
        "服务员",
        "护士",
        "医生",
        "司机",
        "保安",
        "阿姨",
        "老师",
        "同事",
        "师傅",
        "老板",
        "老板娘",
        "小哥",
        "外卖员",
    )
    return sum(text.count(w) for w in _WORDS)


def count_object_callback(text: str) -> int:
    """Count "那个 X" / "它又" object-callback markers."""
    a = len(re.findall(r"那个[一-龥]{1,4}", text))
    b = len(re.findall(r"它又[一-龥]{0,4}", text))
    return a + b


def count_loop_closure(text: str) -> int:
    """Count sentences that appear at least twice in length 4–20 (loop closure candidates)."""
    sents = re.split(r"[。\n]", text)
    counts: Counter[str] = Counter(s.strip() for s in sents if 4 < len(s.strip()) < 20)
    return sum(1 for v in counts.values() if v >= 2)


def count_scene_break(text: str) -> int:
    """Count explicit scene-break separators (``\n---\n`` / ``\n——\n``)."""
    return text.count("\n---\n") + text.count("\n——\n")


def count_direct_question_end(text: str) -> int:
    """Count ``?`` characters in the last 200 chars (decoupled from ``fan_wen``)."""
    tail = text.strip()[-200:]
    return len(re.findall(r"[？\?]", tail))


def count_degree(text: str) -> int:
    """Total occurrences of any degree adverb in :data:`DEG_ADV`."""
    return sum(text.count(w) for w in DEG_ADV)


def count_emo(text: str) -> int:
    """Total occurrences of any direct-emotion phrase in :data:`EMO_DIRECT`."""
    return sum(text.count(p) for p in EMO_DIRECT)


def count_punct(text: str) -> dict[str, int]:
    """Return the four punctuation counters used by the gate."""
    return {
        "感叹号": text.count("！") + text.count("!"),
        "省略号": text.count("……") + text.count("..."),
        "破折号": text.count("——") + text.count("--"),
        "引号": len(re.findall(r"[\u201c\u201d]", text)) + text.count('"'),
    }


# Reference-quote filenames whose name contains ``原文片段`` /
# ``引用片段`` are excluded from the regression scan: they are
# quoted source material, not original-composition samples, so the
# writing-tier counter checks would false-positive on them. The
# exclusion is filename-based (a stable convention carried since
# v1.0.0 baseline) rather than path-based so that future
# testers can drop a new quote file into ``examples/`` without
# touching this gate.
_REFERENCE_QUOTE_MARKERS: tuple[str, ...] = ("原文片段", "引用片段", "实战范例", "反例", "范例")


def sample_files(root: Path) -> list[tuple[str, Path]]:
    """Return the list of example files this gate scans.

    Auto-discovery (plan 3.1 sample-expansion downstream): glob
    ``examples/writing-*.md`` and ``examples/judgment-*.md`` so that any
    new sample tester-2 ships under one of those prefixes is
    picked up automatically. ``meta-*`` and other prefixes are not
    scanned by the regression gate — meta samples have their own
    minimal-lint tier and a future tester-3 will wire them in.
    Files are returned sorted by stem for deterministic gate output
    regardless of filesystem ordering.
    """
    examples = root / "examples"
    samples: list[tuple[str, Path]] = []
    if not examples.exists():
        return samples
    seen: set[Path] = set()
    for pattern in ("writing-*.md", "judgment-*.md"):
        for path in sorted(examples.glob(pattern)):
            if path in seen:
                continue
            if any(marker in path.name for marker in _REFERENCE_QUOTE_MARKERS):
                continue
            seen.add(path)
            samples.append((path.stem, path))
    return samples


def _check_text(
    label: str,
    text: str,
    expect: dict[str, tuple[str, int, str]] | None = None,
    mode: Mode = "writing",
) -> list[CheckResult]:
    """Run every metric in ``expect`` against ``text``; return per-metric checks.

    ``expect`` defaults to the writing-tier :data:`EXPECT` (the original
    17 entries). Pass a custom dict (plan 2.2 dependency injection)
    to exercise alternate rule sets without monkey-patching the module
    global. ``mode`` is recorded on every check's ``detail`` so the
    caller can attribute the result back to its tier.

    An entry with ``op == 'info'`` produces a passing ``[INFO]`` line
    rather than a strict pass/fail check — this is how plan 3.1's
    judgment + meta tiers express "record but don't fail".
    """
    table = EXPECT if expect is None else expect
    checks: list[CheckResult] = [
        CheckResult(
            name=label,
            passed=True,
            message=f"=== {label} (chars={len(text)}, mode={mode}) ===",
            detail={"mode": mode},
        )
    ]

    def record(metric: str, actual: int) -> None:
        spec = table.get(metric)
        if spec is None:
            checks.append(
                CheckResult(
                    name=f"{label}.{metric}",
                    passed=True,
                    message=f"  [INFO] {metric}: {actual}",
                    detail={"actual": actual, "mode": mode, "info": "metric not in tier table"},
                )
            )
            return
        _kind, expected, op = spec
        if op == _INFO_OP:
            # Relaxed tier entry: record, never fail. The "ok" below is
            # unconditional so downstream consumers can rely on a
            # well-formed CheckResult for every expected metric.
            checks.append(
                CheckResult(
                    name=f"{label}.{metric}",
                    passed=True,
                    message=f"  [INFO] {metric}: {actual}  (tier {mode}, relaxed)",
                    detail={
                        "actual": actual,
                        "expected": expected,
                        "op": op,
                        "mode": mode,
                        "relaxed": True,
                    },
                )
            )
            return
        ok = cmp(actual, expected, op)
        checks.append(
            CheckResult(
                name=f"{label}.{metric}",
                passed=ok,
                message=f"  [{'OK' if ok else 'FAIL'}] {metric}: {actual}  (期望 {op} {expected})",
                detail={"actual": actual, "expected": expected, "op": op, "mode": mode},
            )
        )

    record("数字", count_numbers(text))
    record("程度副词", count_degree(text))
    record("情绪直述", count_emo(text))
    for key, val in count_punct(text).items():
        record(key, val)
    record("排比", count_pai_bi(text))
    record("反问", count_fan_wen(text))
    record("比喻", count_metaphor(text))
    record("「我说好」类", count_shuo_hao(text))
    record("「我沉默了」类", count_chen_mo(text))
    record("服务者复调", count_server_polyphony(text))
    record("物件 callback 标记", count_object_callback(text))
    record("闭环句候选", count_loop_closure(text))
    record("场景切换", count_scene_break(text))
    record("结尾直接提问", count_direct_question_end(text))

    return checks


# Helpful type alias for callers (kept here, not exported).
_MetricFn = Callable[[str], int]


def run(
    root: Path,
    expect: dict[str, tuple[str, int, str]] | None = None,
    samples: list[tuple[str, Path]] | None = None,
) -> GateResult:
    """Run the output-regression gate against ``root``.

    ``expect`` defaults to the writing-tier :data:`EXPECT` table (a
    custom dict passed here skips the mode-aware merge entirely and
    applies the same rules to every sample — useful for property
    tests that want to drive a synthetic scenario without going
    through the tier machinery). The normal mode-aware path uses
    :func:`_merge_expect` to overlay the writing tier with the
    per-mode ``EXPECT_BY_MODE`` overrides.

    ``samples`` defaults to :func:`sample_files` (the canonical 5
    hardcoded stems under ``examples/``). Tests may pass a custom
    list to drive synthetic scenarios with new stems or alternate
    modes — the gate still routes each entry through the mode-aware
    expect merge via the stem prefix.
    """
    if samples is None:
        samples = sample_files(root)
    all_checks: list[CheckResult] = []
    miss = 0

    if not samples:
        all_checks.append(
            CheckResult(
                name="examples",
                passed=False,
                message=f"[WARN] examples 目录不存在: {root / 'examples'}",
            )
        )
        miss = 1

    for label, path in samples:
        mode = _mode_for_label(label)
        tier_expect = _merge_expect(mode) if expect is None else expect
        if not path.exists():
            all_checks.append(
                CheckResult(name=label, passed=False, message=f"\n[MISS] {label}: {path} 不存在")
            )
            miss += 1
            continue
        all_checks.extend(
            _check_text(label, path.read_text(encoding="utf-8"), expect=tier_expect, mode=mode)
        )

    failures = sum(1 for c in all_checks if not c.passed)
    passed = failures == 0
    if miss:
        summary = f"FAIL (失败 {failures} 项, 含 {miss} 个文件缺失)"
    elif passed:
        summary = "PASS (所有示例所有硬指标通过)"
    else:
        summary = f"FAIL (失败 {failures} 项)"
    return GateResult(
        name="regression_output",
        passed=passed,
        details=tuple(all_checks),
        summary=f"总结: {summary}",
    )
