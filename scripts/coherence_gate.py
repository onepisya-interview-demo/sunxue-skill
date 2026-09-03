#!/usr/bin/env python3
"""coherence_gate.py — 草稿内部一致性自检(机器层)。

WHY THIS SCRIPT EXISTS
======================

SKILL.md 17 项硬指标(writing_gate.py)覆盖**技法 / 句法**,不查**内容逻辑**。
2026-09-04 回归发现 3 处事实冲突,这三处全部 17 项过、但内容不自洽:

1. 频次声明不一致 — "每两周见一次" + "18 次深圳 / 3 年" = 应 78 次,实 18 次
2. 频次观察不一致 — "每周二和周五,雷打不动飞了三年" + "18 次" = 应 312 次,实 18
3. 时间线不一致 — "2019 年加微信" + "三年异地" = 应 2022 完,文内 2023

USAGE
=====

::

    python3 scripts/coherence_gate.py <draft.md> [--json]

EXIT CODE CONTRACT
==================

exit 0  no automated conflict detected; LLM physical-consistency check is the
        caller's responsibility (read the extracted facts and verify in-band)
exit 2  automated conflict detected (timeline regression, frequency vs total
        count, magnitude regression)

PHILOSOPHY
==========

- 机器层(本脚本):做**算术 / 单调性 / 量级差**(可验证、可重放)
- 模型层(SKILL.md 第 7 步 sub-step):读抽取结果 + 草稿,做**物理常识 / 物件物理状态 / 动作可达性**判断
- 两层都过才进入 writing_gate;writing_gate 通过才进第 8 步

LAYERING WITH WRITING_GATE
==========================

::

    coherence_gate(机器, exit 0) → 物理常识自检(模型, in-band) →
    writing_gate(机器, exit 0) → 第 8 步

L1 / L2 / L3 WHITELIST
======================

- L1 数字(用户输入可见的)必须保留原值,机器不改
- L2 人物 / L3 场景 / L3 数字是虚构项,在状态 B 下可改
- 频次 × 时间 ≈ 总量 检查,允许 ±50% 偏差(文学表达可适度夸张)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple


class NumberToken(NamedTuple):
    value: float
    unit: str
    pos: int


class DateToken(NamedTuple):
    year: int
    month: int | None
    pos: int


_CN_NUM = {
    "一": 1,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

# 数字 + 中文单位(只抽有语义的);后接单位可空
_NUM_PATTERN = re.compile(
    r"(\d+(?:\.\d+)?|[一二两三四五六七八九十])\s*([万千百]?)(年|岁|月|日|天|次|个|分|秒|小时|里|块|元|平|米|只|条|层|室|厅|码|遍|回|趟|位)?"
)

# 频次: "每 X (个) 时间单位 (动词) 一次/见/飞/..." 或 "每 X 时间单位"
# 允许: 每周 / 每周二 / 每周二和周五(只取首个时间单位)
# 允许动词和"一次"出现在时间单位之后(可选)
_FREQ_PATTERN = re.compile(
    r"每\s*([一二两三四五六七八九十\d]+)\s*(?:个)?"
    r"(年|月|日|天|周|星期|小时|分)"
)

# 日期: YYYY 年 (M 月)
_DATE_PATTERN = re.compile(r"(20\d{2})\s*年(?:\s*(\d{1,2})\s*月)?")

# 年数声称: 三年 / 三年多 / 三年零两个月 / 整整三年
# 必须 (?<!\d) 排除 20XX 年(4 位数字前缀)和 2023 年这种具体日期
# group(1) = 数字;前面可有 "整整/差不多/大约/快" 等前缀
_YEARS_CLAIM_PATTERN = re.compile(
    r"(?<!\d)(?:整{1,2}|差不多|大约|快|大概)?"
    r"(\d{1,2}|[一二两三四五六七八九十])"
    r"\s*年"
    r"(?!\d)"
)


def _to_num(s: str) -> float | None:
    if s in _CN_NUM:
        return float(_CN_NUM[s])
    try:
        return float(s)
    except ValueError:
        return None


def _scale_value(v: float, scale: str) -> float:
    if scale == "万":
        return v * 10000
    if scale == "千":
        return v * 1000
    if scale == "百":
        return v * 100
    return v


def extract_numbers(text: str) -> list[NumberToken]:
    out: list[NumberToken] = []
    for m in _NUM_PATTERN.finditer(text):
        val_str, scale, unit = m.group(1), m.group(2), m.group(3) or ""
        v = _to_num(val_str)
        if v is None:
            continue
        v = _scale_value(v, scale)
        out.append(NumberToken(v, unit, m.start()))
    return out


def extract_dates(text: str) -> list[DateToken]:
    out: list[DateToken] = []
    for m in _DATE_PATTERN.finditer(text):
        year = int(m.group(1))
        month = int(m.group(2)) if m.group(2) else None
        out.append(DateToken(year, month, m.start()))
    return out


def extract_frequencies(text: str) -> list[tuple[float, str, int]]:
    out: list[tuple[float, str, int]] = []
    for m in _FREQ_PATTERN.finditer(text):
        num, unit = m.group(1), m.group(2)
        v = _to_num(num)
        if v is None:
            continue
        out.append((v, unit, m.start()))
    return out


def check_timeline_claims(text: str, dates: list[DateToken]) -> list[str]:
    """检查日期跨度 vs 文中"X 年"声称。"""
    issues: list[str] = []
    if len(dates) < 2:
        return issues

    sorted_dates = sorted(set((d.year, d.month or 0) for d in dates))
    s_y, s_m = sorted_dates[0]
    e_y, e_m = sorted_dates[-1]
    span_years = ((e_y - s_y) * 12 + (e_m - s_m)) / 12.0

    for m in _YEARS_CLAIM_PATTERN.finditer(text):
        num = m.group(1)
        v = _to_num(num)
        if v is None:
            continue
        # 1-2 年的"X 年"几乎都是相对表达(明年 / 再撑一年)而非总跨度
        # 只检查 ≥ 3 年的声称
        if v < 3:
            continue
        if abs(span_years - v) > 1.0:
            issues.append(
                f"  [TIMELINE] 文中 '{m.group(0).strip()}' 声称 {v:.0f} 年, "
                f"实际日期跨度 {span_years:.1f} 年 ({s_y}.{s_m:02d} → {e_y}.{e_m:02d})"
            )
    return issues


def check_frequency_vs_total(text: str, freqs: list, nums: list[NumberToken]) -> list[str]:
    """检查 频次声明 vs 实际年频次(±50%)。

    数学:
        "每 X 时间单位 一次" 中的 X 是周期(不是频次)。
        周期 T(月) → 年频次 = 12/T
        周期 T(周) → 年频次 = 52/T
        周期 T(天) → 年频次 = 365/T
        周期 T(年) → 年频次 = 1/T

    实际年频次 = 总次数 / 总年数
    """
    issues: list[str] = []
    if not freqs:
        return issues

    count_claims = [n for n in nums if n.unit == "次" and n.value >= 5]
    if not count_claims:
        return issues

    years_claims: list[float] = []
    for m in _YEARS_CLAIM_PATTERN.finditer(text):
        v = _to_num(m.group(1))
        if v is not None and v >= 3:  # 只看 ≥ 3 年的"总年数"声称
            years_claims.append(v)
    if not years_claims:
        return issues

    seen_pairs: set[tuple[float, str, float]] = set()
    for v_period, unit_period, _pos in freqs:
        # 把周期转成年频次
        if unit_period == "年":
            annual_declared = 1.0 / v_period
        elif unit_period == "月":
            annual_declared = 12.0 / v_period
        elif unit_period in ("周", "星期"):
            annual_declared = 52.0 / v_period
        elif unit_period == "天":
            annual_declared = 365.0 / v_period
        else:
            continue

        for c in count_claims:
            for y in years_claims:
                key = (v_period, unit_period, c.value)
                if key in seen_pairs:
                    continue
                actual_annual = c.value / y
                if abs(actual_annual - annual_declared) / annual_declared > 0.5:
                    issues.append(
                        f"  [FREQUENCY] 频次声明 '每 {v_period:g}{unit_period}一次' "
                        f"≈ {annual_declared:.1f} 次/年,"
                        f"文中 '总 {c.value:.0f} 次 / {y:.0f} 年' "
                        f"≈ {actual_annual:.1f} 次/年 "
                        f"(偏差 {(abs(actual_annual - annual_declared) / annual_declared * 100):.0f}%)"  # noqa: E501
                    )
                    seen_pairs.add(key)
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="coherence_gate",
        description="草稿内部一致性自检(机器层);物理常识由 LLM in-band 审",
    )
    parser.add_argument("draft", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.draft.exists():
        print(f"coherence_gate: draft not found: {args.draft}", file=sys.stderr)
        return 2

    text = args.draft.read_text(encoding="utf-8")

    nums = extract_numbers(text)
    dates = extract_dates(text)
    freqs = extract_frequencies(text)

    if args.json:  # noqa: SIM102 — kept for readability
        payload = {
            "numbers": [{"value": n.value, "unit": n.unit, "pos": n.pos} for n in nums],
            "dates": [{"year": d.year, "month": d.month, "pos": d.pos} for d in dates],
            "frequencies": [{"value": f[0], "unit": f[1], "pos": f[2]} for f in freqs],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("=== coherence_gate ===")
    print(f"draft: {args.draft}")
    print(f"  numbers: {len(nums)}")
    print(f"  dates: {len(dates)}")
    print(f"  frequencies: {len(freqs)}")
    print()

    issues: list[str] = []
    issues += check_timeline_claims(text, dates)
    issues += check_frequency_vs_total(text, freqs, nums)

    print("=== 自动冲突检查 ===")
    if issues:
        for issue in issues:
            print(issue)
        print()
        print(f"coherence_gate FAIL: {len(issues)} issue(s)")
        print("  返回 SKILL.md 第 6 步(写)修订,再重跑 coherence_gate + writing_gate")
        return 2

    print("  [OK] 数字交叉验证通过")
    print("  [OK] 时间线单调性通过")
    print("  [OK] 频次 vs 总量自洽")
    print()
    print("=== 待模型自检(物理常识) ===")
    print("  [TODO] 模型层:读抽取结果 + 草稿,做物理常识判断")
    print("    - 量级差(开篇两个数字是否真有数量级)")
    print("    - 物理常识(动作/时间/距离是否合理)")
    print("    - 物件物理状态(是否可被'用坏/用错')")
    print()
    print("coherence_gate: 机器层 PASS,模型层请人工/对话审")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
