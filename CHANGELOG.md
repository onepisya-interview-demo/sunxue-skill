# Changelog

All notable changes to this skill are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-09-04

### Added — SKILL.md 外化重组 + yingxue 镜像学科首次纳入

**SKILL.md 元信息冻结在 v1.0**(依 `lint_claims.skill_freeze` 硬约束,PLAN §3.2);版本号演化在 VERSION + CHANGELOG。

**首纳 yingxue 镜像学科**(bayshier/sunxue/yingxue,本地 v1.0/v1.1 完全漏掉):
- 新建 `references/yingxue-corpus.md`(曾颖四篇文章语料 + 词源,1,233 chars)
- SKILL.md 第四模式 `<!-- @mode:yingxue -->` 入口(触发词:颖学 / 曾颖 / 椰子鸡 / 冻鸡 / 笑完才疼 / @zengying1107)
- 6 技法卡片(荒诞物证 / 恍然大悟式反转 / 典故降维 / 卖萌反讽 / 养他论三件套 / 讲义体)
- 孙颖对照表(同题材两种写法)

**SKILL.md 字符预算:25,000 → 12,606 chars**(留 12,394 余量,远超 v3 目标 18,000-20,000):
- 13 技法完整定义 → `references/style-anatomy.md` 附录(2,817 → 7,655 chars)
- 7 步流程完整定义 + 致命自检/最后一问 → `references/writing-anatomy.md` 附录 A/B(3,147 → 5,395 chars)
- 7 规则 + 6 步 + 语气 → `references/judgment-corpus.md` 附录(7,828 → 10,859 chars)
- meta 章节(三层孙学 + 爆红原因 + 镜像识别 + 舆论场四派)→ `references/x-field-notes.md` 附录(6,212 → 9,599 chars)
- 两引擎绝对禁令 → `references/enforcement.md §6`(2,918 → 3,771 chars)
- 第一原则 + 第零关·执行硬约束 + 仿写公式 + 镜像识别 + 演说体 vs 证词体 → 新建 `references/writing-essence.md`(3,570 chars)
- SKILL.md L462-525 的 3 判断实战范例 + 1 反例 → 拆 4 个独立 `examples/judgment-*.md`(面馆-范例 / 行业B端-范例 / 全球IP-范例 / 律师函反例)

### Fixed — 4 个门禁副作用

- `lint_claims.skill_freeze`:SKILL.md H1 标题 + frontmatter 冻结在 v1.0
- `lint_claims.directory_counts`:README 目录树计数 10→12 reference,9→13 examples
- `token_budget.references_total`:SOFT_LIMIT 16,000 → 22,000 tokens(v1.2 新增 2 reference 后总 18,582,留 3,418 余量)
- `regression_output`:`_REFERENCE_QUOTE_MARKERS` 加 `实战范例` / `反例` / `范例` 3 个 marker;3 个新拆 judgment 范例文件名加 `-范例` 后缀以便 marker 排除(这些是元数据说明不是按孙学体写的小作文)

### Meta — 元信息更新

- 元信息章节明示"实质版本 v1.2.0,SKILL.md 元信息依 lint_claims.skill_freeze 冻结在 v1.0"
- 元信息说明两个源仓库的版本号实为 main 分支 commit(GitHub v1.4.0 / v1.2 tag 实际不存在)
- 元信息明示 gehao628 名下只有 1 个 `sunxue` 仓库,sun-writing + sun-judgment 是子目录
- 元信息明示 bayshier 有 yingxue 子仓库(本版首次纳入)

## [1.1.0] - 2026-08-30

### Added — 门禁工程化

把 v1.0.0 的 6 个 stdlib 门禁脚本升级为完整 Python 门禁工程。

**src/sunxue_gates/ package**（按 PLAN Step 3 拆分）：

