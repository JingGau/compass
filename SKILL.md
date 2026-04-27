---
name: compass-harness
description: "Use when investigating C端/B端/财务/订单/充电线上问题 with incomplete inputs, multi-turn context, local knowledge, code, logs, data adapters, and evidence-chain root cause analysis."
---

# Compass Harness

Compass 是本地优先的线上问题排查 harness。核心职责不是“让 AI 直接查数”，而是让 Agent 通过 CLI Runtime 把问题结构化、规划动作、执行门禁、沉淀证据、派生假设并输出可追溯结论。

优先级：**CLI/Core 程序约束 > 本 Skill 指令 > 对话习惯**。能由程序校验的规则必须交给 harness，不只靠模型自觉。

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
2. 首轮只做 Problem Intake 和方案确认，禁止调用 adapter。
3. 用户确认后，必须使用 CLI Runtime 维护状态，不得跳过 start/confirm/scene/action/evidence/conclude/report 流程。
4. 先记录 `scene fact`，再通过 `action plan -> action complete` 生成 evidence。
5. 新假设必须引用 scene fact 或 evidence。
6. 结论必须通过 `conclude`，引用已存在 evidence，并填写结构化细节。
7. 如结论后出现新信息，使用 `reopen --reason ...` 进入新 revision，不要直接补证据。
8. 最终报告必须优先由 `report --audience technical|business|review` 生成。
9. 报告后必须主动询问用户是否保留本次最终查询策略；用户确认后用 `strategy keep` 沉淀，用户否认后用 `strategy discard` 记录原因。

最小命令链：

```bash
python3 -m compass_cli start "<用户原始问题>"
python3 -m compass_cli confirm --mode auto
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
python3 -m compass_cli action complete --action-id A1 \
  --summary "<证据摘要>" \
  --finding "<关键发现>" \
  --supports H1
python3 -m compass_cli conclude --conclusion "<结论>" --evidence E1 --confidence high \
  --what "<发生了什么>" \
  --where "<服务/接口/类方法/链路位置>" \
  --when "<具体时间或时间窗>" \
  --why-technical "<技术根因>" \
  --why-business "<业务触发条件>" \
  --blast-radius "<量化影响范围>" \
  --how "<传播链路>" \
  --inference-chain "<连续因果推断链>"
python3 -m compass_cli report --audience technical
python3 -m compass_cli report --audience review
python3 -m compass_cli strategy keep --note "<为什么这次查法值得保留>"
# 或
python3 -m compass_cli strategy discard --note "<为什么不保留>"
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
- SLS 查询如果在实体锚点之外追加关键词，关键词必须来自代码常量/日志模板或 SQL 表字段/表结构，并通过 `keyword_source` 声明；不得由 Agent 自己猜。
- 所有展示给用户的查询结果必须脱敏，规则见 `guards/data-masking.md`。
- `action plan` 必须满足 track 级必填字段；缺字段时不能自行绕过。
- Agent 使用罗盘排查时必须完整遵循 CLI Runtime 流程；禁止直接查询后再补状态，禁止绕过失败的 CLI 门禁。
- evidence 应尽量填写 `kind / strength / raw-ref`，让证据质量进入报告。
- 进入 `concluded` 后禁止继续追加 action/evidence；要补证据必须使用 `reopen --reason ...` 或重开 session。
- 结论后的策略沉淀确认不得跳过；即使不保留，也要用 `strategy discard` 记录原因。

Track 门禁：

| track | 必填 input | 必填 gate |
|-------|------------|-----------|
| sls | `query`, `time_range`, `anchor` | `type`, `status`, `keyword_source` |
| sql | `sql`, `env` | `type`, `explain`, `risk` |
| code | `repo`, `target` | `type`, `scope` |
| kb | `query` | `type` |
| manual | 无 | 无 |

## Progressive References

Read only the reference needed for the current task:

- `references/intake-and-state.md`：首轮模板、最小定位实体、状态结构、证据链格式。
- `references/runtime-protocol.md`：CLI Runtime、action 生命周期、Action Card、每轮最小调用顺序。
- `references/safety-and-capabilities.md`：SQL/Redis/ES/脱敏门禁、adapter 能力、项目和策略系统。
- `knowledge/data-source-index.md`：Doris/CDC/JDBC Catalog/MySQL profile 的查找顺序和表找不到时的 fallback。

For detailed SQL/Redis/ES/data masking rules, read the corresponding files under `guards/` only when that track is used.

## Completion Standard

一次排查只有在以下条件满足时才算完成：

- state 中存在 scene facts、evidence 和结构化 conclusion。
- conclusion 引用的 evidence id 真实存在。
- report 已生成并按用户对象选择 technical、business 或 review 视角。
- 输出中明确区分“已证实结论”和“待验证假设”。
