## 变更说明

<!-- 一句话说明这次 PR 改了什么 -->

## 关联 issue

<!-- 关联的 issue 编号, 如 Fixes #N / Refs #N -->

## 门禁自检

- [ ] `uv run gates` 单跑 8/8 PASS
- [ ] `git diff <baseline>..HEAD -- coverage.xml` 变更行覆盖率 100%（baseline = tests/README §8.3 当前基线，现为 `gate-v1.3.1`）
- [ ] 没有引入新 mutmut survivor (除非在 mutation-exemptions.json 标注)
- [ ] 没有引入新 lint_pii 命中
- [ ] SKILL.md frontmatter 未修改 (v1.0.0 frozen, 见 lint_claims.skill_freeze)

## 受影响文件

<!-- 列出受影响的文件 + 简述变更意图 -->

## 测试证据

<!-- 贴 `uv run gates` 输出最后 5 行 -->

## 风险评估

<!-- 标 low / medium / high, 并说明 -->

## Checklist

- [ ] commit message 遵循 Conventional Commits (`<type>(<scope>): <subject>`)
- [ ] 正文按 WHAT / WHY / HOW 三段
- [ ] 不与 CHANGELOG.md / VERSION / pyproject.toml [project] version 三方数字漂移
- [ ] 引用 docs 用 `path:line` 格式

<!-- 感谢贡献! 任何门禁不过请勿 merge, 见 tests/README.md §8.3 diff-cover baseline 策略 -->
