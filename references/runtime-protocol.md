# Runtime Protocol Reference

## CLI Runtime Priority

当本 Skill 目录存在 `compass_cli/` 时，Agent 必须优先通过 CLI Runtime 维护排查会话。

Agent 使用罗盘排查时必须完整遵循 Runtime 流程。禁止直接调用 adapter、直接查日志/SQL/代码后再补状态；CLI 返回失败时，必须修正输入或补证据，不能在对话中绕过。

罗盘是 investigation-only 工具，只查询、定位、沉淀证据和输出结论。禁止在罗盘流程中修改业务代码、生成补丁、提交代码或执行修复；修复工作应在罗盘报告之外另起开发任务。

## Phase 状态机

CLI Runtime 维护五个 phase，状态字段保存在 `memory/session-state.yaml`（JSON 格式）中：

```text
new
  → start            → awaiting_confirmation
  → confirm          → action_ready
  → scene fact /     → evidence_collecting
    action plan      ↑
  → conclude         → concluded
  → report           → reported
  → strategy keep/discard
  → reopen           → evidence_collecting（revision+1，旧 conclusion 进 history）
```

每个 phase 的下一步由 `state.flow.allowed_commands` 显式列出；写状态的命令同时由 runtime 的 phase guard 和关键前置条件硬拦截。关键前置条件包括：未 `confirm` 禁止写入排查动作；缺少 `scene fact` 禁止 `action plan`；未生成 `report` 禁止 `strategy keep/discard`；`concluded/reported` 后禁止继续补 action/evidence，除非 `reopen`。

## 核心命令

- `start` / `confirm` / `next`：进入排查、确认执行模式、获取下一步建议。`start` 会自动从 `memory/knowledge.yaml` 召回 top-5 相关知识写入 `state.applicable_knowledge`，并把它们加入 hits 计数。
- `confirm --mode auto`：首轮人工确认后由 Agent 自动推进后续流程；只有用户打断、runtime 门禁失败、prod 中高风险 SQL、外部/高风险数据源或缺少关键实体时暂停。`confirm --mode manual` 才要求每一步查询前等待用户确认。
- Agent 自动模式直接调用 SLS/Doris adapter 时，必须带 `COMPASS_AGENT_AUTO=1`、`COMPASS_RUNTIME_STATE_FILE` 和 `COMPASS_RUNTIME_ACTION_ID`；adapter 会校验 action 已确认、已规划、track 匹配且 status=planned。缺少上下文时拒绝裸查。人工直接使用 adapter 不设置 `COMPASS_AGENT_AUTO`，不受该保护影响。
- `scene fact`：在记录假设或写结论前，先用 `category=entrypoint/object/upstream/downstream/config/variant/diff/baseline/repro` 把可引用事实落盘；`category=diff` 强制 value 含对比词（差异/对比/vs/相比/之前/之后/正常/异常/变更等）；建议带 `--event-at` 让事实进入 timeline。
- `action plan` → `action complete`：每次实际查询、读代码、拉日志的成对调用；`plan` 前必须已经有至少一条 `scene fact`，否则 runtime 拒绝；`plan` 写目标/输入/成功标准/门禁，`complete` 写摘要/发现/线索并自动生成 evidence；`complete` 与 `evidence add` 都支持 `--event-at` 进入 timeline。
- `action confirm`：仅当 `plan` 因 SQL 风险等门禁被锁为 `requires_confirmation` 时使用，由用户明确确认风险后解锁。
- `change record` / `change list`：登记发布、配置、数据迁移、灰度、权限调整等变更，必填 `--type/--target/--description/--event-at`，进入 timeline 与故障窗口对齐。
- `timeline`：把所有带 `event_at` 的 changes / scene_facts / evidence 与 action_history 合并为按时间排序的故障时间线。
- `evidence add`：手工补录证据（用户提供的截图、外部线索等）。可用 `--change C1 --change C2` 把证据关联到一笔或多笔已登记变更，timeline 表会用 ⤴ 标识"变更→证据"连线。
- `hypothesis add`：基于 scene fact / evidence 派生新假设；不允许凭空假设；推荐用 `--falsifiable` 给出反证条件，可用 `--change C1` 显式关联到引发猜想的变更。
- `conclude`：写结构化结论。除原有 5W1H + Inference Chain 外，新增字段：
  - `--mitigation` / `--remediation`（纯文本可重复传）
  - `--mitigation-item` / `--remediation-item`（结构化 `desc=...;owner=...;due=...;url=...;status=...`）
  - `--unsolved`（未解之谜，可重复传）
  - `--pattern-scan`（同类扫描方向，可重复传）
  - `--hypothesis`（本结论引用的假设 id，可重复传）
  - `--tldr "<≤3 句执行摘要>"`：给非技术决策者一眼看完，超 3 句会触发 `TLDR_TOO_LONG` 警告
  - `--severity sev1|sev2|sev3|sev4`：不传则按 blast_radius 启发式推荐
  - `--detected-at / --acknowledged-at / --mitigated-at / --resolved-at`：用于报告头部的 MTTD/MTTM/MTTR 时序表（MTTM = acknowledged → mitigated）
  会输出 `quality_warnings`：confidence=high 缺强证据 / 推断链缺因果连接词 / mitigation 或 remediation 为空 / 根治项缺 owner / 支持的假设缺 falsifiable / 存在 status=支持 的假设但 conclude 未引用 / TL;DR 超过 3 句 等情况。
  runtime 同时会自动把 `inference_chain` 按 → / 因为-所以 / 从…到…使… 拆为 `inference_steps`，报告会渲染为有序步骤表。
