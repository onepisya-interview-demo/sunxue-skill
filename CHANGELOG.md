# Changelog

All notable changes to this skill are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-28

### Added — 首次合并发布

把以下两个仓库的 MIT 内容合并到本 skill：

- **bayshier/sunxue v1.4.0** —— 孙学写作法 + 三层孙学（文本/系统/修行）
- **gehao628 sun-writing v1.2** —— 孙宇晨体机械写作引擎
- **gehao628 sun-judgment v1.2** —— 注意力定价与商业判断引擎

合并后形成**单 skill 三子模式**结构：

- `writing` —— 写作引擎（白描 + 数字 + 服务者复调 + 物件 callback + 账单收尾）
- `judgment` —— 判断引擎（先量生意半径 + 7 条规则 + 6 步流程）
- `meta` —— 三层孙学（被割的白描 / 赢学的生意 / 违背师门的代价）

### File Layout

```
sunxue/
├── SKILL.md                      # 三模式入口（v1.0 占位，T2 改造）
├── VERSION                       # 1.0.0
├── LICENSE                       # MIT + 双源版权声明
├── README.md                     # 安装 + 三模式说明 + 触发词表
├── CHANGELOG.md                  # 本文件
├── references/
│   ├── style-anatomy.md          # 来自 bayshier（原文例证 10 技法）
│   ├── x-field-notes.md          # 来自 bayshier（X 舆论场 + 曾颖讲义 + 三层孙学）
│   ├── writing-anatomy.md        # 来自 gehao628 sun-writing（五幕骨架 + 数字骨架）
│   ├── writing-checklist.md      # 来自 gehao628 sun-writing（15 项硬计数自检）
│   ├── judgment-corpus.md        # 来自 gehao628 sun-judgment（核实语料 + 禁用清单）
│   └── background.md             # 来自 bayshier（孙宇晨其人 + 事件脉络）
├── examples/
│   ├── writing-巴菲特午餐.md     # 来自 gehao628（用孙文体写孙本人）
│   ├── writing-示例2-被割版.md   # 占位（T1.5 调研后补）
│   └── judgment-老客户账期.md    # 来自 gehao628（账期四波）
└── tests/                        # 占位（T3 填充 6 个门禁脚本）
```

### Preserved Attribution

- 每个 reference 文件顶部保留**来源仓库 + 路径 + 原 license**注释块。
- LICENSE 顶部声明双源版权 + 原文版权归原作者。
- 原文片段仅作文风研究与语料引用，未做任何技法去重或章节切分。
  技法去重是 T2 任务。

### Known Limitations (v1.0.0)

- SKILL.md 是占位版本：仅含 frontmatter + 三模式入口 + 触发词表 +
  reference 引用路径。完整 13 技法 + 7 规则 + 三层反思的合并版本在
  T2 任务中生成。
- examples/writing-示例2-被割版.md 是占位文件，标注"T1.5 调研后生成"。
- tests/ 目录为空（仅 .gitkeep），6 个门禁脚本在 T3 任务中迁移与新增。
- 本次仅原样搬运两个仓库的内容，未做任何技法去重、章节切分或合并
  重写——所有合并与去重工作留给 T2。

[1.0.0]: https://github.com/your-org/sunxue/releases/tag/v1.0.0
