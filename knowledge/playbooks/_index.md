# 通用排查 Playbooks

这些 playbook 是可共享的通用排查方法，用来帮助 Agent / 人类选择侦查路径。

它们不是 Runtime 状态机规则：程序仍只负责 `start -> confirm -> scene fact -> action plan -> action complete -> conclude -> report` 的流程门禁；日志、代码、数据库的选择由 Agent / 人类根据问题判断。

## 使用边界

- Agent 自动模式下，所有真实查询前必须先 `action plan`，查询后必须 `action complete`。
- 每次制定 `action plan` 前都应把本目录作为策略参考上下文；新增 playbook 默认进入后续决策上下文。
- 如果采用某条 playbook，应在 action objective/source/success-criteria 或后续 evidence finding 中体现。
- Playbook 只能指导“下一步查什么”，不能绕过 scene fact、门禁、证据引用和 report。
- 线上 SLS / Doris 查询仍必须遵守实体锚点、keyword_source、EXPLAIN、风险确认等门禁。
- 如果 playbook 与当前证据冲突，以当前证据和 Runtime 门禁为准。

## Playbook 列表

| 场景 | 文件 | 适用时机 |
|------|------|----------|
| 不确定用户场景或入口接口 | [unknown-entrypoint-log-to-trace.md](unknown-entrypoint-log-to-trace.md) | 只有关键词、现象、用户描述，不知道具体接口或服务 |
| 能由页面 / BFF / 应用确定接口 | [known-page-or-bff-to-link.md](known-page-or-bff-to-link.md) | 已知道页面、BFF 应用、接口路径或后端入口 |
| 日志超过保留期，需要转代码和数据 | [log-expired-code-to-data.md](log-expired-code-to-data.md) | SLS 日志不可查或超过约 5 天，但可从代码和数据补证 |

## 与其他知识的关系

- 业务事实、ID 规则、字段含义：优先放 `memory/knowledge.yaml` 的短句，或 `knowledge/business/` 长文档。
- 页面、接口、服务映射：放 `knowledge/b-side/`、`knowledge/c-side/`、`knowledge/systems.md`。
- 表、catalog、数据源查找：放 `knowledge/data-source-index.md`、`knowledge/doris-jdbc-catalogs.md`、`knowledge/tables/`。
- 已成功的问题排查路径：由 report 后的 `strategy keep/discard` 进入 `memory/strategies.yaml`。
