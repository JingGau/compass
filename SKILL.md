---
name: compass-harness
description: "Use when investigating C端/B端/财务/订单/充电线上问题 with incomplete inputs, multi-turn context, local knowledge, code, logs, data adapters, and evidence-chain root cause analysis."
---

# Compass Harness

Compass 是本地优先的线上问题排查 harness。核心职责不是“让 AI 直接查数”，而是让 Agent 通过 CLI Runtime 把问题结构化、规划动作、执行门禁、沉淀证据、派生假设并输出可追溯结论。

优先级：**CLI/Core 程序约束 > 本 Skill 指令 > 对话习惯**。能由程序校验的规则必须交给 harness，不只靠模型自觉。

## Agent Contract

- Skill 只决定“何时启用罗盘”和“如何和用户协作”；状态、门禁、证据、报告由 CLI Runtime 决定。
- 罗盘没有会话级执行分支；只需要首轮 `confirm`，之后 Agent 按 `next --json` 的 `task` 持续推进，直到用户打断或 runtime 门禁要求确认。
- Hermes/minimax 等 runner 必须通过 `scripts/compass-agent-runtime.sh <agent-command>` 或等价环境启动，确保全进程 `COMPASS_ADAPTER_MODE=runtime`。
- Agent 调 adapter 必须通过 `compass action env --action-id <id>` 获取 action 级 runtime 环境；人类临时调试 adapter 不设置这些变量，不进入罗盘证据链。
- Agent 读代码必须通过 `compass code search/show --action-id <id>`，并且该 id 必须是已规划的 `track=code` action。
- 如果 Skill 文字和 CLI 输出冲突，以 CLI 输出的 `display`、`health`、`task` 和错误信息为准。

## When To Use

Use this skill for:

- C端/B端/财务/订单/充电线上问题排查
- 多轮信息混杂、输入不完整、需要代码/日志/数据/知识库共同定位的问题
- 需要证据链、影响面、根因、修复建议的场景
- 需要 Codex、Claude Code、OpenClaw、Hermes 等 Agent 通过同一套本地能力排查的问题

Do not use this skill for:

- 纯闲聊或业务概念解释
- 不需要证据链的简单代码阅读
- 用户明确要求不要查询、不要启动排查流程的场景

## Mandatory Workflow

1. 默认使用线上环境 `prod` 排查；只有用户明确指定 test/uat/测试/预发时才切换环境。
2. 首轮只做 Problem Intake 和方案确认，禁止调用 adapter。`compass start` 会自动从通用知识库（`memory/knowledge.yaml`）召回 top-5 适用知识，Agent 必须把它们当成"待校对的提示"而不是"已认证的事实"。
3. 用户完成 `confirm` 后，Agent 必须按 CLI Runtime 持续推进，不要每一步都询问是否继续；只有用户主动打断、runtime 硬门禁失败、prod 中高风险 SQL、外部/高风险数据源、缺少关键实体时才暂停请用户决策。
4. 用户确认后，必须使用 CLI Runtime 维护状态，不得跳过 start/confirm/scene/action/evidence/conclude/report 流程；runtime 会拦截未确认、缺 scene fact、未 report 就策略沉淀等顺序错误。
   - Hermes/minimax 等 runner 必须用 `scripts/compass-agent-runtime.sh <agent-command>` 或等价环境启动，不能绕过 runtime guard。
   - Agent 调用 SLS/Doris adapter 时必须处于已规划 action 上下文：优先运行 `compass action env --action-id <action_id>` 获取 `COMPASS_ADAPTER_MODE=runtime`、`COMPASS_RUNTIME_GUARD=1`、`COMPASS_RUNTIME_STATE_FILE=<state>`、`COMPASS_RUNTIME_ACTION_ID=<action_id>`。裸调 SLS/Doris adapter 会被拒绝；人工直接使用 adapter 不设置这些变量，不受影响。
   - Agent 读取业务代码时必须先规划 `track=code` action，再用 `compass code search/show --action-id <action_id>`；裸 `rg/sed/cat` 只允许作为人类临时调试，不计入罗盘证据链。
