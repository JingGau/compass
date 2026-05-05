# Harness 发版前检查清单

## 1. 结构完整性

- `python3 scripts/check_harness_ready.py` 通过
- `compass_cli/__main__.py`、`compass_core/{runtime,state,intake,report,masking,kb,knowledge,timeline}.py`、`tools/{action_cards,sql_gate,setup_check,python_env}.py` 均存在
- `references/{intake-and-state,runtime-protocol,safety-and-capabilities}.md` 与 `guards/{sql,redis,es,data-masking}-safety.md` 与代码保持一致
- 旧 v3 模块只在 `legacy/` 目录下出现，主流程不再 import 它们
- `memory/knowledge.yaml` 存在（默认空，作为 KB Learn 底底文件）；`.gitignore` 已排除该文件

## 2. 代码与静态检查

- `python3 -m py_compile compass_cli/__main__.py compass_core/*.py tools/*.py adapters/*/client.py adapters/base.py` 通过
- `python3 -m pytest tests/` 全部通过
- IDE lint 无新增错误

## 3. 流程功能检查

- `python3 -m compass_cli setup-check --json` 输出最小配置就绪状态
- `python3 -m compass_cli start "<冒烟问题>" && python3 -m compass_cli confirm --mode auto && python3 -m compass_cli next` 可正常推进 phase
- prod 环境 `action plan --track sql` 缺少 `input.explain_text` 时被 runtime 阻断，错误信息明确
- 中/高风险 SQL `action plan` 后必须经 `action confirm` 才能 `action complete`
- `compass kb learn` 写入 `memory/knowledge.yaml` 后 `compass kb suggest --query ...` 能召回；`compass start` 后 `state.applicable_knowledge` 字段非空时 CLI 输出"适用知识"提示
- `compass change record` 写入后 `compass timeline` 能渲染时间线；report technical 头部能看到时间线 + 变更窗口
- `compass conclude` 在 confidence=high 但缺强证据 / 缺 mitigation / 缺 remediation / 支持假设缺 falsifiable / 根治项缺 owner / TL;DR 超过 3 句 时返回 quality_warnings；report 渲染"结论质量提示"段
- `scene fact --category diff` 缺对比词时被运行时拒绝
- `compass conclude --tldr ... --severity ... --detected-at ... --acknowledged-at ... --mitigated-at ... --resolved-at ...` 后 report 头部能看到 TL;DR 卡片 + 严重等级标签 + MTTD/MTTM/MTTR 时序表（MTTM = acknowledged → mitigated）
- `compass conclude --remediation-item "desc=...;owner=@x;due=...;url=...;status=..."` 后 report"止血与根治"段渲染为带 Owner/Due/状态/链接的表
- runtime 自动把 `inference_chain` 拆为 `inference_steps`，report 渲染为有序步骤表（步骤 # / 推断 / 引用证据）
- prod 环境 `action plan --track sql` 后 `gate.explain_text` 落盘了 EXPLAIN 原文；report Action Card 用 fenced 代码块显示原文（可一键复制）
- `compass evidence add --change C1` 与 `compass hypothesis add --change C1` 在引用不存在的变更时会被 runtime 拒绝；timeline 表会用 ⤴ 标识"变更→证据"连线
- `report --audience postmortem` 输出事故复盘十段式 Markdown

## 4. 安全与门禁

- `guards/sql-safety.md` 三档判定与 `tools/sql_gate.assess_sql_explain` 行为一致
- `guards/data-masking.md` 描述的脱敏字段与 `compass_core/masking.py` 已实现的覆盖范围一致（差异需在文档中显式标注）
- SLS plan 缺少高区分度 anchor 或包含泛词时会被 `_validate_sls_query_policy` 拒绝

## 5. Adapter 标准化

- 5 个 adapter 的 `health_check()` 返回结构统一：
  - `adapter`
  - `status`
  - `latency_ms`
  - `environment`
  - `error`
- 所有 adapter 凭证均通过 `${ENV_VAR}` 注入，`adapters/*/config.yaml` 不含明文密钥

## 6. 文档与配置

- `README.md`、`SKILL.md` 与代码命令链一致；不留旧 v3 step-based 流程描述
- `.env.example` 列出所有 adapter profile 模板与可选 `COMPASS_PYTHON` / harness 阈值变量
- `legacy/README.md` 说明旧模块停用原因与等价替代