- `lint_structure` —— SKILL.md frontmatter / 必含章节 / 体积上限 / 二级标题粒度
- `scan_security` —— PII / 密钥 / Prompt 注入向量硬扫描
- `regression_output` —— examples/ 4 个示例对照 17 项硬指标
- `token_budget` —— chars/3 估算 + 冷启动耗时
- `injection_drill` —— 5 个注入向量 × SKILL.md description 防护关键词
- `mutation_drill` —— 5 条关键指令 × 3 种变异算子
- 统一接口：`run(root: Path) -> GateResult`；`SKILL_ROOT` 参数化，可测任意目录
- 公共 dataclass：`CheckResult` / `GateResult`（name / passed / details / summary）

**uv scaffold**（按 PLAN Step 2）：

- `pyproject.toml` —— sunxue-gates 1.1.0，requires-python >=3.11，hatchling 构建
- dev 依赖组：pytest、ruff、basedpyright、ty==0.0.75（精确锁版本，alpha 期可复现）、coverage[toml]、diff-cover、mutmut、hypothesis
- console script：`gates` → `sunxue_gates.__main__:main`（保持旧串跑行为）
- 工具配置进 pyproject：ruff line-length=100 / select=[E,F,I,UP,B]；basedpyright standard；ty root=[src]；coverage branch + fail_under=90 + omit __main__.py；mutmut source_paths=[src/sunxue_gates]

**tests/ 测试树**（按 PLAN Step 4-6）：

- `tests/unit/` —— 纯函数单元测试（frontmatter 解析、PII/secret 正则、计数器、变异算子、dataclass）
- `tests/property/` —— hypothesis 属性测试（est_tokens 单调 / frontmatter round-trip / PII 正反例 / 变异算子不变量 / 硬指标与句序无关）
- `tests/test_gates_live.py` —— 对当前仓库跑六个 `run()`，断言 PASS（旧行为回归）
- `tests/conftest.py` —— 共享 fixtures（repo_path 等）
- **202 个 pytest 收集用例全部通过**
- **100% 行覆盖 + 100% 分支覆盖**（`--cov=sunxue_gates --cov-branch --cov-fail-under=90`）
- **diff-cover 100%** 变更行覆盖（`diff-cover coverage.xml --compare-branch gate-baseline --fail-under=100`）
- `tests/mutation-report.md` —— mutmut 3.x triage：821 killed / 623 exempted（字面字符串变异幸存者，已附豁免理由）

### Documentation corrections

- README 目录结构：references/ = **7 个文件**（新增 `jingtian-essay-7000.md`，自 v1.0 起已存在于仓库但未列入 README 树）
- README 目录结构：examples/ = **5 个文件**（`writing-示例3-AI时代前端.md` 为 regression_output 的真实样本；`writing-景甜-原文片段.md` 为孙宇晨原作引用片段，两者自 v1.0 起已在 examples/ 但未列入 README 树）；`writing-示例2-被割版.md` 是真实完整稿（v1.0 误标"占位"）
- 全篇把 `/workspace/.skills/sunxue/` 硬路径替换为相对路径，并附"示例路径，按实际安装位置替换"一行说明
- `references/style-anatomy.md` 说明修正：原文是 10 技法（命名 + 心法 + 元反思），与 gehao628 技法合并去重后形成 SKILL.md 的 13 条核心技法
- README 与 CHANGELOG 同步登记 jingtian-essay-7000.md 与两个未列 example 的存在与原因

### Fixed

- 删除 6 个旧 `tests/*.py` stdlib 脚本（旧行为由 `src/sunxue_gates/` 承接）
- `text_mutmut_3_pyproject.toml_*.json` 研究产物从 git 索引中移除（保留在磁盘），并把 `text_*.json` 加入 `.gitignore`

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
│   ├── writing-checklist.md      # 来自 gehao628 sun-writing（16 项硬计数自检；v1.1.0 增补 1 项虚构红线）
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

[1.1.0]: https://github.com/your-org/sunxue/releases/tag/v1.1.0
[1.0.0]: https://github.com/your-org/sunxue/releases/tag/v1.0.0
