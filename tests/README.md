# sunxue skill — 八层 Python 门禁工程

按 [PLAN.md §0](../PLAN.md#0-背景与目标) 实施。把 v1.0.0 的 6 个 stdlib
脚本升级为完整 Python 门禁工程，对应质量五维（正确性 / 安全性 /
可维护性 / 性能 / 成本效率）。plan 1.2 增补第 7 层 claims-lint
口径一致性门禁。

---

## 1. 八层门禁 × 命令 × 质量维度

| Layer | 工具 | 命令 | 质量维度 | 对应本项目 |
|---|---|---|---|---|
| Tests | pytest | `uv run pytest` | 正确性 | 门禁逻辑单元测试 + 属性测试 + 仓库级回归（`test_gates_live.py`） |
| Types（双门禁） | basedpyright + ty | `uv run basedpyright && uv run ty check .` | 可维护性 | 两个引擎互补：basedpyright 深度规则，ty 快速新锐；任一报错即 FAIL |
| Lint + format | ruff | `uv run ruff check . && uv run ruff format .` | 可维护性 | 门禁代码风格统一（line-length 100，select [E,F,I,UP,B]） |
| Changed-line coverage | coverage.py + diff-cover | `uv run pytest --cov=sunxue_gates --cov-branch --cov-report=xml --cov-fail-under=90` + `uv run diff-cover coverage.xml --compare-branch gate-v1.3.0 --fail-under=100` | 可维护性 | 无 fail-under 则该层永不失败；diff-cover 专门卡变更行 |
| Mutation | mutmut 3+ | `uv run mutmut run` | 正确性 | 幸存者 = 弱测试；产出 triage 报告（`tests/mutation-report.md`） |
| Property-based | hypothesis | `@given(...)` 随 pytest 运行 | 正确性 | 门禁逻辑的真实不变量（`tests/property/`） |
| Claims-lint（plan 1.2） | `lint_claims.run` | `uv run gates`（内嵌） | 可维护性 | 口径一致性：VERSION ↔ pyproject、README 目录树 ↔ 磁盘、阈值 ↔ tests/README、uv 命令 ↔ 已注册 CLI |

> 成功判据：上表所有命令退出码 0（变异层允许有书面豁免的幸存者，记录在
> `tests/mutation-report.md`）。

> diff-cover 的 `--compare-branch` 基线滚动策略与切换时点见 §8.3。

---

## 2. 质量五维映射（本项目版）

| 维度 | 约束 |
|---|---|
| 正确性 | 单元测试、属性测试、变异测试 |
| 安全性 | `scan_security`（PII/密钥/注入扫描）+ `injection_drill`（越狱演练）—— skill 文档的 SAST |
| 可维护性 | ruff + basedpyright + ty（双类型门禁）+ 覆盖率 + 结构 lint（体积/章节粒度） |
| 性能 | `token_budget` 冷启动耗时（性能预算） |
| 成本效率 | token 预算（字符/3 估算 + 软上限）—— skill 的"计算成本"就是上下文成本 |

---

## 3. 当前 tests/ 树

```
tests/
├── README.md                   # 本文件
├── conftest.py                 # 共享 fixtures（repo_path 等）
├── unit/                       # 纯函数单元测试
│   ├── test_parsing.py         # parse_frontmatter / classify_doc / count_h2
│   ├── test_results.py         # CheckResult / GateResult / merge_passed
│   ├── test_lint_structure.py  # 必含章节 / 体积上限 / 标题粒度
│   ├── test_scan_security.py   # PII / SECRET / INJECTION 正则
│   ├── test_regression_output.py  # 17 项硬计数
│   ├── test_token_budget.py    # est_tokens / 软上限
│   ├── test_injection_drill.py # 5 个演练向量
│   └── test_mutation_drill.py  # 3 种变异算子
├── property/                   # hypothesis 属性测试
│   ├── test_token_monotone.py          # est_tokens 单调 + n // 3
│   ├── test_frontmatter_roundtrip.py   # 合法 frontmatter round-trip + 任意输入不抛
│   ├── test_pii_secret.py              # 假数据命中 / 随机安全文本不误报
│   ├── test_mutation_operators.py      # 变异算子不变量（输≠入 / 确定性 / M3 软化强度词消失）
│   └── test_hard_metric_permutation.py # 硬指标与句序无关
├── test_gates_live.py          # 对当前仓库跑八门禁 run()，断言 PASS（v1.0 行为回归）
└── mutation-report.md          # mutmut 3.x triage（豁免台账见 mutation-exemptions.json）
```

---

## 4. 怎么跑

```bash
# uv 缓存路径覆盖（本机 sandbox 限制；按需删去前缀）
export UV_CACHE_DIR=.cache/uv

# 一行串跑八门禁（旧脚本的串跑契约保留为 console script `gates`）
uv run gates              # 等价于：uv run python -m sunxue_gates

# 全套八层门禁
uv run pytest                                                       # Tests
uv run basedpyright                                                  # Types（深度）
uv run ty check .                                                    # Types（速度）
uv run ruff check . && uv run ruff format .                          # Lint + format
uv run pytest --cov=sunxue_gates --cov-branch --cov-fail-under=90    # Coverage
uv run diff-cover coverage.xml --compare-branch gate-v1.3.0 --fail-under=100  # 变更行（基线滚动策略见 §8.3）
uv run mutmut run                                                    # Mutation（生成 triage）

# 对任意目录跑门禁（root 可参数化；__main__ 默认当前 repo 根）
uv run python -m sunxue_gates <root>
```

---

## 5. 设计要点

### 5.1 统一接口

每个门禁模块导出 `run(root: Path) -> GateResult`。`GateResult` 是 frozen
dataclass，至少包含：

- `name: str` —— 门禁名
- `passed: bool` —— 全部子检查通过
- `details: tuple[CheckResult, ...]` —— 每个子检查的 name / passed / message / detail
- `summary: str` —— 一行总结（PASS/FAIL + 数字）

`SKILL_ROOT` 不再是模块级常量，而是 `run(root)` 的参数；`__main__` 默认传
包父目录的父目录（repo 根）。这样门禁可以**对任意目录跑**（future worker.test
可以用 fixture 喂迷你仓库）。

### 5.2 各门禁要点

- **`lint_structure`** —— 解析极简 YAML frontmatter（无 pyyaml 依赖，手写解析单行 + 块标量）。必含章节用三组正则。体积上限分两类：SKILL.md 25k、reference 12k。章节切分粒度：二级标题 (##) 超过 80 个视为过碎。
- **`scan_security`** —— 扫描 SKILL.md / references/ / examples/ / README.md。
  三大类硬危险：PII（中国手机 / 身份证 / 银行卡 / 邮箱）/ SECRET（OpenAI /
  GitHub PAT / AWS / 私钥）/ INJECTION（忽略以上 / 角色劫持 / ChatML / Llama
  / 模板）。命中即 FAIL，退出 1；否则退出 0。
- **`regression_output`** —— 对 examples/ 4 个示例（`writing-巴菲特午餐`、
  `writing-示例2-被割版`、`writing-示例3-AI时代前端`、`judgment-老客户账期`）
  跑 17 项硬指标（`references/writing-checklist.md`）。全部 OK 才返回 0；
  任意一项 FAIL 则返回 1。`judgment-老客户账期` 是判断模式样本，部分硬指标
  （排比 / 反问 / 比喻等）可能不适用，脚本仍按统一规则跑出结果供人判断。
- **`token_budget`** —— 估算方式 `chars / 3`（英文常用近似；对中文偏紧，但
  作为预算告警足够）。软上限：SKILL.md ≤ 8_500 token、references/ 合计
  ≤ 16_000 token、单个 reference ≤ 4_000 token。输出冷启动时间
  （SKILL.md read + 估算的毫秒数）。
- **`injection_drill`** —— 5 个演练向量（D1~D5）：中文忽略 / 角色劫持 /
  ChatML / Llama / 模板注入。判据：每个向量至少命中 2 个防护关键词（从
  description 或全文搜），才算该向量防护到位。关键词表来自注入防御语料
  （注入 / 拒绝 / 不可信 / 系统段 / Llama / ChatML 等）。
- **`mutation_drill`** —— 从 SKILL.md 自动抽取 5 条包含核心动词（必须 /
  不要 / 改成 / 出庭作证 / 判断一个句子是否合格）的句子。对每条做 3 种
  变异：M1 同义词（必须→务必）/ M2 拆句 / M3 软化（必须→建议）。变异后，
  计算该句仍能命中几个硬指标关键词；命中 ≥ 1 视为变异不破坏硬约束。

### 5.3 退出码契约

全套统一：`PASS = 0`、`FAIL = 1`。`__main__.py` 串跑 6 个门禁，全部 PASS
才返回 0，否则返回 1，并打印失败列表。

---

## 6. 与 v1.0 的差异

- **v1.0** —— 6 个独立 stdlib 脚本（`tests/lint_structure.py` 等），无包结构、
  无类型、无覆盖率、无变异门禁
- **v1.1** —— 6 个门禁迁入 `src/sunxue_gates/` 包；新增 hypothesis 属性测试、
  mutmut 变异门禁、diff-cover 变更行门禁、双类型门禁（basedpyright + ty）

---

## 7. 完成判据对照

| 判据 | 对应命令 |
|------|----------|
| 全部 pytest 用例通过 | `uv run pytest` exit 0 |
| 双类型门禁清零 | `uv run basedpyright` + `uv run ty check .` 双 0 errors |
| ruff 风格一致 | `uv run ruff check .` exit 0 |
| 覆盖率达标 | `uv run pytest --cov-fail-under=90` exit 0（实际 100%） |
| 变更行全覆盖 | `uv run diff-cover coverage.xml --compare-branch gate-v1.3.0 --fail-under=100` exit 0（基线滚动见 §8.3） |
| 八门禁串跑 | `uv run gates` exit 0（8/8 PASS） |

---

## 8. Hooks & CI (PLAN §1.3)

`gates --all` 把八条验收命令串成一条命令；同时提供两层防护，让"代码进
仓库前"和"仓库进主分支后"两段时间都有门禁。

### 8.1 本地 pre-commit（快层）

`.githooks/pre-commit` 是纯 bash 钩子（无新增 Python 依赖），串跑快层
五条：

```
uv run ruff format --check .
uv run ruff check .
uv run basedpyright
uv run ty check .
uv run pytest -q
```

慢层（覆盖率 / diff-cover / mutmut）故意不进 pre-commit——mutmut 单跑
≈11s，留给 CI 与本地显式 `gates --all`。

一次性启用本仓库钩子路径（每个新克隆只需执行一次）：

```bash
git config core.hooksPath .githooks
```

跳过本次钩子：

```bash
git commit --no-verify
```

### 8.2 CI（慢层 + 完整链）

`.github/workflows/gates.yml` 在 `macos-14` 上跑：

```
uv sync --dev
uv run gates --all
```

`gates --all` 内部包含覆盖率 / diff-cover / mutmut，加上 pre-commit
的五条，正好八条。CI 的 stage table + total wall time 会写入工作流日志，
失败时定位到具体 stage 与 exit code。

### 8.3 diff-cover 基线 tag（plan 2.3）

`diff-cover --compare-branch` 跟随当前发布版本——每个 release 都打
`gate-vX.Y.Z` 形式的 annotated tag，下一次发版前的 `diff-cover` 用上一版
tag 作为对比基线。当前 v1.3.1 工作的基线 = `gate-v1.3.0`（v1.3.0 release
时打的 annotated tag）：

```bash
# 当前对比基线（v1.3.1 起，baseline = v1.3.0）
uv run diff-cover coverage.xml --compare-branch gate-v1.3.0 --fail-under=100

# 历史 annotated tag（保留供回溯，不作为基线）：
git tag -a gate-v1.1.0 -m "v1.1.0 — 七层 Python 门禁工程化 (plan 1.2);v1.2.0 八层 (plan 1.4 lint_pii 追加)"
git tag -a gate-v1.2.0 -m "v1.2.0 — SKILL.md 外化 + yingxue 镜像学科首次纳入"
git tag -a gate-v1.2.1 -m "v1.2.1 — 全面 audit 收口 (12 P0 + 18 P1 全修)"
git tag -a gate-v1.2.2 -m "v1.2.2 — patch 收口 (audit-v4 H-8 补打, 原漏标)"
git tag -a gate-v1.3.0 -m "v1.3.0 — 命名/常量清理 + yingxue-anatomy (audit-v4 H-8 补打, 原漏标)"

# 下一版对比基线会变成 gate-v1.3.1，依此类推。
```

**为什么这样改**：原 `gate-baseline` tag 是 v1.1.0 升级一次性锚定的，再没动过；
随着门禁代码自身被修改（claims-lint 加进第 7 位预算 / 性能预算 / token
精算），变更行永远在涨——`diff-cover` 对的基线必须随版本前进，否则 gate
意义递减。`claims-lint` 的 uv-commands 子检查已经会扫到 `--compare-branch`
后跟随的参数，所以一旦发版流程跑起来，命令行错位会立即报警。

**v1.2.2 迁移说明**：v1.2.2 patch 收口时，仓库 `--compare-branch` 从
`gate-baseline` 切到 `gate-v1.2.1`（v1.2.2 工作的 baseline）。`gate-baseline`
保留为历史一次性 tag 不删除（仍可 `git diff gate-baseline` 看 v1.0 起点）。

**audit-v4 H-8 补打说明（v1.3.1）**：v1.2.2 与 v1.3.0 两个 release 漏打
`gate-` 基线 tag（政策自 v1.2.2 起连续两版未执行），audit-v4 已按
`git tag -a gate-v1.2.2 0579c10` / `git tag -a gate-v1.3.0 219e877` 补打；
release 流程回归「每个 release 必打 gate-vX.Y.Z」纪律。

