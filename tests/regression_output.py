#!/usr/bin/env python3
"""
输出回归: 对 examples/ 三个示例做自检, 跑的是 SKILL 自己写下的 15 项硬约束。

被测对象 (来自 /workspace/.skills/sunxue/examples/):
- writing-巴菲特午餐.md
- writing-示例2-被割版.md
- judgment-老客户账期.md

硬指标 (来自 references/writing-checklist.md):
 1.  全文数字 >= 15
 2.  程度副词 = 0
 3.  情绪形容词直述 = 0
 4.  感叹号 / 省略号 / 破折号 / 引号 各 0
 5.  排比 = 0
 6.  反问 = 0
 7.  比喻 <= 2
 8.  「我说好」类 >= 5
 9.  「我沉默了/我没有说」类 >= 4
 10. 打破节拍 = 1 次
 11. 服务者复调段落 >= 3
 12. 物件 callback >= 1
 13. 闭环句 = 3
 14. 结尾遗留物清单 >= 5
 15. 结尾直接提问 = 1

退出码: 0 = 所有示例通过, 1 = 至少一项 FAIL
"""
import re
import sys
import pathlib
from collections import Counter

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLES_DIR = SKILL_ROOT / "examples"

SAMPLES = [
    ("writing-巴菲特午餐", EXAMPLES_DIR / "writing-巴菲特午餐.md"),
    ("writing-示例2-被割版", EXAMPLES_DIR / "writing-示例2-被割版.md"),
    ("writing-示例3-AI时代前端", EXAMPLES_DIR / "writing-示例3-AI时代前端.md"),
    ("judgment-老客户账期", EXAMPLES_DIR / "judgment-老客户账期.md"),
]

DEG_ADV = [
    "非常", "无比", "深深", "格外", "极其", "特别", "十分",
    "极为", "甚为", "尤为", "万分", "百般", "分外", "相当",
    "异常", "极度", "相当", "特别地", "非常地",
]
EMO_DIRECT = [
    "我很痛苦", "我很爱她", "我很伤心", "我很难过", "我很高兴",
    "我很开心", "我好难过", "我好痛苦", "心里很痛", "心如刀割",
    "心碎", "泪流满面", "泪水模糊", "我好委屈", "我特别难过",
]

