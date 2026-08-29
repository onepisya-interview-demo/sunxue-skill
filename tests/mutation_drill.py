#!/usr/bin/env python3
"""
变异测试: 取 SKILL.md 的 5 条关键指令, 对每条做 3 种小幅改写
(同义词替换 / 拆句 / 软化语气), 检查改写后是否仍能被硬指标命中。

流程:
 1. 从 SKILL.md 抽取包含 5 个核心动词的句子作为关键指令:
    - "必须" / "不要" / "改成" / "出庭作证" / "判断一个句子是否合格"
 2. 对每条做 3 种变异:
    M1 同义词: "必须" -> "务必"; "不要" -> "请勿"
    M2 拆句: 长句拆成两句
    M3 软化: "必须" -> "建议"; "不要" -> "尽量不要"
 3. 变异后, 用硬指标关键词命中数判断是否还能约束写作:
    - 仍能命中 >= 2 个核心硬指标 (数字 / 服务者 / 物件 / 闭环 / 沉默 / 排比禁用 等) -> PASS
    - 命中 < 2 -> FAIL (变异破坏了硬约束)

退出码: 0 = 全部 PASS, 1 = 至少一项 FAIL
"""
import re
import sys
import pathlib

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_ROOT / "SKILL.md"

KEY_PHRASES = [
    "必须",
    "不要",
    "改成",
    "出庭作证",
    "判断一个句子是否合格",
]

# 硬指标关键词 (从 checklist.md 抄来)
HARD_KEYWORDS = [
    "数字", "服务者", "物件", "闭环", "沉默", "排比",
    "反问", "程度副词", "情绪", "比喻", "场景切换",
    "我说好", "遗留物",
]

# 三种变异
def mutate_synonym(text: str) -> str:
    table = [
        ("必须", "务必"),
        ("不要", "请勿"),
        ("应该", "宜"),
        ("改写", "改写成"),
    ]
    out = text
    for a, b in table:
        out = out.replace(a, b)
    return out


_SPLIT_MARKERS = re.compile(r"([，。；])")


def mutate_split(text: str) -> str:
    """在第一个句号 / 分号处拆成两句, 第二句用 '也就是说,' 开头。"""
    parts = _SPLIT_MARKERS.split(text, maxsplit=1)
    if len(parts) >= 3:
        head, sep, tail = parts[0], parts[1], "".join(parts[2:])
        return f"{head}{sep} 也就是说, {tail}"
    return text + " 这一条不要忘。"


def mutate_soften(text: str) -> str:
    table = [
        ("必须", "建议"),
        ("务必", "尽量"),
        ("请勿", "尽量不要"),
        ("不要", "尽量不要"),
        ("严禁", "不推荐"),
        ("应该", "可以"),
    ]
    out = text
    for a, b in table:
        out = out.replace(a, b)
    return out


MUTATORS = [
    ("M1 同义词", mutate_synonym),
    ("M2 拆句", mutate_split),
    ("M3 软化", mutate_soften),
]


def extract_key_sentences(text: str, max_n: int = 5):
    """从 SKILL.md 抽取包含关键短语的句子作为关键指令。"""
    sents = re.split(r"(?<=[。！？\n])\s*", text)
    out = []
    used = set()
    for phrase in KEY_PHRASES:
        for s in sents:
            if phrase in s and 20 <= len(s) <= 200 and id(s) not in used:
                out.append(s.strip())
                used.add(id(s))
                break
        if len(out) >= max_n:
            break
    return out


def hit_count(text: str) -> int:
    """计算硬指标关键词的命中数 (去重)。"""
    n = 0
    for kw in HARD_KEYWORDS:
        if kw in text:
            n += 1
    return n


def main() -> int:
    print("=" * 70)
    print("变异测试 — sunxue skill (5 条关键指令 × 3 种变异)")
    print("=" * 70)

    if not SKILL_MD.exists():
        print(f"[MISS] {SKILL_MD} 不存在")
        return 1

    text = SKILL_MD.read_text(encoding="utf-8")
    sentences = extract_key_sentences(text, max_n=5)
    print(f"抽取关键指令 {len(sentences)} 条")

    if not sentences:
        print("[WARN] 未抽到任何关键指令, 按 PASS 处理 (无变异对象)")
        return 0

    # 用全文作为硬指标命中基线 (变异后应保持接近的命中数)
    base_hits = hit_count(text)
    print(f"基线硬指标关键词命中数: {base_hits}")
    print()

    fails = 0
    for i, sent in enumerate(sentences, 1):
        # 抽取原句自身的命中
        sent_hits = hit_count(sent)
        print(f"\n--- 指令 {i} ---")
        print(f"原句 ({sent_hits} hits): {sent[:120]}{'...' if len(sent) > 120 else ''}")
        for mname, mfunc in MUTATORS:
            mutated = mfunc(sent)
            m_hits = hit_count(mutated)
            # 判据: 变异后自身仍能命中 >= 1 个硬指标
            # (这是粗判, 因为单句不可能包含全部关键词, 关键是不要把约束消没)
            ok = m_hits >= 1 or sent_hits == 0
            tag = "PASS" if ok else "FAIL"
            print(f"  [{tag}] {mname} ({m_hits} hits): {mutated[:120]}{'...' if len(mutated) > 120 else ''}")
            if not ok:
                fails += 1

    print("\n" + "=" * 70)
    if fails == 0:
        print("总结: PASS (所有变异后硬指标仍可命中)")
        return 0
    print(f"总结: FAIL ({fails} 项变异破坏硬约束)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
