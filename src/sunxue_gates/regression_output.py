"""Gate 3: output regression — verifies the 15 hard metrics in examples/.

Each example under ``examples/`` is checked against a fixed table of
``(kind, expected, op)`` rules. Pure counter functions are exposed so a
future worker.test can property-test them with Hypothesis.

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

from .results import CheckResult, GateResult

# SERVER_POLYPHONY_WORDS is imported solely to re-export it under this
# module's attribute path (the golden literal test probes
# ``regression_output.SERVER_POLYPHONY_WORDS``); the runtime code
# uses the local literal ``_WORDS`` inside ``count_server_polyphony``
# (see comment there for why the literal is duplicated).
from .tables import DEG_ADV, EMO_DIRECT, SERVER_POLYPHONY_WORDS  # noqa: F401

__all__ = [
    "DEG_ADV",
    "EMO_DIRECT",
    "EXPECT",
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

# (metric_label) -> (kind, expected, op)
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


def sample_files(root: Path) -> list[tuple[str, Path]]:
    """Return the list of example files this gate scans."""
    examples = root / "examples"
    samples: list[tuple[str, Path]] = []
    if not examples.exists():
        return samples
    candidates = (
        "writing-巴菲特午餐",
        "writing-示例2-被割版",
        "writing-示例3-AI时代前端",
        "judgment-老客户账期",
    )
    for stem in candidates:
        samples.append((stem, examples / f"{stem}.md"))
    return samples


def _check_text(label: str, text: str) -> list[CheckResult]:
    """Run every metric in :data:`EXPECT` against ``text``; return per-metric checks."""
    checks: list[CheckResult] = [
        CheckResult(name=label, passed=True, message=f"=== {label} (chars={len(text)}) ===")
    ]

    def record(metric: str, actual: int) -> None:
        spec = EXPECT.get(metric)
        if spec is None:
            checks.append(
                CheckResult(
                    name=f"{label}.{metric}", passed=True, message=f"  [INFO] {metric}: {actual}"
                )
            )
            return
        _kind, expected, op = spec
        ok = cmp(actual, expected, op)
        checks.append(
            CheckResult(
                name=f"{label}.{metric}",
                passed=ok,
                message=f"  [{'OK' if ok else 'FAIL'}] {metric}: {actual}  (期望 {op} {expected})",
                detail={"actual": actual, "expected": expected, "op": op},
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


def run(root: Path) -> GateResult:
    """Run the output-regression gate against ``root``."""
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
        if not path.exists():
            all_checks.append(
                CheckResult(name=label, passed=False, message=f"\n[MISS] {label}: {path} 不存在")
            )
            miss += 1
            continue
        all_checks.extend(_check_text(label, path.read_text(encoding="utf-8")))

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
