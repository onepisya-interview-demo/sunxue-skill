# sunxue skill — 门禁测试套件

本目录是 `/workspace/.skills/sunxue/` 的 6 个门禁脚本 + 1 份说明。所有脚本独立可执行, 不依赖外部网络, 也不装新包。

## 脚本一览

| 脚本 | 类型 | 测什么 | 退出码 |
|------|------|--------|--------|
| `lint_structure.py`   | 迁移 (旧 `门禁_结构lint.py`) | SKILL.md frontmatter / 必含章节 / 体积上限 / 章节切分粒度 | 0=PASS, 1=FAIL |
| `scan_security.py`    | 迁移 (旧 `门禁_安全扫描.py`) | PII / 密钥 / Prompt 注入向量扫描 | 0=干净, 1=硬命中 |
| `regression_output.py`| 迁移 (旧 `门禁_输出回归.py`) | examples/ 三个示例对照 15 项硬指标 | 0=全部通过, 1=至少一项 FAIL |
| `token_budget.py`     | 新增 | 字符/3 估算 token, 单文件与全量上限, 冷启动耗时 | 0=在软上限内, 1=超限 |
| `injection_drill.py`  | 新增 | 5 个注入向量, 检查 description 是否写明防护 | 0=5 个全 PASS, 1=至少 1 个 FAIL |
| `mutation_drill.py`   | 新增 | 5 条关键指令 × 3 种变异, 检查变异后仍能命中硬指标 | 0=全部 PASS, 1=变异破坏约束 |

## 硬指标来源

- 15 项硬计数自检: `references/writing-checklist.md`
- 体积上限: `SKILL.md ≤ 25_000 字符`, `reference ≤ 12_000 字符` (来自合并方案)
- 注入向量: 来源于 `scan_security.py` 旧版并扩到 5 类

## 怎么跑

```bash
cd /workspace/.skills/sunxue/tests

# 一个一个跑
python3 lint_structure.py
python3 scan_security.py
python3 regression_output.py
python3 token_budget.py
python3 injection_drill.py
python3 mutation_drill.py

# 或一行串跑 (推荐)
for s in lint_structure scan_security regression_output token_budget injection_drill mutation_drill; do
  echo "=== $s ==="
  python3 "$s.py"
  echo "exit=$?"
done
```

## 每个脚本的设计要点

### lint_structure.py
- 解析极简 YAML frontmatter (无 pyyaml 依赖, 手写解析, 单行 / 块标量)
- 必含章节用三组正则: `第一原则|心法|写作引擎|判断引擎|方法论` / `触发词|触发|适用于|命中` / `红线|铁律|禁令|绝对禁令|不要`
- 体积上限分两类: SKILL.md 25k, reference 12k
- 章节切分粒度: 二级标题 (##) 超过 80 个视为过碎

### scan_security.py
- 扫描 SKILL.md / references/ / examples/ / README.md
- 三大类硬危险: PII (中国手机 / 身份证 / 银行卡 / 邮箱) / SECRET (OpenAI / GitHub PAT / AWS / 私钥) / INJECTION (忽略以上 / 角色劫持 / ChatML / Llama / 模板)
- 命中即 FAIL, 退出 1; 否则退出 0

### regression_output.py
- 对 examples/ 三个示例 (writing-巴菲特午餐, writing-示例2-被割版, judgment-老客户账期) 跑 15 项硬指标
- 全部 OK 才返回 0; 任意一项 FAIL 则返回 1
- judgment-老客户账期 是判断模式样本, 部分硬指标 (排比 / 反问 / 比喻等) 可能不适用, 脚本仍按统一规则跑出结果供人判断

### token_budget.py
- 估算方式: `chars / 3` (英文常用近似; 对中文偏紧, 但作为预算告警足够)
- 软上限: SKILL.md ≤ 8_500 token, references/ 合计 ≤ 16_000 token, 单个 reference ≤ 4_000 token
- 输出冷启动时间 (SKILL.md read + 估算的毫秒数)

### injection_drill.py
- 5 个演练向量 (D1~D5): 中文忽略 / 角色劫持 / ChatML / Llama / 模板注入
- 判据: 每个向量至少命中 2 个防护关键词 (从 description 或全文搜), 才算该向量防护到位
- 关键词表来自注入防御语料 (注入 / 拒绝 / 不可信 / 系统段 / Llama / ChatML 等)

### mutation_drill.py
- 从 SKILL.md 自动抽取 5 条包含核心动词 (必须 / 不要 / 改成 / 出庭作证 / 判断一个句子是否合格) 的句子
- 对每条做 3 种变异: M1 同义词 (必须→务必) / M2 拆句 / M3 软化 (必须→建议)
- 变异后, 计算该句仍能命中几个硬指标关键词; 命中 ≥ 1 视为变异不破坏硬约束

## 完成判据对照

| 判据 | 对应脚本 |
|------|----------|
| 6 个脚本存在 | `ls *.py` 应有 6 个 |
| 每个脚本 `python3 xxx.py` 跑得动 | 见上"怎么跑" |
| 至少 3 个核心脚本输出真实结果 | `lint_structure / scan_security / regression_output` 全部跑出结构化结果 |
| 退出码策略 | 全套脚本统一: PASS=0, FAIL=1 |

## 禁止项的遵守

- 不装新包: 全程用标准库 (re, sys, pathlib, time, collections)
- 不依赖网络: 没有任何 HTTP 调用
- 不写假装的"代码覆盖率"数字
- 不写"圈复杂度"