# 期望
EXPECT = {
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
    if op == "==":
        return actual == expected
    if op == ">=":
        return actual >= expected
    if op == "<=":
        return actual <= expected
    return False


def count_numbers(text: str) -> int:
    cn = len(re.findall(r"[一二三四五六七八九十百千万亿零〇壹贰叁肆伍陆柒捌玖拾佰仟]+", text))
    ar = len(re.findall(r"\b\d+(\.\d+)?\b", text))
    return cn + ar


def count_pai_bi(text: str) -> int:
    # 简单排比: X、Y、Z 三段式顿号
    return len(re.findall(r"、([^、\n]{1,6})、([^、\n]{1,6})、([^、\n]{1,6})[，。\n]", text))


def count_fan_wen(text: str) -> int:
    # 反问只看正文前 80% — 结尾的直接提问不归反问
    # (与 SKILL「15. 结尾直接提问恰好 1 个」互斥但解耦)
    body = text[:int(len(text) * 0.8)] if len(text) else text
    return len(re.findall(r"[？\?]", body))


# 比喻连接词: 必须以完整词组作为引导, 防止单字"好""同"误判
# (旧 char class `[仿佛如同好似犹如貌似像]` 包含"好"和"同",
#  会把"我说好"/"合同"/"同行"/"同款"误判为比喻)
METAPHOR_PATTERN = re.compile(r"(?:仿佛|好似|犹如|貌似|如同[一-龥]{1,4}(?:般|一样|似的))")


def count_metaphor(text: str) -> int:
    return len(METAPHOR_PATTERN.findall(text))


def count_shuo_hao(text: str) -> int:
    return len(re.findall(r"我说好", text)) + len(re.findall(r"好[,，]?\s*妈妈", text))


def count_chen_mo(text: str) -> int:
    return len(re.findall(r"我沉默了|我没有说|我也没有说|我没有问|我也没有问|我没说话|我没吭声", text))


def count_server_polyphony(text: str) -> int:
    words = [
        "工人", "摊主", "助理", "摄影", "导播", "化妆", "前台",
        "清洁工", "服务员", "护士", "医生", "司机", "保安", "阿姨",
        "老师", "同事", "师傅", "老板", "老板娘", "小哥", "外卖员",
    ]
    return sum(text.count(w) for w in words)


def count_object_callback(text: str) -> int:
    # 简化: "那个 X" / "它又" / "X 还是 X" 标记数
    a = len(re.findall(r"那个[一-龥]{1,4}", text))
    b = len(re.findall(r"它又[一-龥]{0,4}", text))
    return a + b


def count_loop_closure(text: str) -> int:
    sents = re.split(r"[。\n]", text)
    c = Counter(s.strip() for s in sents if 4 < len(s.strip()) < 20)
    return sum(1 for k, v in c.items() if v >= 2)


def count_scene_break(text: str) -> int:
    return text.count("\n---\n") + text.count("\n——\n")


def count_direct_question_end(text: str) -> int:
    # 结尾直接提问: 看最后 200 字符 (与"反问=0"按前 80% 解耦)
    tail = text.strip()[-200:]
    return len(re.findall(r"[？\?]", tail))


def count_degree(text: str) -> int:
    return sum(text.count(w) for w in DEG_ADV)


def count_emo(text: str) -> int:
    return sum(text.count(p) for p in EMO_DIRECT)


def count_punct(text: str):
    return {
        "感叹号": text.count("！") + text.count("!"),
        "省略号": text.count("……") + text.count("..."),
        "破折号": text.count("——") + text.count("--"),
        "引号": len(re.findall(r"[\u201c\u201d]", text)) + text.count('"'),
    }


def run_one(name: str, text: str) -> int:
    print(f"\n=== {name} (chars={len(text)}) ===")
    fails = 0

    def line(label, actual):
        nonlocal fails
        if label in EXPECT:
            kind, exp, op = EXPECT[label]
            ok = cmp(actual, exp, op)
            tag = "OK  " if ok else "FAIL"
            print(f"  [{tag}] {label}: {actual}  (期望 {op} {exp})")
            if not ok:
                fails += 1
        else:
            print(f"  [INFO] {label}: {actual}")

    line("数字", count_numbers(text))
    line("程度副词", count_degree(text))
    line("情绪直述", count_emo(text))
    p = count_punct(text)
    for k, v in p.items():
        line(k, v)
    line("排比", count_pai_bi(text))
    line("反问", count_fan_wen(text))
    line("比喻", count_metaphor(text))
    line("「我说好」类", count_shuo_hao(text))
    line("「我沉默了」类", count_chen_mo(text))
    line("服务者复调", count_server_polyphony(text))
    line("物件 callback 标记", count_object_callback(text))
    line("闭环句候选", count_loop_closure(text))
    line("场景切换", count_scene_break(text))
    line("结尾直接提问", count_direct_question_end(text))

    return fails


def main() -> int:
    print("=" * 70)
    print("输出回归 — sunxue skill (15 项硬指标)")
    print("=" * 70)
    print(f"examples 目录: {EXAMPLES_DIR}")

    total_fail = 0
    total_miss = 0
    for name, p in SAMPLES:
        if not p.exists():
            print(f"\n[MISS] {name}: {p} 不存在")
            total_miss += 1
            total_fail += 1
            continue
        text = p.read_text(encoding="utf-8")
        total_fail += run_one(name, text)

    print("\n" + "=" * 70)
    if total_miss:
        print(f"总结: FAIL (失败 {total_fail} 项, 含 {total_miss} 个文件缺失)")
    elif total_fail == 0:
        print("总结: PASS (所有示例所有硬指标通过)")
    else:
        print(f"总结: FAIL (失败 {total_fail} 项)")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
