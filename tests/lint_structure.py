#!/usr/bin/env python3
"""
结构 lint: 检查 skill 文件的必填字段 / 必含章节 / 体积上限 / 章节切分粒度。

被测对象 (skill 根目录 = /workspace/.skills/sunxue/)：
- SKILL.md
- references/*.md

硬指标:
- YAML frontmatter 必填: name, description
- 必含章节: 第一原则 / 心法 / 触发词 / 红线 / 铁律 (任一组命中即过)
- 体积上限: SKILL.md <= 25_000 字符, reference <= 12_000 字符
- 章节切分粒度: 二级标题 (##) 数量过多 (>= 80) 视为过碎

退出码: 0 = PASS, 1 = FAIL
"""
import re
import sys
import pathlib

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_ROOT / "SKILL.md"
REFERENCES_DIR = SKILL_ROOT / "references"

REQUIRED_FRONTMATTER = ["name", "description"]

# 三组核心章节: 每组用 | 连接多个备选词, 命中任一即过
REQUIRED_SECTION_GROUPS = [
    "第一原则|心法|写作引擎|判断引擎|方法论",
    "触发词|触发|适用于|命中",
    "红线|铁律|禁令|绝对禁令|不要",
]

SIZE_LIMITS = {
    "SKILL": 25_000,
    "reference": 12_000,
}

# 章节切分粒度阈值
MAX_H2_HEADINGS = 80


def parse_fm(text: str):
    """极简 YAML frontmatter 解析: 只支持 key: value 单行 / 块。"""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    body = m.group(1)
    out = {}
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        m2 = re.match(r"^(\S+):\s*(.*)$", line)
        if not m2:
            i += 1
            continue
        k, v = m2.group(1), m2.group(2)
        if not v.strip():
            # 多行块: 缩进行读到非缩进
            block = []
            j = i + 1
            while j < len(lines) and (
                lines[j].startswith("  ") or lines[j].startswith("\t")
            ):
                block.append(lines[j].strip())
                j += 1
            out[k] = " ".join(block)
            i = j
        else:
            out[k] = v.strip().strip('"').strip("'")
            i += 1
    return out


def classify(p: pathlib.Path) -> str:
    return "SKILL" if p.name == "SKILL.md" else "reference"


def count_h2(text: str) -> int:
    return len(re.findall(r"^##\s+", text, re.MULTILINE))


def check_one(name: str, p: pathlib.Path) -> int:
    """对一个文件跑结构 lint, 返回失败数。"""
    fails = 0
    if not p.exists():
        print(f"[MISS] {name}: {p} 不存在")
        return 1

    text = p.read_text(encoding="utf-8")
    size = len(text)
    kind = classify(p)
    limit = SIZE_LIMITS[kind]
    print(f"\n=== {name} ({kind}, {size} chars, 上限 {limit}) ===")

    # 1) frontmatter
    if kind == "SKILL":
        fm = parse_fm(text)
        if fm is None:
            print(f"  [FAIL] 缺 YAML frontmatter (--- 块)")
            fails += 1
        else:
            for k in REQUIRED_FRONTMATTER:
                if k not in fm or not str(fm[k]).strip():
                    print(f"  [FAIL] frontmatter 缺字段: {k}")
                    fails += 1
                else:
                    v = str(fm[k])
                    preview = v[:60].replace("\n", " ")
                    print(f"  [OK] frontmatter.{k} = {preview}{'...' if len(v) > 60 else ''}")

    # 2) 体积
    if size > limit:
        print(f"  [FAIL] 体积 {size} > 上限 {limit} (溢出 {size - limit})")
        fails += 1
    else:
        print(f"  [OK] 体积 {size} <= {limit}")

    # 3) 必含章节 (SKILL 文件才检查)
    if kind == "SKILL":
        for group in REQUIRED_SECTION_GROUPS:
            if not re.search(group, text):
                print(f"  [FAIL] 必含章节未命中 /{group}/")
                fails += 1
            else:
                print(f"  [OK] 必含章节命中 /{group}/")

    # 4) 章节切分粒度
    h2 = count_h2(text)
    if h2 > MAX_H2_HEADINGS:
        print(f"  [FAIL] 二级标题 {h2} > {MAX_H2_HEADINGS} (过碎)")
        fails += 1
    else:
        print(f"  [OK] 二级标题数 {h2} <= {MAX_H2_HEADINGS}")

    return fails


def main() -> int:
    print("=" * 70)
    print("结构 lint — sunxue skill")
    print("=" * 70)
    print(f"skill 根目录: {SKILL_ROOT}")

    total_fail = 0
    total_fail += check_one("SKILL.md", SKILL_MD)

    if REFERENCES_DIR.exists():
        for ref in sorted(REFERENCES_DIR.glob("*.md")):
            total_fail += check_one(f"references/{ref.name}", ref)
    else:
        print(f"\n[WARN] references/ 目录不存在: {REFERENCES_DIR}")

    print("\n" + "=" * 70)
    if total_fail == 0:
        print("总结: PASS (所有检查通过)")
        return 0
    print(f"总结: FAIL (失败 {total_fail} 项)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
