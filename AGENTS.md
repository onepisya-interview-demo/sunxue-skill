# AGENTS.md — sunxue-skill 协作规范

面向所有在本仓库工作的 AI agent 与人类贡献者。

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

- Python 门禁工程：`src/sunxue_gates`（七门禁）+ `tests/` + `SKILL.md` / `references` / `examples`
- 一键验收：`uv run gates --all`；本地快速层 pre-commit 需 `git config core.hooksPath .githooks` 手动启用
- Git 身份：提交者使用**自己环境**的全局 git 身份，规范中不写死任何个人邮箱；本仓库 local config 禁止配置假身份 / 占位身份（如 `gates@sunxue.local` 这类机器身份）
- 历史改写（message / 身份）需连带重写 tags（`--tag-name-filter cat`）并清理 `refs/original` + reflog + gc，确保旧对象物理清除
