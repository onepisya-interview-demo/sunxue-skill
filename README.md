# 孙学 Skill · sunxue-skill

> 合并自 [`bayshier/sunxue`](https://github.com/bayshier/sunxue) v1.4.0
> + [`gehao628`](https://github.com/gehao628) `sun-writing` + `sun-judgment` v1.2。
> 四个子模式（writing / judgment / meta / **yingxue**）合装在一个 skill 内，
> 触发词命中哪个子模式就只加载对应章节。

**版本**：v1.4.0（SKILL.md 再外化收敛为路由器：13,132 → 4,295 chars，冷启动开销 -67%；技法/流程/禁令真源归 `references/`，详见 [CHANGELOG 1.4.0](./CHANGELOG.md#140---2026-09-05)）
**License**：MIT（双源版权 + 原文版权归原作者，详见 [LICENSE](./LICENSE)）

> **元信息冻结**：SKILL.md 结构冻结（H1 标记 + frontmatter name/description 不动，license 为静态字段）；事实数字与指针随版本同步（audit-v4 D1③，口径见 AGENTS.md）。

---

## 这是什么

孙学 Skill 把两套互补的"孙学"内容合并到一个 skill 里：

| 来源 | 焦点 | 蒸馏产物 |
|---|---|---|
| bayshier/sunxue v1.4.0 | 写作心法 + 三层孙学 | 10 技法（命名 + 心法 + 元反思），见 `references/style-anatomy.md` |
| gehao628/sun-writing v1.2 | 写作机械结构 | 12 条硬规则 + 15 项硬计数自检（本地增补 1 项后 16）+ 7 步流程 |
| gehao628/sun-judgment v1.2 | 商业判断 | 规则 0（先量生意半径）+ 7 条规则 + 6 步流程 + 核实语料库 |

> **技法归并说明**：`style-anatomy.md` 记的是 bayshier 原文例证的 **10 条技法**
> （命名 / 心法 / 元反思三个层）。与 gehao628 的 12 条硬规则合并去重后，
> 形成 SKILL.md 的 **13 条核心技法**（去重不丢粒度）。详见 CHANGELOG 1.1.0。

合并后形成**四个子模式**：

1. **`writing`** —— 用孙宇晨体写克制白描散文
2. **`judgment`** —— 注意力定价与商业判断
3. **`meta`** —— 三层孙学反思（文本 / 系统 / 修行）
4. **`yingxue`** —— 曾颖深情喜剧学（笑点在前、痛点在后；v1.2.0 首纳）

---

## 安装

### 启动器同步（推荐）

把本仓库克隆 / 同步到你的启动器 skills 目录（按实际安装路径替换）：

```
$HOME/.agents/skills/sunxue-skill/
```

> **注**: 实际路径因启动器而异——ZCode = `$HOME/.zcode/skills/sunxue-skill/`;
> Claude Code = `$HOME/.claude/skills/sunxue-skill/`; Hermes = `$HOME/.agents/skills/sunxue-skill/`。
> 下面示例用 `$HOME/.agents/skills/sunxue-skill/`。
> **命名一致性**（官方规范要求目录名与 frontmatter `name` 一致）: 仓库名 = 安装目录名 = `name` = **`sunxue-skill`**（audit-v4 BP-C1 红线收口；`agentskills validate` 通过）。

启动器在启动时会自动同步 `.skills/` 下的 skill。无需额外步骤。

### 手工拷贝到其他框架

```bash
# ZCode / Codex CLI
cp -r $HOME/.agents/skills/sunxue-skill ~/.zcode/skills/sunxue-skill

# Claude Code
cp -r $HOME/.agents/skills/sunxue-skill ~/.claude/skills/sunxue-skill

# 软链
ln -s $HOME/.agents/skills/sunxue-skill ~/.zcode/skills/sunxue-skill
```

### 验证安装

```bash
ls $HOME/.agents/skills/sunxue-skill/
# 应该看到：SKILL.md  VERSION  LICENSE  README.md  CHANGELOG.md
#           references/  examples/  scripts/  tests/  src/  pyproject.toml
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

产出预期：一篇克制白描的长文——数字骨架、物件回环、账单收尾，能通过 writing-checklist 的 16 项硬计数自检。

**模式 2 · judgment（判断引擎）** —— 带上你的决策处境：

> 孙学判断：我预算五万块，怎么在一个新行业里做出声量？

> 注意力定价：要不要公开承认我们产品出了这个 bug？

产出预期：一条判断链——注意力怎么定价、动作怎么设计、风险在哪，口径对齐已核实的公开商业动作。

**模式 3 · meta（三层孙学反思）** —— 想拆解而非创作时：

> 三层孙学：为什么「我的女友景甜」这种文本能爆红？

> 仿写公式：我想做白描 + 流量 + 商业三合一的内容产品，边界在哪？

产出预期：文本层 / 系统层 / 修行层的三层拆解。

**模式 4 · yingxue（深情喜剧学）** —— 带上旧情或亲情的真实细节：

> 用颖学写一段：他寄的冻鸡被海关扣了，打电话让我去认领……

产出预期：一篇让人「又笑又心疼」的深情文——荒诞实物承载深情，结尾一句「原来…」立刻收笔。

### 素材给法（决定产出上限）

- **writing**：带着真实细节来（时间、地点、金额、对话）——被割场景（被分手 / 被骗 / 亏损 / 裁员）威力最大
- **judgment**：给清处境、预算与目标声量，让引擎给动作定价
- **meta**：给一个具体的文本或现象，别问空泛问题
- **yingxue**：给一段旧情/亲情的真实细节，让荒诞实物（冻鸡 / 椰子鸡 / 消息条数）替你说深情

### 铁律（来自 SKILL.md，触发前必读）

1. writing/yingxue 只用于散文回忆，judgment 只用于商业决策——**引擎互不污染**
2. 严禁用 judgment 给真人真事定罪
3. 严禁用 writing/yingxue 把普通生活写成营销稿
4. 原作版权归原作者；本 skill 仅摘引片段作技法分析

### 触发不中怎么办

- 换用更完整的触发词（全表见下方「触发词总表」）
- 或直接点名子模式：「用 writing 引擎写……」「进入 judgment 模式……」
- 一个输入只针对一个引擎——把写作和决策两类需求揉进同一句话，路由会含糊

各模式的完整触发词、适合场景与 reference 索引，见下节「四模式说明」。

---

## 四模式说明

### 模式 1：writing（写作引擎）

**触发词**：

- 孙宇晨体 / 用孙宇晨的风格写 / 孙哥风格
- 景甜式白描 / 冷叙事 / 被割版
- 把这段经历写成小作文

**适合场景**：

- 写一段关系、一次失去、一场徒劳、一段经历
- 非虚构长文、人物特写、纪实散文
- 仿写（"我的男友/女友 XX"句式）
- 用户带着败局（被分手 / 被骗 / 亏损 / 裁员）来写

**会用到的 reference**：

- `references/writing-essence.md` —— 第一原则（温度计归零）+ 第零关闸门（动笔前必读）
- `references/style-anatomy.md` —— 13 技法完整定义 + 原文例证
- `references/writing-anatomy.md` —— 7+1 步流程逐幕机械做法
- `references/writing-checklist.md` —— 16 项硬计数自检（17 项 EXPECT 真源）
- `examples/writing-*.md` —— 9 个完整样本（巴菲特午餐 / 我沉默了-强示范 等）

### 模式 2：judgment（判断引擎）

**触发词**：

- 孙学判断 / sun-judgment / 注意力定价
- 孙宇晨会怎么做 / 注意力套利
- 这笔钱怎么花才有声量

**适合场景**：

- 预算有限但想要行业级知名度
- 要不要做一件"看起来很蠢"的事
- 怎么处理负面舆论
- 怎么给一个动作定价

**会用到的 reference**：

- `references/judgment-corpus.md` —— 7 规则 + 6 步 + 8 节核实语料 + 防翻车禁用清单
- `references/enforcement.md` —— 绝对禁令 + 门禁工程契约
- `examples/judgment-*.md` —— 6 个判断样本（面馆/全球IP/暑期招生 范例 + 律师函反例 等）

### 模式 3：meta（三层孙学反思）

**触发词**：

- 三层孙学 / 仿写公式 / 孙学爆红原因
- 学孙学还是学孙哥 / 修行层

**适合场景**：

- 理解"孙学"为什么爆红
- 仿写（梗、句式、文体）的边界与公式
- 想要做"白描 + 流量 + 商业"三合一的内容产品
- 想要"用孙学反击孙学"（曾颖讲义体）

**会用到的 reference**：

- `references/x-field-notes.md` —— X 舆论场 + 三层孙学 + 舆论场四派
- `examples/meta-注意力定价-bug-disclosure.md` —— 注意力定价三层拆解真样本
- （背景可选读 `references/background.md` —— 孙宇晨其人与事件脉络）

---

### 模式 4：yingxue（深情喜剧学）

**触发词**：

- 颖学 / 曾颖 / 椰子鸡 / 冻鸡
- 笑完才疼 / 一把屎一把尿式深情 / @zengying1107

**适合场景**：

- 旧情回忆、人物侧写——想让人「又笑又心疼」时用
- 深情不直说，让一个荒诞实物（冻鸡 / 椰子鸡 / 一条没删的消息）替你说
- 以柔克刚的反击（颖学只发嗲和反问，不写长文骂人）

**会用到的 reference**：

- `references/yingxue-corpus.md` —— 曾颖四篇语料 + 词源
- `references/yingxue-anatomy.md` —— 技法解剖 + 四篇骨架表 + 孙颖对照
- `examples/yingxue-冻鸡挽歌-仿写.md` —— 200 字仿写首例

---

## 触发词总表

| 子模式 | 触发词 |
|---|---|
| **writing** | 孙宇晨体, 用孙宇晨的风格写, 孙哥风格, 景甜式白描, 冷叙事, 被割版, 把这段经历写成小作文 |
| **judgment** | 孙学判断, sun-judgment, 注意力定价, 孙宇晨会怎么做, 注意力套利, 这笔钱怎么花才有声量 |
| **meta** | 三层孙学, 仿写公式, 孙学爆红原因, 学孙学还是学孙哥, 修行层 |
| **yingxue** | 颖学, 曾颖, 椰子鸡, 冻鸡, 笑完才疼, 一把屎一把尿式深情, @zengying1107 |

> 上表与 `SKILL.md` frontmatter `description` 逐词对应（触发真源 = description，未列出的口语说法靠主动触发条款兜底）。
> 多个触发词命中同一子模式时只加载该子模式章节。

---

## 目录结构

```
sunxue-skill/
├── SKILL.md                          # 路由器：触发词 → 模式 → 读取顺序 SOP + 铁律（结构冻结；v1.4.0 实测 4,295 chars，技法/流程/禁令真源在 references/）
├── VERSION                           # 1.4.0
├── LICENSE                           # MIT + 双源版权声明
├── README.md                         # 本文件
├── CHANGELOG.md                      # v1.3.0 命名/常量清理+内容扩 / v1.2.2 patch 收口 / v1.2.1 audit 收口 / v1.2.0 yingxue+SKILL.md 外化 / v1.1.0 门禁工程化 / v1.0.0 合并首发
├── AGENTS.md                          # AI 协作规范（提交 WHAT/WHY/HOW / 仓库速览 / 门禁回环约束）
├── CONTRIBUTING.md                    # 贡献指南（v1.2.2 起，最小流程）
├── pyproject.toml                    # uv 配置 + dev 工具链
├── uv.lock                           # 锁定依赖图 (本仓库 tracked, v1.2.1 audit 起入 git)
├── src/
│   └── sunxue_gates/                 # 门禁包（八门禁 + 共享解析 + 结果类型）
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
│       ├── lint_pii.py                # Gate 8（PII 硬扫描）
│       ├── _cli_flags.py              # --all/--json flag 真源 frozenset（get_gates_flags）
│       └── tables.py                  # 关键词/模式纯数据表（golden 契约锁定）
├── references/                       # 13 个 reference（原样搬运 + 技法注解 + 门禁契约 + 第 7.2 步内容自洽性扫描 + v1.2 写作总纲 + yingxue 语料 + v1.3 颖学解剖）
│   ├── style-anatomy.md              # bayshier 原文例证 10 技法（与 gehao628 合并去重后形成 SKILL.md 的 13 条核心技法）
│   ├── x-field-notes.md              # bayshier X 舆论场 + 曾颖讲义 + 三层孙学
│   ├── writing-anatomy.md            # gehao628 sun-writing（五幕骨架 + 数字骨架 + 7 步流程 + 致命自检/最后一问附录 A/B）
│   ├── writing-checklist.md          # gehao628 sun-writing（16 项硬自检）— 17 项 EXPECT 字典的真源（含场景切换/闭环句）
│   ├── judgment-corpus.md            # gehao628 sun-judgment（核实语料 + 7 规则 + 6 步 + 语气 + 防翻车禁用）
│   ├── background.md                 # bayshier 孙宇晨其人 + 事件脉络
│   ├── jingtian-essay-7000.md        # 孙宇晨原作《我的女友景甜》原文片段
│   ├── merge-map.md                  # 22 条 → 13 条去重映射表（v1.1.0 从 SKILL.md 外迁，plan 3.2）
│   ├── enforcement.md                # 交付期门禁契约 + 跨宿主诚实声明 + 两引擎绝对禁令 §6
│   ├── coherence-checklist.md        # SKILL.md 第 7.2 步内容自洽性扫描 SOP（5 项检查 + 报告格式）
│   ├── writing-essence.md            # v1.2.0 新增：第一原则 + 第零关 + 仿写公式 + 镜像识别 + 演说体 vs 证词体
│   ├── yingxue-corpus.md             # v1.2.0 新增：曾颖四篇语料（冻鸡/椰子鸡/15688 消息/养他论）+ 词源
│   └── yingxue-anatomy.md            # v1.3.0 新增：颖学技法解剖 + 四篇骨架表 + 孙颖对照（本地归纳，与 SKILL.md 上游 6 卡关系见文件头仲裁注）
├── examples/                         # 17 个真实样本（v1.2.1 audit 收口：8 写作 + 6 判断 + 1 meta + 1 yingxue；v1.3 集群 D 加 1 写作我沉默了强示范）
│   ├── writing-巴菲特午餐.md         # gehao628：用孙文体写孙本人
│   ├── writing-示例2-被割版.md       # 真实完整稿（v1.0 误标占位，v1.1 更正）
│   ├── writing-示例3-AI时代前端.md   # regression_output 真实样本
│   ├── writing-景甜-原文片段.md       # 孙宇晨原作引用片段
│   ├── writing-十二个字节.md          # v2 门禁实战样本
│   ├── writing-七年通勤.md           # 通勤七年账本（plan 3.1 sample-expansion）
│   ├── writing-五次打印机.md         # 五次打印机报价单（plan 3.1 sample-expansion）
│   ├── writing-清仓大甩卖.md         # 清仓大甩卖话术（plan 3.1 sample-expansion）
│   ├── writing-我沉默了-强示范.md     # v1.3.0 集群 D：双线节拍强示范（装修工单，我沉默了/我说好 ≥ 5）
│   ├── judgment-老客户账期.md         # gehao628：账期四波
│   ├── judgment-面馆-范例.md         # v1.2.0 拆分：3 公里面馆上热搜（规则 0/2/3 强示范）
│   ├── judgment-行业B端-范例.md      # v1.2.0 拆分：B 端借势蹭争议（规则 0/4/5/7 边界三问）
│   ├── judgment-全球IP-范例.md        # v1.2.0 拆分：500 万买事件（规则 0/1/2/3 强示范）
│   ├── judgment-律师函反例.md         # v1.2.0 拆分：发律师函的边界失败（规则 4/5/7 反例）
│   ├── judgment-暑期招生窗口期.md     # v1.2.1 收口：三线培训机构问暑期招生（规则 6 争一千天 强示范）
│   ├── meta-注意力定价-bug-disclosure.md  # v1.2.1 收口：注意力定价三层拆解（meta 真样本）
│   └── yingxue-冻鸡挽歌-仿写.md      # v1.2.1 收口：曾颖《冻鸡挽歌》200 字仿写（yingxue 模式首例，演示荒诞物证/恍然大悟反转/典故降维/讲义体）
├── scripts/                             # 辅助脚本（3 个非门禁脚本：coherence_gate / writing_gate / gen_mutation_report，用法见各脚本 docstring）
└── tests/                            # pytest 测试树（unit + property + integration + golden + live）
    ├── README.md                     # 八层门禁命令表 + 质量五维映射 + 测试思路指针
    ├── __init__.py                    # 包标记（pytest 根识别）
    ├── conftest.py                   # 共享 fixtures
    ├── unit/                         # 纯函数单元测试（12 文件，10 门禁模块全覆盖）
    ├── property/                     # hypothesis 属性测试（15 个 @given 不变量）
    ├── integration/                  # scripts/ CLI 契约测试（2 测试文件：writing_gate + coherence_gate；含 _helpers.py + fixtures/ 3 md）
    ├── golden/                       # 字面量金样（literals.json + gen_golden.py；SHA-256 + hex_utf8 双签名，4 门覆盖）
    ├── test_gates_live.py            # 对当前仓库跑八门禁 run()，断言 PASS（旧行为回归）
    ├── mutation-report.md            # mutmut 3.x triage 报告（豁免台账见 mutation-exemptions.json）
    └── mutation-exemptions.json      # 50.7% 幸存者的豁免理由 JSON
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| 1.4.0 | 2026-09-05 | **SKILL.md 再外化：收敛为路由器（resolver）**：13,132 → 4,295 chars（-67%，冷启动 4,377 → 1,431 tok）——技法卡/流程/禁令/对照表删重不复述，真源归 references/；yingxue 命名真源六卡 + 五步 + 六红线 + 孙颖对照迁入 yingxue-anatomy 附录二（IF-03 仲裁更新，双源漂移归一）；四模式 SOP 化（含交稿门禁命令）；H1 + frontmatter + @mode 骨架冻结不动；8/8 gates --all 全绿 130.12s |
| 1.3.1 | 2026-09-04 | **audit-v4 全面审计收口**：9 维度正交审计（8 并行 + peer 元审计）P0/P1 修复——文档真源勘误（字节冒充 chars / 7.9% 残留 / 节序）/ README 四模式补全 / SKILL.md 事实同步（D1③ 结构冻结数字同步）/ meta+yingxue 门禁接线（10→12/17）/ golden 扩五模块 / 残留物清零（promo 546KB 删除）/ coherence 星期锚点修复 / gates_all 120→180s / mutmut 50.7% 机渲刷新 |
| 1.3.0 | 2026-09-04 | **5 集群 patch 收口**：7 项 P2/P3 命名/常量清理（F7/F8/F9/F14/F16/F17/F21，tables.py 真源化）+ tests/integration/_helpers.py 抽公共 helper + mutmut 试探留档（51.5% 1330/2582，未达 ≤ 40% 接受判据）+ yingxue-anatomy 6 技法卡片（references/yingxue-anatomy.md）+ 我沉默了 ≥ 5 强示范 example（17 example / 13 reference）/ 8/8 gates --all 全绿 / 335 tests pass |
| 1.2.2 | 2026-09-04 | **patch 收口**：5 集群 13 项 P0/P1 全修（数字/路径真源 + 文档补完 + 路由同步 + peer hygiene + mutmut budget 45→120s）/ mutmut 幸存率 51.4%（audit-v4 勘误：发布时描述 7.9% 系 reporter 字段名歧义误读，M-14 未命中）/ 8/8 gates --all 全绿 48.58s |
| 1.2.1 | 2026-09-04 | **全面 audit 收口**：七→八门禁口径统一 / meta 模式首个真样本 / examples 16 / scripts 3 个 owner 文档 / 16/17 项硬指标口径统一 / 目录树补项 |
| 1.2.0 | 2026-09-04 | SKILL.md 元信息冻结 12,606 chars 外化重组 + yingxue 第四模式首次纳入（曾颖四篇语料 → references/yingxue-corpus.md）|
| 1.1.0 | 2026-08-30 | 门禁工程化：src/sunxue_gates package + uv scaffold + tests/ 测试树（202 pytest 100% 覆盖） |
| 1.0.0 | 2026-08-28 | 合并首发：bayshier/sunxue v1.4.0 + gehao628 sun-writing + sun-judgment |

详见 [CHANGELOG.md](./CHANGELOG.md)。

> 注：`references/jingtian-essay-7000.md`、`examples/writing-示例3-AI时代前端.md`、`examples/writing-景甜-原文片段.md` 自 v1.0 起已在仓库而未列入 v1.0 README 树，见 [CHANGELOG 1.1.0](./CHANGELOG.md#110---2026-08-30)。

---

## 致谢与版权

- **写作心法与三层孙学** —— 来自 [bayshier/sunxue](https://github.com/bayshier/sunxue)（MIT）
- **写作机械结构与判断引擎** —— 来自 [gehao628](https://github.com/gehao628)（MIT；原 sun-writing / sun-judgment 二仓已合并为 [gehao628/sunxue](https://github.com/gehao628/sunxue)）
- **范本原文** —— 来自 [HEJustinSun/my-girlfriend-jingtian-latex](https://github.com/HEJustinSun/my-girlfriend-jingtian-latex)（《我的女友景甜》全文版权归原作者孙宇晨所有；2026-09-04 快照：该仓库与账号已 404，疑似注销/改名，本地摘录见 `references/jingtian-essay-7000.md`）

本 skill 仅摘引片段作技法分析与语料研究，不修改、不续写、不商化原始内容。

---

## 平台限制

- **macOS GitHub Actions runner**: 默认 `macos-14` runner 上 mutmut 阶段会撞 libcst Rust 编译 + fork() 兼容性, 性能约为 Linux runner 的 30-50%。如需在 CI 跑 `gates --all`, 推荐 `ubuntu-latest` 跑 mutation 阶段, macOS 仅跑快速 7 门 (`uv run gates`)。
- **Windows 原生**: 不支持。mutmut 需要 `fork()`, Windows 必须在 WSL 内运行。
- **Python 版本**: ≥ 3.11 (pyproject.toml `requires-python = ">=3.11"`; mutmut 3.7.x 需 py3.10+, 本仓以 3.11 为下限)。
- **磁盘**: `mutmut` 阶段会临时生成 `mutants/` 目录 (默认几十 MB), `gates --all` 跑完自动清理。

## 免责声明

- 本 skill 的输出**不构成任何投资建议或法律建议**。
- 判断模式（judgment）整理的孙宇晨本人公开语料与商业动作，仅作为
  方法论研究的样本。用户在套用判断规则前应自行评估自身风险承受能力。
- 写作模式（writing）生成的文本仅作技法演示，请勿冒犯真实他人隐私。
- 详见 [LICENSE](./LICENSE) 第 3 节"商业判断免责声明"。
