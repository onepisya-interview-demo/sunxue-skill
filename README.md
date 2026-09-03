# 孙学 Skill · sunxue

> 合并自 [`bayshier/sunxue`](https://github.com/bayshier/sunxue) v1.4.0
> + [`gehao628`](https://github.com/gehao628) `sun-writing` + `sun-judgment` v1.2。
> 三个子模式（writing / judgment / meta）合装在一个 skill 内，
> 触发词命中哪个子模式就只加载对应章节。

**版本**：v1.1.0（七层 Python 门禁工程化）
**License**：MIT（双源版权 + 原文版权归原作者，详见 [LICENSE](./LICENSE)）

> **元信息冻结**：SKILL.md 自 v1.0 起冻结（字符数顶在 lint 门禁上限）。
> `references/jingtian-essay-7000.md` 与 `examples/writing-示例3-AI时代前端.md`、
> `examples/writing-景甜-原文片段.md` 自 v1.0 起已存在于仓库但未列入 v1.0 README 树，
> 详见本 README 与 [CHANGELOG.md 1.1.0 条目](./CHANGELOG.md#110---2026-08-30)。

---

## 这是什么

孙学 Skill 把两套互补的"孙学"内容合并到一个 skill 里：

| 来源 | 焦点 | 蒸馏产物 |
|---|---|---|
| bayshier/sunxue v1.4.0 | 写作心法 + 三层孙学 | 10 技法（命名 + 心法 + 元反思），见 `references/style-anatomy.md` |
| gehao628/sun-writing v1.2 | 写作机械结构 | 12 条硬规则 + 15 项硬计数自检 + 7 步流程 |
| gehao628/sun-judgment v1.2 | 商业判断 | 规则 0（先量生意半径）+ 7 条规则 + 6 步流程 + 核实语料库 |

> **技法归并说明**：`style-anatomy.md` 记的是 bayshier 原文例证的 **10 条技法**
> （命名 / 心法 / 元反思三个层）。与 gehao628 的 12 条硬规则合并去重后，
> 形成 SKILL.md 的 **13 条核心技法**（去重不丢粒度）。详见 CHANGELOG 1.1.0。

合并后形成**三个子模式**：

1. **`writing`** —— 用孙宇晨体写克制白描散文
2. **`judgment`** —— 注意力定价与商业判断
3. **`meta`** —— 三层孙学反思（文本 / 系统 / 修行）

---

## 安装

### 启动器同步（推荐）

skill 目录已就位（按实际安装路径替换）：

```
<skill-install-path>/sunxue/
```

启动器在启动时会自动同步 `.skills/` 下的 skill。无需额外步骤。

### 手工拷贝到其他框架

```bash
# ZCode / Codex CLI
cp -r <skill-install-path>/sunxue ~/.zcode/skills/sunxue

# Claude Code
cp -r <skill-install-path>/sunxue ~/.claude/skills/sunxue

# 软链
ln -s <skill-install-path>/sunxue ~/.zcode/skills/sunxue
```

### 验证安装

```bash
ls <skill-install-path>/sunxue/
# 应该看到：SKILL.md  VERSION  LICENSE  README.md  CHANGELOG.md
#           references/  examples/  notes/  scripts/  tests/  src/  pyproject.toml
```

---

## 快速上手：怎么用

本 skill 不是跑命令的工具，而是**装进 AI agent 的一段写作/判断引擎**。装好之后不需要任何命令——在对话里说出带触发词的句子，agent 会自动加载对应引擎并按其技法工作。

### 三步开始

1. 把 skill 装进你的 agent（见上一节）；
2. 新开对话，直接说一句带触发词的话（下面有可复制的例子）；
3. agent 自动命中子模式、只加载该引擎的章节，按技法产出。

### 可直接复制的示例

**模式 1 · writing（写作引擎）** —— 把你的真实经历交给它：

> 用孙宇晨的风格，把这段经历写成小作文：我和她异地三年，最后发现她早就和别人看好了房子……

> 像孙学一样写一段被裁员的故事，克制一点，别煽情。

产出预期：一篇克制白描的长文——数字骨架、物件回环、账单收尾，能通过 writing-checklist 的 15 项硬计数自检。

**模式 2 · judgment（判断引擎）** —— 带上你的决策处境：

> 孙学判断：我预算五万块，怎么在一个新行业里做出声量？

> 注意力定价：要不要公开承认我们产品出了这个 bug？

产出预期：一条判断链——注意力怎么定价、动作怎么设计、风险在哪，口径对齐已核实的公开商业动作。

**模式 3 · meta（三层孙学反思）** —— 想拆解而非创作时：

> 三层孙学：为什么「我的女友景甜」这种文本能爆红？

> 仿写公式：我想做白描 + 流量 + 商业三合一的内容产品，边界在哪？

产出预期：文本层 / 系统层 / 修行层的三层拆解。

### 素材给法（决定产出上限）

- **writing**：带着真实细节来（时间、地点、金额、对话）——被割场景（被分手 / 被骗 / 亏损 / 裁员）威力最大
- **judgment**：给清处境、预算与目标声量，让引擎给动作定价
- **meta**：给一个具体的文本或现象，别问空泛问题

### 铁律（来自 SKILL.md，触发前必读）

1. writing 只用于散文回忆，judgment 只用于商业决策——**两个引擎互不污染**
2. 严禁用 judgment 给真人真事定罪
3. 严禁用 writing 把普通生活写成营销稿
4. 原作版权归原作者；本 skill 仅摘引片段作技法分析

### 触发不中怎么办

- 换用更完整的触发词（全表见下方「触发词总表」）
- 或直接点名子模式：「用 writing 引擎写……」「进入 judgment 模式……」
- 一个输入只针对一个引擎——把写作和决策两类需求揉进同一句话，路由会含糊

各模式的完整触发词、适合场景与 reference 索引，见下节「三模式说明」。

---

## 三模式说明

### 模式 1：writing（写作引擎）

**触发词**：

- 孙宇晨体 / 用孙宇晨的风格写 / 用孙哥的风格写
- sun-writing / 把这段经历写成小作文
- 景甜式写法 / 克制白描 / 像孙学一样写
- 被割版 / 写一段（关系/经历/失去/徒劳）

**适合场景**：

- 写一段关系、一次失去、一场徒劳、一段经历
- 非虚构长文、人物特写、纪实散文
- 仿写（"我的男友/女友 XX"句式）
- 用户带着败局（被分手 / 被骗 / 亏损 / 裁员）来写

**会用到的 reference**：

- `references/writing-anatomy.md` —— 五幕骨架解剖
- `references/writing-checklist.md` —— 15 项硬计数自检
- `references/style-anatomy.md` —— 10 技法原文例证（与 gehao628 技法合并去重后形成 SKILL.md 的 13 条核心技法）
- `examples/writing-巴菲特午餐.md` —— 用孙文体写孙本人

### 模式 2：judgment（判断引擎）

**触发词**：

- 孙学判断 / sun-judgment / 注意力定价
- 孙宇晨会怎么做 / 用孙宇晨的逻辑判断
- 注意力套利 / 这钱该怎么花才有声量

**适合场景**：

- 预算有限但想要行业级知名度
- 要不要做一件"看起来很蠢"的事
- 怎么处理负面舆论
- 怎么给一个动作定价

**会用到的 reference**：

- `references/judgment-corpus.md` —— 核实过的原文语料 + 禁用清单
- `examples/judgment-老客户账期.md` —— 账期四波的实战样本

### 模式 3：meta（三层孙学反思）

**触发词**：

- 三层孙学 / 仿写公式 / 被割版
- 孙学爆红原因 / 学孙学还是学孙哥
- 怎么像孙学一样传播 / 文本层 / 系统层 / 修行层

**适合场景**：

- 理解"孙学"为什么爆红
- 仿写（梗、句式、文体）的边界与公式
- 想要做"白描 + 流量 + 商业"三合一的内容产品
- 想要"用孙学反击孙学"（曾颖讲义体）

**会用到的 reference**：

- `references/x-field-notes.md` —— X 舆论场 + 曾颖讲义 + 三层孙学
- `references/background.md` —— 孙宇晨其人与事件脉络

---

## 触发词总表

| 子模式 | 触发词 |
|---|---|
| **writing** | 孙宇晨体, 用孙宇晨的风格写, 用孙哥的风格写, sun-writing, 把这段经历写成小作文, 景甜式写法, 克制白描, 像孙学一样写, 被割版, 写一段（关系/经历/失去/徒劳） |
| **judgment** | 孙学判断, sun-judgment, 注意力定价, 孙宇晨会怎么做, 用孙宇晨的逻辑判断, 注意力套利, 这钱该怎么花才有声量 |
| **meta** | 三层孙学, 仿写公式, 被割版, 孙学爆红原因, 学孙学还是学孙哥, 怎么像孙学一样传播, 文本层, 系统层, 修行层 |

> 触发词可在 `SKILL.md` 的 frontmatter `description` 中找到。
> 多个触发词命中同一子模式时只加载该子模式章节。

---

## 目录结构

```
sunxue/
├── SKILL.md                          # 三模式入口（元信息冻结；v1.1 减重后 23,865 字符）
├── VERSION                           # 1.1.0
├── LICENSE                           # MIT + 双源版权声明
├── README.md                         # 本文件
├── CHANGELOG.md                      # v1.1.0 门禁工程化 / v1.0.0 合并首发
├── pyproject.toml                    # uv 配置 + dev 工具链
├── uv.lock                           # 锁定依赖图
├── src/
│   └── sunxue_gates/                 # 门禁包（七门禁 + 共享解析 + 结果类型）
│       ├── __init__.py               # GATES 元组 + run() / run_all()
│       ├── __main__.py               # `python -m sunxue_gates` 串跑入口
│       ├── results.py                # CheckResult / GateResult dataclass
│       ├── parsing.py                # frontmatter / classify / count_h2
│       ├── lint_structure.py         # Gate 1
│       ├── scan_security.py          # Gate 2
│       ├── regression_output.py      # Gate 3
│       ├── token_budget.py           # Gate 4
│       ├── injection_drill.py        # Gate 5
│       ├── mutation_drill.py         # Gate 6
│       ├── lint_claims.py             # Gate 7
│       └── tables.py                  # 关键词/模式纯数据表（golden 契约锁定）
├── references/                       # 9 个 reference（原样搬运 + 技法注解 + 门禁契约）
│   ├── style-anatomy.md              # bayshier 原文例证 10 技法（与 gehao628 合并去重后形成 SKILL.md 的 13 条核心技法）
│   ├── x-field-notes.md              # bayshier X 舆论场 + 曾颖讲义 + 三层孙学
│   ├── writing-anatomy.md            # gehao628 sun-writing（五幕骨架 + 数字骨架）
│   ├── writing-checklist.md          # gehao628 sun-writing（17 项硬计数自检）— 16 项硬指标的真源
│   ├── judgment-corpus.md            # gehao628 sun-judgment（核实语料 + 禁用清单）
│   ├── background.md                 # bayshier 孙宇晨其人 + 事件脉络
│   ├── jingtian-essay-7000.md        # 孙宇晨原作《我的女友景甜》原文片段
│   ├── merge-map.md                  # 22 条 → 13 条去重映射表（v1.1.0 从 SKILL.md 外迁，plan 3.2）
│   └── enforcement.md                # 交付期门禁契约 + 跨宿主诚实声明（synthesis 档 ① 外置）
├── examples/                         # 9 个真实样本（无占位）
│   ├── writing-巴菲特午餐.md         # gehao628：用孙文体写孙本人
│   ├── writing-示例2-被割版.md       # 真实完整稿（v1.0 误标占位，v1.1 更正）
│   ├── writing-示例3-AI时代前端.md   # regression_output 真实样本
│   ├── writing-景甜-原文片段.md       # 孙宇晨原作引用片段
│   ├── writing-十二个字节.md          # v2 门禁实战样本
│   ├── writing-七年通勤.md           # 通勤七年账本（plan 3.1 sample-expansion）
│   ├── writing-五次打印机.md         # 五次打印机报价单（plan 3.1 sample-expansion）
│   ├── writing-清仓大甩卖.md         # 清仓大甩卖话术（plan 3.1 sample-expansion）
│   └── judgment-老客户账期.md         # gehao628：账期四波
├── notes/                               # 开发笔记（踩坑 / 手册 / 学习 / 测试思路）
│   ├── pitfalls.md                      # 踩坑记录（10 条实战坑）
│   ├── runbook.md                       # 操作手册（搭建 / 日常 / 发版 / 受限环境）
│   ├── learning.md                      # 学习笔记（门禁分层设计理念）
│   └── testing.md                       # 测试思路（五层金字塔与豁免政策）
├── assets/                           # 推广海报
│   ├── promo-1.jpg
│   └── promo-2.jpg
├── scripts/                             # 辅助脚本（gen_mutation_report.py）
└── tests/                            # pytest 测试树（unit + property + live）
    ├── README.md                     # 七层门禁命令表 + 质量五维映射 + 测试思路指针
    ├── conftest.py                   # 共享 fixtures
    ├── unit/                         # 纯函数单元测试
    ├── property/                     # hypothesis 属性测试
    ├── test_gates_live.py            # 对当前仓库跑七门禁 run()，断言 PASS（旧行为回归）
    └── mutation-report.md            # mutmut 3.x triage 报告（豁免台账见 mutation-exemptions.json）
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| 1.1.0 | 2026-08-30 | 门禁工程化：src/sunxue_gates package + uv scaffold + tests/ 测试树（202 pytest 100% 覆盖） |
| 1.0.0 | 2026-08-28 | 合并首发：bayshier/sunxue v1.4.0 + gehao628 sun-writing + sun-judgment |

详见 [CHANGELOG.md](./CHANGELOG.md)。

---

## 致谢与版权

- **写作心法与三层孙学** —— 来自 [bayshier/sunxue](https://github.com/bayshier/sunxue)（MIT）
- **写作机械结构与判断引擎** —— 来自 [gehao628](https://github.com/gehao628)（MIT）
- **范本原文** —— 来自 [HEJustinSun/my-girlfriend-jingtian-latex](https://github.com/HEJustinSun/my-girlfriend-jingtian-latex)（《我的女友景甜》全文版权归原作者孙宇晨所有）

本 skill 仅摘引片段作技法分析与语料研究，不修改、不续写、不商化原始内容。

---

## 免责声明

- 本 skill 的输出**不构成任何投资建议或法律建议**。
- 判断模式（judgment）整理的孙宇晨本人公开语料与商业动作，仅作为
  方法论研究的样本。用户在套用判断规则前应自行评估自身风险承受能力。
- 写作模式（writing）生成的文本仅作技法演示，请勿冒犯真实他人隐私。
- 详见 [LICENSE](./LICENSE) 第 3 节"商业判断免责声明"。