- `reopen`：进入新 revision；旧 conclusion 自动归档到 `conclusion_history`。
- `report`：按 `--audience technical|business|review|postmortem` 渲染 Markdown。结论后的第一次 report 会把 phase 推进到 `reported`，并记录 `flow.report_generated=true`。`postmortem` 为事故复盘十段式（Executive Summary / Impact / Detection / Response / Recovery / Root Cause / Action Items / Lessons Learned / References / Timeline），内容与 technical 共用同一套 state，仅章节编排不同。
- `strategy keep` / `strategy discard`：报告后必走的最终查询策略沉淀确认；未生成 report 会被 runtime 拒绝。
- `kb learn` / `kb suggest` / `kb list` / `kb search`：通用知识库（`memory/knowledge.yaml`）。`learn` 录入一句话事实/规则（≤300 字）；`suggest` 按 query/tags 召回 top-N 并可选 `--increment-hits`；`search` 同时搜 markdown 知识与 yaml 知识。

## Action Lifecycle

每次实际查询、读代码、拉日志前：

1. `action plan` 写入目标、输入、成功标准和门禁。
2. 执行真实查询或阅读动作。
3. `action complete` 写入摘要、发现、线索，生成 evidence 和 action history。
4. 如产生新场景事实，用 `scene fact --evidence E<n>` 绑定证据。
5. 如产生新假设，用 `hypothesis add --source-fact ... --source-evidence ...`。

存在 planned action 时，`next` 必须优先提示完成或调整计划，不能直接结论。

## Reopen And Revision

`concluded/reported` 后禁止继续补证据。收到新信息时：

```bash
python3 -m compass_cli reopen --reason "<为什么需要修订>"
```

reopen 会把当前 conclusion 写入 `conclusion_history`，标记 `status=superseded`，递增 `revision`，并回到 `evidence_collecting`。后续证据和新结论属于新 revision。

## Evidence Quality

创建证据时尽量提供：

- `--kind manual|user|log|sql|code|kb|inference`
- `--strength weak|medium|strong`
- `--raw-ref <traceId/sql/code path/kb path>`

