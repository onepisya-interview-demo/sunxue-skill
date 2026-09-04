# AGENTS.md — sunxue-skill 协作规范

面向所有在本仓库工作的 AI agent 与人类贡献者。

## 版本与外化状态（v1.2.0 立，v1.3.1 audit-v4 更新）

- **SKILL.md 结构冻结，事实数字随版本同步（audit-v4 D1③ 裁决）**：`lint_claims.skill_freeze` 实际只锁两个标记——README 含「元信息冻结」注记 + SKILL.md 含「孙学 Skill v1.0」H1 子串；结构（frontmatter / 章节骨架 / 触发词组）保持冻结，事实数字与指针（样本计数 / reference 清单 / 版本叙述 / 必读清单）允许随 `VERSION` 演化同步更新。版本号演化在 `VERSION` 文件 + `pyproject.toml` + `CHANGELOG.md`。
- 实质版本演化：v1.0.0（合并首发，2026-08-28）→ v1.1.0（门禁工程化，2026-08-30）→ v1.2.0（SKILL.md 外化 + yingxue 镜像学科首次纳入）→ v1.2.1（7 维度 audit 收口）→ v1.2.2（patch 收口）→ v1.3.0（命名清理 + yingxue-anatomy + 强示范 example）→ v1.3.1（audit-v4 全面审计收口，均 2026-09-04）。
- SKILL.md 字符预算：`lint_structure` 硬上限 25,000 chars；v1.3.1 实测 12,708 chars（留 12,292 余量）。
- references/ 字符预算：每个 ≤ 12,000 chars；v1.3.1 实际 13 个 reference，总 60,896 chars / 20,298 tokens（est = Σ⌊chars/3⌋，`token_budget.references_total` 上限 22,000；yingxue-anatomy.md 3,515 chars / 1,171 tokens——v1.3.0 曾误记字节数 7,621 为 chars，audit-v4 勘误）。
- 4 模式路由：description 触发词命中即加载对应 `<!-- @mode:writing|judgment|meta|yingxue -->` 章节。

## 提交规范：Commit-as-Prompt（WHAT / WHY / HOW）

> 本仓库全部历史提交已于 2026-08-31 按本规范改写完成，新提交必须延续同样格式。

### 1. 标题：Conventional Commits

- 格式：`<type>(<scope>): <subject>`
- type：feat / fix / docs / test / refactor / style / chore / build，另有 `prompt`（见第 3 节）
- subject 用祈使句、具体明确；禁止「修复 bug」「更新代码」类模糊词

### 2. 正文：WHAT / WHY / HOW 三段（不带编号，各一行）

    WHAT: <做什么> — 一句话，动作 + 对象，祈使动词，不含实现细节
    WHY:  <为什么> — 业务动机 / 缺陷背景 / 需求编号 / 架构权衡，避免泛泛而谈
    HOW:  <怎么做> — 整体策略、兼容性 / 依赖、验证方式、风险与影响；不罗列文件清单（diff 已体现细节）

### 3. prompt: 类型提交（Context Prompt）

- 需要转成 AI 上下文 Prompt 的提交，标题以 `prompt(<scope>):` 开头，正文同样 WHAT / WHY / HOW
- prompt 类与常规 feat / fix / docs 类提交分开，不混排
- 聚合输出格式（多条 prompt 提交合并为一段上下文）：

        <Context>
        1. [WHAT] ...
           [WHY] ...
           [HOW] ...
        2. [WHAT] ...
           [WHY] ...
           [HOW] ...
        </Context>

### 4. 拆分原则

- 一次提交聚焦单一主题；多个主题必须拆分为多次提交
- 纯格式化、依赖升级、大规模重命名作为独立提交，不与功能变更混合
- 只暂存与当前主题相关的文件（`git add -p` 或按文件暂存）

### 5. 示例

    fix(gates): mutmut stage env workaround inside gates --all

    WHAT: gates --all 内置 mutmut 阶段的环境变通
    WHY: mutmut 3.x 在 --all 子进程环境中读不到自身配置导致阶段假失败，掩盖真实结果
    HOW: 阶段执行时注入所需环境变量；--all 端到端恢复全绿

## 仓库速览

- Python 门禁工程：`src/sunxue_gates`（八门禁：lint_structure / scan_security / regression_output / token_budget / injection_drill / mutation_drill / lint_claims / lint_pii）+ `tests/` + `SKILL.md` / `references` / `examples`
- 一键验收：`uv run gates --all`；本地快速层 pre-commit 需 `git config core.hooksPath .githooks` 手动启用（激活与跳过步骤见 tests/README §8.1）
- Skill 自身门禁：SKILL.md 写作引擎第 7 步为「门禁回环（gate loop）」硬约束——写完自动跑 `references/writing-checklist.md` 的 16 项硬自检（v1.1.0 增补 1 项虚构红线），任何一项不过 → 回炉 → 再跑，全部通过才交付。详见 `SKILL.md` §七步写作流程。
- Git 身份：提交者使用**自己环境**的全局 git 身份，规范中不写死任何个人邮箱；本仓库 local config 禁止配置假身份 / 占位身份（即无主人的机器占位地址，形如「用户名 + @ + 本地域名」——为免触发 scan_security 邮箱硬规则，此处不书写字面量）
- 历史改写（message / 身份）需连带重写 tags（`--tag-name-filter cat`）并清理 `refs/original` + reflog + gc，确保旧对象物理清除
