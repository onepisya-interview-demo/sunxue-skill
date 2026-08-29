# 孙学 Skill · sunxue

> 合并自 [`bayshier/sunxue`](https://github.com/bayshier/sunxue) v1.4.0
> + [`gehao628`](https://github.com/gehao628) `sun-writing` + `sun-judgment` v1.2。
> 三个子模式（writing / judgment / meta）合装在一个 skill 内，
> 触发词命中哪个子模式就只加载对应章节。

**版本**：v1.0.0（合并首发）
**License**：MIT（双源版权 + 原文版权归原作者，详见 [LICENSE](./LICENSE)）

---

## 这是什么

孙学 Skill 把两套互补的"孙学"内容合并到一个 skill 里：

| 来源 | 焦点 | 蒸馏产物 |
|---|---|---|
| bayshier/sunxue v1.4.0 | 写作心法 + 三层孙学 | 10 条技法（命名 + 心法 + 元反思） |
| gehao628/sun-writing v1.2 | 写作机械结构 | 12 条硬规则 + 15 项硬计数自检 + 7 步流程 |
| gehao628/sun-judgment v1.2 | 商业判断 | 规则 0（先量生意半径）+ 7 条规则 + 6 步流程 + 核实语料库 |

合并后形成**三个子模式**：

1. **`writing`** —— 用孙宇晨体写克制白描散文
2. **`judgment`** —— 注意力定价与商业判断
3. **`meta`** —— 三层孙学反思（文本 / 系统 / 修行）

---

## 安装

### Mavis（推荐）

skill 目录已就位：

```
/workspace/.skills/sunxue/
```

Mavis 在启动时会自动同步 `.skills/` 下的 skill。无需额外步骤。

### 手工拷贝到其他框架

```bash
# ZCode / Codex CLI
cp -r /workspace/.skills/sunxue ~/.zcode/skills/sunxue

# Claude Code
cp -r /workspace/.skills/sunxue ~/.claude/skills/sunxue

# 软链
ln -s /workspace/.skills/sunxue ~/.zcode/skills/sunxue
```

### 验证安装

```bash
ls /workspace/.skills/sunxue/
# 应该看到：SKILL.md  VERSION  LICENSE  README.md  CHANGELOG.md
#           references/  examples/  tests/
```

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
- `references/style-anatomy.md` —— 10 技法原文例证
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
├── SKILL.md                      # 三模式入口（v1.0 占位）
├── VERSION                       # 1.0.0
├── LICENSE                       # MIT + 双源版权声明
├── README.md                     # 本文件
├── CHANGELOG.md                  # v1.0.0 合并首发
├── references/                   # 6 个 reference（原样搬运）
│   ├── style-anatomy.md
│   ├── x-field-notes.md
│   ├── writing-anatomy.md
│   ├── writing-checklist.md
│   ├── judgment-corpus.md
│   └── background.md
├── examples/                     # 2 真 + 1 占位
│   ├── writing-巴菲特午餐.md
│   ├── writing-示例2-被割版.md   # 占位（T1.5 调研后补）
│   └── judgment-老客户账期.md
└── tests/                        # 占位（T3 填充 6 个门禁脚本）
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
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
