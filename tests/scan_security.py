#!/usr/bin/env python3
"""
安全扫描: 检查 SKILL 文档中是否
1) 含真实手机号 / 身份证 / 银行卡 / 邮箱 (PII 泄露)
2) 含密钥 / Token 字面量 (密钥泄露)
3) 含 prompt 注入向量 (用户输入可直接逃逸)
   - "忽略以上指示" / "你现在是" / "<|im_start|>" / "[INST]" / "<<SYS>>" / "{{system}}"

被测对象:
- /workspace/.skills/sunxue/SKILL.md
- /workspace/.skills/sunxue/references/*.md
- /workspace/.skills/sunxue/examples/*.md
- /workspace/.skills/sunxue/README.md

退出码: 0 = 干净 / 仅 WARN, 1 = 命中硬危险 (PII / SECRET / 注入向量)
"""
import re
import sys
import pathlib

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent

FILES = []

for sub in ("", "references", "examples"):
    base = SKILL_ROOT / sub if sub else SKILL_ROOT
    if base.exists():
        for p in sorted(base.glob("*.md")):
            label = (sub + "/" if sub else "") + p.name
            FILES.append((label, p))

# 1) PII 模式
PII = [
    (r"\b1[3-9]\d{9}\b", "中国手机号"),
    (r"\b\d{17}[\dXx]\b", "中国身份证"),
    # 银行卡号 (16-19 位连续数字) — URL 上下文豁免：path 段 (/) 前后不算
    (r"(?<![\w/])\d{16,19}(?![\w/])", "疑似银行卡号 (16-19 位连续数字)"),
    (r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "邮箱"),
]

# 2) 密钥模式
SECRET = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI / Anthropic API key"),
    (r"ghp_[A-Za-z0-9]{30,}", "GitHub PAT"),
    (r"AKIA[0-9A-Z]{16}", "AWS access key"),
    (r"-----BEGIN [A-Z ]+PRIVATE KEY-----", "私钥"),
]

# 3) prompt 注入向量
INJECTION = [
    (r"忽略(以上|之前|上面)(的|所有)?(指示|指令|内容)", "中文注入: '忽略以上指示'"),
    (r"ignore (all|previous|above) (instructions|prompts)", "英文注入: ignore previous"),
    (r"你现在是[^\n]{0,30}角色", "角色劫持: '你现在是...角色'"),
    (r"<\|im_start\|>", "ChatML 注入: <|im_start|>"),
    (r"<\|im_end\|>", "ChatML 注入: <|im_end|>"),
    (r"\[INST\]", "Llama 注入: [INST]"),
    (r"<<SYS>>", "Llama 系统段: <<SYS>>"),
    (r"\{\{.*system.*\}\}", "模板注入: {{...system...}}"),
]


def scan_file(name: str, p: pathlib.Path):
    """扫描一个文件, 返回 (hard_hits, soft_hits)。"""
    if not p.exists():
        return [(f"[MISS] {name}: 文件不存在", "")], []

    text = p.read_text(encoding="utf-8")
    hard = []  # 必须 0 — PII / SECRET / INJECTION
    soft = []  # 仅 WARN — 长数字串 (可能是巧合)

    # PII
    for pat, label in PII:
        for m in re.finditer(pat, text):
            hard.append((label, m.group()[:40]))

    # SECRET
    for pat, label in SECRET:
        for m in re.finditer(pat, text):
            hard.append((label, m.group()[:40]))

    # INJECTION
    for pat, label in INJECTION:
        for m in re.finditer(pat, text, re.IGNORECASE):
            hard.append((label, m.group()[:40]))

    return hard, soft


def main() -> int:
    print("=" * 70)
    print("安全门禁扫描报告 — sunxue skill")
    print("=" * 70)
    print(f"扫描 {len(FILES)} 个文件")

    total_hard = 0
    for name, p in FILES:
        hard, soft = scan_file(name, p)
        if hard:
            print(f"\n[{name}] 硬命中 {len(hard)} 条")
            for label, val in hard:
                print(f"  - {label}: {val!r}")
            total_hard += len(hard)
        else:
            print(f"[{name}] 干净 (无 PII / SECRET / 注入)")

    print("\n" + "=" * 70)
    if total_hard == 0:
        print("扫描完成: PASS (无硬命中)")
        return 0
    print(f"扫描完成: FAIL (硬命中 {total_hard} 条)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