5. 每次制定 `action plan` 前，Agent 必须把 `knowledge/playbooks/` 作为策略参考上下文之一；若匹配到适用 playbook，应在 action objective/source/success-criteria 或后续 evidence finding 中体现采用了哪条 playbook。Playbook 只辅助选择侦查路径，不替代 Runtime 门禁。
6. 先记录 `scene fact`，再通过 `action plan -> action complete` 生成 evidence；没有 scene fact 时 `action plan` 会被拒绝。当排查涉及"前后对比"时，必须用 `scene fact --category baseline` / `--category diff` 把"正常态 vs 异常态"显式落盘。
7. 新假设必须引用 scene fact 或 evidence；建议同时通过 `--falsifiable` 给假设填反证条件（"如果 X 不成立则该假设不成立"），让结论可证伪。
8. 排查过程中如果定位到疑似变更（发布、配置、数据迁移、灰度等），必须用 `compass change record --type ... --target ... --description ... --event-at ...` 登记，进入故障 timeline 与变更窗口。
9. 结论必须通过 `conclude`，引用已存在 evidence，并填写结构化细节；同时必须显式给出 `--mitigation`（止血）和 `--remediation`（根治），未解之谜走 `--unsolved`，同类扫描方向走 `--pattern-scan`，引用的关键假设走 `--hypothesis`。`conclude` 输出的 `quality_warnings` 必须读完并响应。
   - **强烈建议**同时提供：`--tldr "<≤3 句执行摘要>"`、`--severity sev1|sev2|sev3|sev4`、以及四个时间戳 `--detected-at / --acknowledged-at / --mitigated-at / --resolved-at`；这些字段直接驱动报告头部的 TL;DR 卡片与 MTTD/MTTM/MTTR 时序表。
   - 结构化的根治项请优先用 `--remediation-item "desc=...;owner=@team-x;due=2026-05-15;url=https://...;status=planned"` 形式，无 Owner 的根治项会触发 `REMEDIATION_NO_OWNER` 警告。
10. 如结论后出现新信息，使用 `reopen --reason ...` 进入新 revision，不要直接补证据。
11. 最终报告优先由 `report --audience technical|business|review|postmortem` 生成；`postmortem` 用于标准十段式事故复盘文档（Executive Summary / Impact / Detection / Response / Recovery / Root Cause / Action Items / Lessons Learned / References / Timeline）。
12. 报告后必须确认是否保留本次最终查询策略；若用户未打断，Agent 可根据复用价值直接 `strategy keep` 或 `strategy discard`，并写明理由。未生成 report 时，`strategy keep/discard` 会被拒绝。
13. 排查过程中沉淀的"小颗粒、跨问题、可复用"事实/规则（≤300 字），必须用 `compass kb learn --statement ... --tag ...` 写进通用知识库，下次自动召回。长文档/系统拓扑请放 `knowledge/` 目录。

最小命令链：

```bash
python3 -m compass_cli start "<用户原始问题>"
python3 -m compass_cli confirm
python3 -m compass_cli next
python3 -m compass_cli scene fact --category entrypoint --name "<入口名>" --value "<接口/页面/动作>" --source "<证据来源>"
python3 -m compass_cli action plan --action-id A1 --track sls --source SLS \
  --objective "<本次动作要验证什么>" \
  --success-criteria "<什么结果算验证成功>" \
  --input "query=<查询条件>" \
  --input "anchor=<订单号/手机号/userId/traceId/站点名等高区分度实体>" \
  --input "time_range=<查询时间窗>" \
  --gate "type=sls" \
  --gate "status=passed" \
  --gate "keyword_source=none|code|sql|schema|table_field|code_sql"
python3 -m compass_cli action env --action-id A1
python3 -m compass_cli action complete --action-id A1 \
  --summary "<证据摘要>" \
  --finding "<关键发现>" \
  --supports H1
# 若本步是代码轨，读取代码也必须走 gateway，再 complete 对应 action
python3 -m compass_cli action plan --action-id C1 --track code --source repo \
  --objective "<本次代码动作要验证什么>" \
  --success-criteria "<什么结果算验证成功>" \
  --input "repo=<代码仓库绝对路径>" \
  --input "target=<页面/接口/类/方法/业务分支>" \
  --gate "type=code" \
  --gate "scope=read-only"
python3 -m compass_cli code search --action-id C1 --query "<日志模板/错误码/接口路径/字段名>"
python3 -m compass_cli code show --action-id C1 --path "<相对路径>" --start <起始行> --end <结束行>
python3 -m compass_cli action complete --action-id C1 --summary "<代码证据摘要>" --finding "<关键代码发现>" --supports H1
python3 -m compass_cli conclude --conclusion "<结论>" --evidence E1 --confidence high \
  --what "<发生了什么>" \
  --where "<服务/接口/类方法/链路位置>" \
  --when "<具体时间或时间窗>" \
  --why-technical "<技术根因>" \
  --why-business "<业务触发条件>" \
  --blast-radius "<量化影响范围>" \
  --how "<传播链路>" \
  --inference-chain "<连续因果推断链>" \
  --tldr "<≤3 句执行摘要，给非技术决策者一眼看完>" \
  --severity sev2 \
  --detected-at "<yyyy-mm-ddTHH:MM:SS+08:00>" \
  --acknowledged-at "<yyyy-mm-ddTHH:MM:SS+08:00>" \
  --mitigated-at "<yyyy-mm-ddTHH:MM:SS+08:00>" \
  --resolved-at "<yyyy-mm-ddTHH:MM:SS+08:00>" \
  --mitigation "<短期止血动作>" \
  --remediation-item "desc=<长期根治动作>;owner=@team-x;due=2026-05-15;url=https://jira/...;status=planned" \
  --pattern-scan "<同类扫描方向>" \
  --unsolved "<本次未解之谜>" \
  --hypothesis H1
python3 -m compass_cli report --audience technical
python3 -m compass_cli report --audience postmortem
python3 -m compass_cli report --audience review
python3 -m compass_cli strategy keep --note "<为什么这次查法值得保留>"
# 或
python3 -m compass_cli strategy discard --note "<为什么不保留>"
# 排查中沉淀的可复用知识 / 通用规则（≤300 字一条）
python3 -m compass_cli kb learn --statement "<一句话事实/规则>" --tag <topic> --tag <id-rule>
# 与故障相关的变更登记
python3 -m compass_cli change record --type deploy --target <服务@版本> \
  --description "<变更内容>" --event-at "yyyy-mm-dd HH:MM" --source <jenkins-id>
# 故障时间线（合并 changes / scene_facts(event_at) / evidence(event_at) / action_history）
python3 -m compass_cli timeline
```

