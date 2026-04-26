# Runtime Protocol Reference

## CLI Runtime Priority

当本 Skill 目录存在 `compass_cli/` 时，Agent 必须优先通过 CLI Runtime 维护排查会话。

Agent 使用罗盘排查时必须完整遵循 Runtime 流程。禁止直接调用 adapter、直接查日志/SQL/代码后再补状态；CLI 返回失败时，必须修正输入或补证据，不能在对话中绕过。

罗盘是 investigation-only 工具，只查询、定位、沉淀证据和输出结论。禁止在罗盘流程中修改业务代码、生成补丁、提交代码或执行修复；修复工作应在罗盘报告之外另起开发任务。

核心命令：

- `start / confirm / next`
- `scene fact`
- `action plan / action complete`
- `evidence add`
- `hypothesis add`
- `conclude`
- `reopen`
- `report`

`action record` 仅作为兼容式事后登记入口。

## Action Lifecycle

每次实际查询、读代码、拉日志前：

1. `action plan` 写入目标、输入、成功标准和门禁。
2. 执行真实查询或阅读动作。
3. `action complete` 写入摘要、发现、线索，生成 evidence 和 action history。
4. 如产生新场景事实，用 `scene fact --evidence E<n>` 绑定证据。
5. 如产生新假设，用 `hypothesis add --source-fact ... --source-evidence ...`。

存在 planned action 时，`next` 必须优先提示完成或调整计划，不能直接结论。

## Reopen And Revision

`concluded` 后禁止继续补证据。收到新信息时：

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

1. 构造 `InvestigationAction`，写明目的、工具、环境、查询对象、成功标准。
2. 输出 `render_before_card(action)`。
3. 输出 Safety Gate；SQL 使用 `assess_sql_explain` 后再 `render_safety_gate_card`。
4. 若 `gate.requires_confirmation=true`，必须 `build_pending_confirmation` 并暂停。
5. 执行查询 / 读代码 / 拉日志。
6. 构造 `ActionResult`，输出 `render_after_card(action, result)`。
7. 将 `ActionResult.leads` 写入 `EvidenceGraph`。

| 轨道 | 执行前必须展示 | 执行后必须提取 |
|------|----------------|----------------|
| SLS | query、时间范围、anchor、keyword_source、limit、容器/服务 | traceId/tlogId、接口、服务、异常时间、后续代码/DB/链路 |
| SQL | 完整 SQL、环境、EXPLAIN SQL 和风险 | 返回行数、关键字段、相关表、是否指向代码/日志 |
| 代码 | 应用、文件/类/方法、来源线索 | 页面→接口→Controller→Service→Mapper→表、日志关键字、业务分支 |
| Redis/ES | 命令/索引/查询体、范围限制 | key/index、命中摘要、是否指向 SQL/代码/日志 |

## 每轮最小调用顺序

1. `read_state`
2. `sense_flow_deviation`
3. `get_context`
4. 更新/展示 Investigation State
5. 每个动作前：`InvestigationAction -> render_before_card -> Safety Gate`
6. 风险需确认时：`build_pending_confirmation -> write_state -> 暂停`
7. 执行后：`ActionResult -> render_after_card -> EvidenceGraph.add_result_leads`
8. 查询后：归入 `evidence / hypotheses / ruled_out / next_actions`
9. `sense_query_result + mark_checkpoint`
10. 推进前：`assert_step_complete`
11. 必要时：`sense_context_size -> compress`
12. `advance_step`
13. `write_state`

## 强制门禁

- `assert_step_complete.ok=false`：禁止推进。
- `sense_log_track_progress.complete=false`：禁止进入结果分析。
- `sense_context_size.action in {COMPRESS, EMERGENCY_COMPRESS}`：必须先压缩再继续。
- `conclude` 失败时禁止在对话中绕过并直接下结论。
- 默认环境为 `prod`；SQL plan 未显式提供 `env` 时 Runtime 使用 session 环境，默认就是 `prod`。
- SLS 查询必须以高区分度实体作为 `anchor`：订单号、支付单号、用户ID、手机号、traceId、枪编码、站点名等。禁止以“异常/失败/余额不足/支付/订单”等泛词作为主查询。
- SLS 查询若在 `anchor` 外追加关键词，必须声明 `keyword_source=code/sql/schema/table_field/code_sql`，表示关键词来自代码常量/日志模板或 SQL 字段/表结构；不得使用 Agent 自己猜测的业务词。

## Special Entrypoints

| 用户说 | 执行 |
|--------|------|
| 配置 / setup / 初始化 | `prompts/setup.md` |
| 注册项目 | `prompts/project-onboarding.md` |
| 扫描前端整理知识 | `prompts/knowledge-batch-scan.md` |
| 注册页面 | `prompts/knowledge-onboarding.md` |
| 加个 XX 能力 | `adapters/_convention.md` |
| 知识库现状 | 汇总 projects/ + adapter 状态 + 策略数量 |
