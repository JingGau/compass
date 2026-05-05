# 通用排查 Playbook 规范

## 定位

`knowledge/playbooks/` 存放通用排查方法，回答“在某类信息条件下，通常怎么推进证据链”。

Playbook 不替代 Runtime：

- Runtime 负责流程状态、门禁、安全拦截。
- Playbook 只帮助 Agent / 人类选择日志、代码、数据库、知识库等侦查路径。
- 任何真实查询仍必须先 `action plan`，查询后 `action complete`。

## 推荐结构

每个 playbook 使用 Markdown，建议包含：

```markdown
# 标题

## 适用场景

## 排查路径

## 门禁提醒

## 证据落点
```

## 写作规则

- 写通用方法，不写单次事故细节。
- 不写敏感数据、真实手机号、真实 token、真实账号。
- 不鼓励裸查 adapter；必须显式提醒 action plan / action complete。
- 不把“查日志、查代码、查数据库”的选择写成程序强制顺序。
- 涉及数据源 fallback 时，链接到 `knowledge/data-source-index.md`。

## 与 memory 的区别

- `knowledge/playbooks/`：团队共享、可提交到 Git 的方法论。
- `memory/knowledge.yaml`：一句话小颗粒事实/规则，适合自动召回。
- `memory/strategies.yaml`：某次问题跑通后，用户确认保留的历史策略。