## Hard Rules

- 未 `confirm` 前禁止记录查询动作。
- 排查环境默认是 `prod`；Agent 不得因为安全或方便自行改用 test/uat。
- 罗盘只用于问题查询、定位和证据链分析；不得修改业务代码、生成补丁、提交代码或执行修复。
- 禁止任何写操作：`INSERT / UPDATE / DELETE / DROP / SET / DEL` 等。
- 内部 adapter 优先；JDBC、直连数据库、未登记 HTTP 接口等外部方式必须先让用户确认。
- 目标表或库在内部 CDC/Doris 常规库找不到时，必须先按 `knowledge/data-source-index.md` 查代码表名、Doris Internal Catalog、Doris JDBC Catalog、MySQL profile，不得猜库名或表名。
- prod SQL 必须先 EXPLAIN，风险规则见 `guards/sql-safety.md`。
- SLS 查询必须有高区分度实体锚点：订单号、支付单号、用户ID、手机号、traceId、枪编码、站点名等；禁止用“异常/失败/余额不足/支付/订单”等泛关键词作为主查询。
- SLS 未指定时间窗时 runtime/adapter 默认查最近一周（`-7d`）；如果能从订单创建、支付创建、事件发生时间等证据推断时间窗，应使用推断时间窗并在 action/evidence 中写明依据。
- SLS 默认 logstore 固定为 `all`；不得因配置或便利自行改为单服务 logstore，显式使用非 `all` 前必须用户确认。
- SLS 查询如果在实体锚点之外追加关键词，关键词必须来自代码常量/日志模板或 SQL 表字段/表结构，并通过 `keyword_source` 声明；不得由 Agent 自己猜。
- `action plan` 会由 runtime 强制注入 `context`：playbook 索引、候选知识、首轮候选方向和已召回 playbook；采用通用 playbook 或 `memory/knowledge.yaml` 知识时，必须用 `--playbook` / `--knowledge` 显式记录，让报告和审计能看到“为什么这么查”。
- `next --json` 返回的 `health` 是过程仪表盘，`task` 是下一步任务卡；若出现 `pending_actions`、`open_hypotheses`、`possible_half_root_cause` 等标记，或 task 指向 `sls_plan` / `change_check`，Agent 应优先按任务卡补证据。
- `task` 指向 planned SLS/SQL action 时，先执行 `compass action env --action-id <id>` 生成 adapter runtime 环境并写入 `adapter_env_generated` 事件，再调用真实 adapter；不要手写或省略这些变量。
- `task` 指向 planned code action 时，只能执行 `compass code search/show --action-id <id>`；该 gateway 会校验 `track=code`、`status=planned` 和 repo 边界，并写入 `code_search_executed` / `code_show_executed` 审计事件。
- Agent 排查中禁止用裸 `rg/sed/cat` 代替 `compass code search/show` 读取业务代码；若 CLI gateway 报错，应补 `scene fact`、修正 `action plan` 或请用户确认范围，而不是绕过。
- `knowledge/playbooks/rules.yaml` 是给弱模型使用的机器可读 playbook 索引；新增通用 playbook 时，优先同步一条轻量规则，让 Runtime 能生成 task card。
- 首轮 intake 只能产生 `investigation_hints` 候选排查方向，不能提前创建正式 hypothesis；正式 hypothesis 必须由 scene fact / evidence / change 派生。
- 结论如果只解释“哪里断了”（连不上、不可达、超时、离线、校验失败），但没有变更/timeline/影响面/反证证据，会触发 `HALF_ROOT_CAUSE`；必须继续追最近变更或把根因降级为待验证。
- 执行 `action plan/env/confirm/complete` 后必须阅读 CLI 输出里的 `display`：自然语言说明、命令原文、门禁评估和结构化结果都以 runtime 输出为准，不要在对话里自行编造门禁结论。
- 门禁规则可以通过 `.env` 的 `COMPASS_SQL_GATE_MEDIUM_ROWS` / `COMPASS_SQL_GATE_HIGH_ROWS` / `COMPASS_SLS_GENERIC_KEYWORDS` / `COMPASS_SLS_KEYWORD_SOURCES` 调整；`COMPASS_NON_PROD_RELAX_GATES=1` 只允许放宽 test/uat 等非生产环境，不能关闭 prod SQL EXPLAIN、SLS anchor 或 keyword_source 要求。
- 所有展示给用户的查询结果必须脱敏，规则见 `guards/data-masking.md`。
- `action plan` 必须满足 track 级必填字段；缺字段时不能自行绕过。
- Agent 使用罗盘排查时必须完整遵循 CLI Runtime 流程；禁止直接查询后再补状态，禁止绕过失败的 CLI 门禁。
- evidence 应尽量填写 `kind / strength / raw-ref`，让证据质量进入报告。
- 进入 `concluded/reported` 后禁止继续追加 action/evidence；要补证据必须使用 `reopen --reason ...` 或重开 session。
- 结论后的策略沉淀确认不得跳过；即使不保留，也要用 `strategy discard` 记录原因。

