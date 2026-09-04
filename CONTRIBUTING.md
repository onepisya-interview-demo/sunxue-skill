# Contributing to sunxue

> v1.2.2 起建立最小贡献规范。仓库规模小, 流程简短。

## 0. 读这之前先读

- `README.md` — 仓库是什么 + 怎么用
- `AGENTS.md` — 给 AI agent 的协作规范 (本文件是给人看的镜像)
- `tests/README.md` — 8 门禁 + diff-cover + mutmut 完整测试策略
- `references/writing-checklist.md` — 16 项硬自检 (samples/writing 必过)
- `references/enforcement.md` — 写作引擎绝对禁令 §6.2 + judgment 引擎禁用清单

## 1. 提交规范

commit message 遵循 Conventional Commits, 正文按 WHAT / WHY / HOW 三段:

```
<type>(<scope>): <subject>

WHAT: <做了什么> - 一句话, 动作 + 对象
WHY:  <为什么> - 业务动机 / 缺陷背景 / 需求编号
HOW:  <怎么做> - 整体策略 / 兼容性 / 验证方式
```

type: `feat` / `fix` / `docs` / `test` / `refactor` / `style` / `chore` / `build`

## 2. 开发流程

```bash
# 1. 装依赖
uv sync --dev

# 2. 跑单跑门禁
uv run gates

# 3. 跑全链 (含 mutmut, 允许 90s+)
uv run gates --all

# 4. 写 / 改 / 测

# 5. 再跑门禁
uv run gates

# 6. commit (Conventional Commits + WHAT/WHY/HOW)
```

## 3. 加新 example

1. 文件名遵循 `<mode>-<title>.md`, 如 `writing-我的题材.md` / `judgment-我的题材.md`
2. 内容按对应 mode tier 硬指标:
   - `writing-*` → `regression_output` 跑 17 项 strict
   - `judgment-*` → tier judgment 7 规则 + 1 防翻车
   - `meta-*` → tier meta 极简结构
   - `yingxue-*` → tier yingxue 6 技法 + 数字 ≥ 5
3. 不引号 (`「」""`) / 不感叹 / 不排比 (writing tier 硬约束)
4. 长度 1500-2500 chars 区间

## 4. 加新 reference

1. 文件名 `references/<name>.md`, ≤ 12,000 chars
2. 顶部 frontmatter 块 (HTML 注释格式, 见其他 reference):
   ```
   <!--
   Source: ...
   Original license: MIT
   合并说明: ...
   -->
   ```
3. 更新 README.md L241+ 目录树加 1 行
4. 跑 `uv run gates` 验证 references_total 不超 22,000 tokens

## 5. 加新门禁

1. `src/sunxue_gates/<gate>.py` 实现
2. `src/sunxue_gates/__init__.py` GATES 元组加 1 项
3. `src/sunxue_gates/__main__.py` `_ALL_CHAIN` 加 1 阶段
4. `tests/unit/test_<gate>.py` 单测
5. `tests/golden/literals.json` 锁定 EXPECT 字典
6. `tests/README.md` 表格 + 1 行
7. `pyproject.toml [tool.mutmut]` `do_not_mutate` 加 `<gate>.py` (literal 表保护)
8. 跑 `uv run gates --all` 8/8 PASS

## 6. PR 流程

1. fork → branch → 改 → commit → push
2. 开 PR, 填 `.github/PULL_REQUEST_TEMPLATE.md` 模板
3. CI 跑 `uv run gates --all` 8 阶段
4. 维护者 review + merge
5. 维护者负责 bump VERSION + pyproject + CHANGELOG + 标 release tag

## 7. 禁止事项

- ❌ 改 SKILL.md frontmatter (v1.0.0 frozen, 见 lint_claims.skill_freeze)
- ❌ 改 CHANGELOG.md 历史段的数字 (历史 release 当时真值, 不可逆)
- ❌ 改 examples/ 触发 regression_output FAIL (用 ASCII 引号 / 反引号避引号==0 约束)
- ❌ 删 v1.0.0 的合并首发内容 (CHANGELOG 1.0.0 段)
- ❌ 引入 PII (git config email 用自己环境的全局身份, 不用占位 / 假身份, 详见 AGENTS.md Git 身份约定)

## 8. 平台 / 环境

详见 README.md 「平台限制」段: macOS runner 性能问题, Windows 需 WSL, Python ≥ 3.10。
