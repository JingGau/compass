# Compass Architecture

Compass 是状态机驱动的线上问题排查 harness。Agent 负责判断和表达，Runtime 负责流程、门禁、证据链和可观测事件。

## Responsibility Split

| 层 | 负责 | 不负责 |
|----|------|--------|
| Agent | 理解用户问题、选择侦查路径、解释证据、询问必要确认 | 绕过 CLI、裸查 adapter、伪造门禁结论 |
| CLI Runtime | phase、allowed commands、action lifecycle、gate、events、report | 判断业务根因、替用户做高风险确认 |
| Adapter | 只读查询线上日志或数据源，校验 runtime action 上下文 | 保存流程状态、决定下一步 |
| Knowledge | 提供通用 playbook 和业务事实上下文 | 替代证据或结论 |

## Flow

```text
new
  -> start
  -> awaiting_confirmation
  -> confirm
  -> action_ready
  -> scene fact
  -> action plan
  -> action env / code search / code show
  -> action complete
  -> hypothesis add
  -> conclude
  -> report
  -> strategy keep/discard
```

首轮 `confirm` 之后没有会话级模式分支。Agent 按 `next --json.task` 持续推进，直到用户打断或 Runtime 返回必须暂停的门禁。

## Hard Gates

- 未 `confirm`：不能写入 action/evidence。
- 缺少 `scene fact`：不能 `action plan`。
- SLS action：必须有 `query`、`time_range`、高区分度 `anchor` 和 `keyword_source`；未给时间窗时默认 `-7d`；默认 logstore 是 `all`，非 `all` 必须用户确认。
- SQL action：prod 必须提供 EXPLAIN；中高风险必须 `action confirm`。
- Code action：必须先规划 `track=code`，再用 `code search/show --action-id`，不能裸读业务代码作为罗盘证据。
- `concluded/reported` 后补证据必须先 `reopen`。

## Runtime Guard

Agent 调 adapter 的唯一推荐入口：

```bash
scripts/compass-agent-runtime.sh <agent-command>
python3 -m compass_cli action env --action-id <id>
```

`action env` 生成：

```text
COMPASS_ADAPTER_MODE=runtime
COMPASS_RUNTIME_GUARD=1
COMPASS_RUNTIME_STATE_FILE=<state>
COMPASS_RUNTIME_ACTION_ID=<id>
```

Adapter 会校验 action 已确认、已规划、track 匹配且 status 为 `planned`。人工临时直连 adapter 不设置这些变量，不进入罗盘证据链。

仅 adapter guard 保留旧环境兼容：`COMPASS_AGENT_AUTO=1` 会被视为 runtime 调用，防止旧 runner 绕过门禁。流程层、Skill 文档和 CLI 不保留旧模式参数。

## Observability

- `state.events` 只记录轻量审计事件，不存大查询结果。
- `next --json.health` 暴露 pending action、open hypothesis、possible half root cause 等过程健康信号。
- `action plan/env/confirm/complete` 和 `code search/show` 都输出 `display`：自然语言说明、命令原文、门禁评估和结构化结果。
- `timeline` 合并 changes、scene facts、evidence 和 action history，最终报告按受众渲染 technical/business/review/postmortem。
