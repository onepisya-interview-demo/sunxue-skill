#!/usr/bin/env python3
"""
Token 预算: 用字符数 / 3 估算 token。

被测对象:
- /workspace/.skills/sunxue/SKILL.md (单文件)
- /workspace/.skills/sunxue/references/ (全量)
- /workspace/.skills/sunxue/examples/ (全量, 仅作信息参考)

软上限 (用于报警, 不强制):
- SKILL.md 单文件 token <= 8_500 (对应 ~25_000 字符)
- references/ 全量 token <= 16_000 (对应 ~48_000 字符)
- 单个 reference token <= 4_000 (对应 ~12_000 字符)

输出:
- 各文件 token 数
- references/ 总和
- 冷启动时间 (read + 估算, 毫秒)

退出码: 0 = 全部低于软上限, 1 = 至少一项超限
"""
import sys
import time
import pathlib

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_ROOT / "SKILL.md"
REFERENCES_DIR = SKILL_ROOT / "references"
EXAMPLES_DIR = SKILL_ROOT / "examples"

CHARS_PER_TOKEN = 3  # 经验值, 与英文 token 化近似

# 软上限
SOFT_LIMIT = {
    "SKILL.md": 8_500,
    "references_total": 16_000,
    "reference_single": 4_000,
}


def est_tokens(n_chars: int) -> int:
    return n_chars // CHARS_PER_TOKEN


def main() -> int:
    print("=" * 70)
    print("Token 预算 — sunxue skill (chars / 3 估算)")
    print("=" * 70)
    print(f"skill 根目录: {SKILL_ROOT}")

    cold_start_ms = None
    over = 0

    # 1) SKILL.md 单文件
    if SKILL_MD.exists():
        t0 = time.perf_counter()
        text = SKILL_MD.read_text(encoding="utf-8")
        t1 = time.perf_counter()
        cold_start_ms = (t1 - t0) * 1000
        size = len(text)
        tok = est_tokens(size)
        limit = SOFT_LIMIT["SKILL.md"]
        status = "OK  " if tok <= limit else "OVER"
        print(f"\n[SKILL.md] chars={size}  est_tokens={tok}  上限={limit}  [{status}]")
        if tok > limit:
            over += 1
    else:
        print(f"\n[MISS] {SKILL_MD} 不存在")
        over += 1

    # 2) references/ 全量
    total_chars = 0
    total_tok = 0
    if REFERENCES_DIR.exists():
        print(f"\n[references/]")
        for ref in sorted(REFERENCES_DIR.glob("*.md")):
            text = ref.read_text(encoding="utf-8")
            size = len(text)
            tok = est_tokens(size)
            total_chars += size
            total_tok += tok
            single_limit = SOFT_LIMIT["reference_single"]
            status = "OK  " if tok <= single_limit else "OVER"
            print(f"  - {ref.name}  chars={size}  est_tokens={tok}  上限={single_limit}  [{status}]")
            if tok > single_limit:
                over += 1
        total_limit = SOFT_LIMIT["references_total"]
        status = "OK  " if total_tok <= total_limit else "OVER"
        print(f"  -- 合计  chars={total_chars}  est_tokens={total_tok}  上限={total_limit}  [{status}]")
        if total_tok > total_limit:
            over += 1
    else:
        print(f"\n[WARN] references/ 目录不存在: {REFERENCES_DIR}")

    # 3) examples/ (仅信息)
    if EXAMPLES_DIR.exists():
        print(f"\n[examples/] (INFO 仅作参考, 不计入硬上限)")
        ex_total = 0
        ex_count = 0
        for ex in sorted(EXAMPLES_DIR.glob("*.md")):
            text = ex.read_text(encoding="utf-8")
            tok = est_tokens(len(text))
            ex_total += tok
            ex_count += 1
            print(f"  - {ex.name}  est_tokens={tok}  [INFO]")
        print(f"  -- 合计  文件={ex_count}  est_tokens={ex_total}  [INFO]")
    else:
        print(f"\n[examples/] 不存在: {EXAMPLES_DIR}")

    # 4) 冷启动时间
    if cold_start_ms is not None:
        print(f"\n[cold-start] SKILL.md read + 估算耗时: {cold_start_ms:.2f} ms")
    else:
        print(f"\n[cold-start] 不可用 (SKILL.md 缺失)")

    print("\n" + "=" * 70)
    if over == 0:
        print("总结: PASS (全部 token 在软上限内)")
        return 0
    print(f"总结: FAIL (超限 {over} 项)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