证据质量会进入 technical report。用户口述通常不应直接作为 strong 结论证据；日志、SQL、代码互相印证时可提升强度。

## Action Card Protocol

任何查询、日志搜索、代码读取、Redis/ES 访问都必须先构造动作卡，再执行。禁止直接调用 adapter 或直接读代码后再补过程说明。

顺序：

1. 构造 `tools.action_cards.InvestigationAction`，写明目的、工具、环境、查询对象、成功标准。
2. 输出 `render_before_card(action)`。
3. 输出 Safety Gate；SQL 由 `compass_cli action plan --track sql --input "explain_text=..." ...` 触发 runtime 内部调用 `tools.sql_gate.assess_sql_explain`，结果直接覆盖 Agent 自报字段，Agent 不能伪造。
4. 若 `gate.requires_confirmation=true`，runtime 会把 action 标记为 `requires_confirmation` 并阻断 `complete`，必须先 `python3 -m compass_cli action confirm --action-id <id>` 由用户解锁。
5. 执行查询 / 读代码 / 拉日志。
6. 构造 `tools.action_cards.ActionResult`，输出 `render_after_card(action, result)`。

| 轨道 | 执行前必须展示 | 执行后必须提取 |
|------|----------------|----------------|
| SLS | query、时间范围、anchor、keyword_source、limit、容器/服务 | traceId/tlogId、接口、服务、异常时间、后续代码/DB/链路 |
| SQL | 完整 SQL、环境、EXPLAIN 原文（prod 强卡）、风险等级 | 返回行数、关键字段、相关表、是否指向代码/日志 |
| 代码 | 应用、文件/类/方法、来源线索 | 页面→接口→Controller→Service→Mapper→表、日志关键字、业务分支 |
| Redis/ES | 命令/索引/查询体、范围限制 | key/index、命中摘要、是否指向 SQL/代码/日志 |

## 强制门禁

- `phase` 不匹配时，runtime 会抛 `CompassRuntimeError`，禁止推进。
- `plan_action(track='sql', env='prod')`：必须传 `input.explain_text`，runtime 内部调 `assess_sql_explain` 真验证；中/高风险自动锁住，必须 `action confirm` 后才能 `action complete`。
- `plan_action(track='sls')`：必须有高区分度实体作为 `anchor`（订单号、支付单号、用户ID、手机号、traceId、枪编码、站点名等）；额外关键词必须声明 `keyword_source=code/sql/schema/table_field/code_sql`，禁止 Agent 自己猜业务词。
- `action plan/confirm/complete`：CLI 输出必须先给自然语言说明，再给命令原文、门禁评估和结构化结果；JSON 输出使用同一份 `display` 字段。
- 门禁规则可通过环境变量调整：`COMPASS_SQL_GATE_MEDIUM_ROWS`、`COMPASS_SQL_GATE_HIGH_ROWS`、`COMPASS_SLS_GENERIC_KEYWORDS`、`COMPASS_SLS_KEYWORD_SOURCES`。`COMPASS_NON_PROD_RELAX_GATES=1` 只放宽非生产环境；prod 强制门禁不可关闭。
- `conclude` 必须满足 8 个结构化字段（`what/where/when/why_technical/why_business/blast_radius/how/inference_chain`），且引用真实存在的 evidence id。
- 默认环境为 `prod`；SQL plan 未显式提供 `env` 时 runtime 使用 session 环境，默认就是 `prod`。

## Special Entrypoints

| 用户说 | 执行 |
|--------|------|
| 配置 / setup / 初始化 | `prompts/setup.md` |
| 注册项目 | `prompts/project-onboarding.md` |
| 扫描前端整理知识 | `prompts/knowledge-batch-scan.md` |
| 注册页面 | `prompts/knowledge-onboarding.md` |
| 加个 XX 能力 | `adapters/_convention.md` |
| 知识库现状 | 汇总 projects/ + adapter 状态 + 策略数量 |