Track 门禁：

| track | 必填 input | 必填 gate |
|-------|------------|-----------|
| sls | `query`, `time_range`（未指定自动 `-7d`）, `anchor` | `type`, `status`, `keyword_source` |
| sql | `sql`, `env`，prod 必须额外提供 `explain_text` | `type`（`status` / `risk` / `explain` 由 runtime 解析 EXPLAIN 后真实写入，禁止自报） |
| code | `repo`, `target` | `type`, `scope` |
| kb | `query` | `type` |
| manual | 无 | 无 |

prod SQL plan 流程要点：

1. `compass action plan --track sql --input "sql=..." --input "env=prod" --input "explain_text=$(EXPLAIN 原文)"` 后 runtime 调 `tools/sql_gate.assess_sql_explain` 真实评估。
2. 中风险（rows ≥ 10 万）/ 高风险（rows > 100 万 / EXPLAIN 解析失败）会把 action 标记为 `requires_confirmation` 并写入 `state.pending_confirmations`，此时 `action complete` 会被拒绝。
3. 解锁方式：用户审视风险后回执 `compass action confirm --action-id <id> --note "..."`，再执行 `action complete`。

## Progressive References

Read only the reference needed for the current task:

- `references/intake-and-state.md`：首轮模板、最小定位实体、状态结构、证据链格式。
- `references/runtime-protocol.md`：CLI Runtime、action 生命周期、Action Card、每轮最小调用顺序。
- `references/safety-and-capabilities.md`：SQL/Redis/ES/脱敏门禁、adapter 能力、项目和策略系统。
- `knowledge/playbooks/_index.md`：通用排查方法索引，不确定入口、已知页面/BFF、日志过期转数据等场景。
- `knowledge/data-source-index.md`：Doris/CDC/JDBC Catalog/MySQL profile 的查找顺序和表找不到时的 fallback。

For detailed SQL/Redis/ES/data masking rules, read the corresponding files under `guards/` only when that track is used.

## Completion Standard

一次排查只有在以下条件满足时才算完成：

- state 中存在 scene facts、evidence 和结构化 conclusion。
- conclusion 引用的 evidence id 真实存在。
- report 已生成并按用户对象选择 technical、business 或 review 视角。
- 输出中明确区分“已证实结论”和“待验证假设”。
