# 查询规划

**职责**：把已确认的问题、场景事实和候选知识转成下一步最小证据动作。当前权威流程由 CLI Runtime 决定，本文件只说明 Agent 如何围绕 `next --json.task` 规划和执行。

> 本文件被 `SKILL.md` 引用。若本文件与 CLI 输出冲突，以 CLI 的 `task`、`display`、`health` 和错误信息为准。

---

## 核心原则

1. 首轮确认前只做 intake、澄清和方案说明，禁止调用 adapter、读代码或查数据。
2. 首轮确认只执行 `compass confirm`，不再区分会话级执行分支。
3. 确认后按 `compass next --json` 的 `task.suggested_commands` 持续推进；用户打断、runtime 门禁失败、缺关键实体、外部数据源或 prod 中高风险 SQL 时暂停。
4. 每个真实动作都必须先 `action plan`，再执行对应 gateway/adapter，最后 `action complete` 生成 evidence。
5. 代码读取必须走 `compass code search/show`；SLS/SQL adapter 必须先 `compass action env --action-id <id>`。
6. `action plan` 前必须已有 `scene fact`，否则先补入口、对象、上下游、配置、复现、baseline 或 diff。
7. 每步只验证一个清晰目标，避免一次 plan 同时覆盖日志、代码、SQL。
8. 不要手写门禁结论；读取 CLI `display.gate`，并把关键发现写进 `action complete`。

---

## 标准循环

```bash
python3 -m compass_cli next --json
python3 -m compass_cli scene fact ...
python3 -m compass_cli action plan ...
# 按 track 执行：
#   sls/sql -> python3 -m compass_cli action env --action-id A1
#   code    -> python3 -m compass_cli code search/show --action-id C1 ...
python3 -m compass_cli action complete --action-id <id> --summary "..." --finding "..."
```

存在 planned action 时，必须优先完成、确认或修正该 action，不要跳到结论。

---

## Track 选择

| 场景 | 优先 track | 规划要点 |
|------|------------|----------|
| 用户只有截图、报错文案、关键字 | `sls` | 默认 logstore 为 `all`；时间窗缺失时 `-7d`；先用页面/关键字找当时调用情况 |
| 已知页面、BFF、接口路径 | `sls` + `code` | 先定位调用链，再用代码找日志模板、接口、业务分支 |
| 日志超过 5 天且代码能定位表 | `code` + `sql` | 代码找主题表、内部库表或 JDBC 直连表，再规划 SQL |
| 只需记录用户补充事实 | `manual` | 这是人工补充信息 track，不是会话执行分支 |
| 需要复用经验或业务规则 | `kb` | 查询通用知识，采用时在 action 加 `--knowledge` |

---

## 门禁摘要

- prod SQL：`action plan --track sql` 必须带 `input.explain_text`，由 runtime 调 `tools.sql_gate.assess_sql_explain` 真评估；中/高风险进入 `requires_confirmation`。
- SLS：必须有高区分度 `anchor`；额外关键词必须声明 `keyword_source=code/sql/schema/table_field/code_sql/none`。
- SLS 默认 logstore 是 `all`；需要改非 `all` 前必须用户确认。
- 代码：必须 planned `track=code`，`gate.type=code`，`gate.scope=read-only`，路径限制在 `input.repo` 内。
- 外部库、JDBC、未登记 HTTP 或高风险数据源必须先停下来请用户确认。

---

## 输出要求

执行前后不要自由发挥成长篇过程。优先复述 CLI `display`：

```text
准备执行：...
命令原文：
...
门禁评估：...
执行结论：...
```

`action complete` 的 summary/finding 要写成可引用证据：

- 查到了什么，没查到什么。
- 关键 trace/tlog/interface/table/class/field/change 时间。
- 下一步线索：去日志、代码、SQL、配置、变更或结束。

---

## 质量规则

- 连续两步无新增证据时，换 track 或请用户补信息。
- 只定位到“连不上、超时、校验失败、离线”等直接断点时，继续追最近变更、配置、发布、网关、影响面和反证；否则结论会被视为半根因。
- 新 hypothesis 必须引用 scene fact、evidence 或 change。
- 结论必须引用真实 evidence，并用 report 输出技术/业务/review/postmortem 视角。
- 报告后用 `strategy keep` 或 `strategy discard` 记录是否沉淀最终查询策略。
