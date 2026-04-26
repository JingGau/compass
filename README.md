# Compass Harness

Compass Harness 是一个本地优先的线上问题排查底座，用来给 Codex、Claude Code、OpenClaw、Hermes 等 Agent 提供稳定的排查入口。

它不是公共 MCP 服务，也不是独立替代 Agent 的大模型应用。它的定位是：

```text
Agent -> Skill -> CLI -> Core -> Adapter -> Data Source
```

## 当前架构

```text
compass-harness/
  SKILL.md              # 给 Agent 的总排查规则
  compass_cli/          # CLI 入口，所有 Agent 都能通过命令行调用
  compass_core/         # intake / kb / state / report 等核心能力
  adapters/             # mysql / redis / sls / es / platform 数据源适配
  guards/               # SQL / Redis / ES / 脱敏 / 查询限制
  knowledge/            # 本地 Markdown 知识库
  memory/               # 本地排查状态、策略、用户决策
  projects/             # 项目上下文
  prompts/              # 场景分类、实体提取、查询规划、结果分析
  tools/                # 证据图、状态机、setup check 等底层工具
```

## CLI Quick Start

在项目根目录执行：

```bash
python3 -m compass_cli setup-check --json
python3 -m compass_cli intake "用户支付成功但订单没有推进，订单号 123456，今天上午" --json
python3 -m compass_cli kb search "清分单 入金通知" --json
python3 -m compass_cli state show --json
python3 -m compass_cli report --format markdown
```

## Controlled Runtime Flow

线上排查应优先使用受控会话命令，让 CLI 负责状态机和证据门禁：

```bash
python3 -m compass_cli start "用户礼品卡不展示，手机号 15921195068，今天下午" --json
python3 -m compass_cli confirm --mode auto --json
python3 -m compass_cli next --json
python3 -m compass_cli scene fact \
  --category entrypoint \
  --name app_payment_ways \
  --value "/app/gun/payment-ways-v2" \
  --source "SLS trace" \
  --json
python3 -m compass_cli action plan \
  --action-id A1 \
  --track sls \
  --source SLS \
  --objective "确认财务是否返回礼品卡" \
  --success-criteria "拿到 payment-ways-v2 trace 中财务返回和最终响应差异" \
  --input "query=15921195068 AND payment-ways-v2" \
  --input "time_range=2026-04-25 16:40~17:10" \
  --input "anchor=15921195068" \
  --gate "type=sls" \
  --gate "status=passed" \
  --gate "keyword_source=code" \
  --json
python3 -m compass_cli action complete \
  --action-id A1 \
  --summary "财务返回礼品卡，guan-zhong 最终响应无礼品卡" \
  --elapsed-ms 1200 \
  --finding "finance returned subPayWay=3 amount=2319.01" \
  --finding "payment-ways-v2 response removed gift card" \
  --lead trace_ids=trace-1 \
  --lead interfaces=/app/gun/payment-ways-v2 \
  --supports H2 \
  --json
python3 -m compass_cli scene fact \
  --category variant \
  --name detail_vs_payment_ways \
  --value "detail has tradeModes, payment-ways-v2 missing tradeModes" \
  --source "SLS/code" \
  --evidence E1 \
  --json
python3 -m compass_cli hypothesis add \
  --id H4 \
  --statement "入口链路上下文不一致导致礼品卡被误过滤" \
  --source-fact detail_vs_payment_ways \
  --source-evidence E1 \
  --json
python3 -m compass_cli conclude \
  --conclusion "礼品卡在 guan-zhong payment-ways-v2 链路被过滤" \
  --evidence E1 \
  --confidence high \
  --what "用户切换支付方式后礼品卡不展示" \
  --where "guan-zhong /app/gun/payment-ways-v2" \
  --when "2026-04-25 16:51 前后" \
  --why-technical "payment-ways-v2 链路未填充 tradeModes，互联站过滤逻辑误过滤礼品卡" \
  --why-business "用户在国网互联站 App 端切换支付方式" \
  --blast-radius "已知影响该用户在该站 App 切换支付方式场景" \
  --how "App 切换支付方式 -> guan-zhong 查询站点基础信息 -> tradeModes 为空 -> 过滤礼品卡" \
  --inference-chain "财务返回礼品卡 -> guan-zhong 最终响应无礼品卡 -> 代码过滤点依赖 tradeModes -> 定位为 guan-zhong 过滤" \
  --json
python3 -m compass_cli report --audience technical
python3 -m compass_cli report --audience business
python3 -m compass_cli report --audience review
```

门禁规则：

- 默认使用线上环境 `prod` 排查；只有用户明确指定 test/uat/测试/预发时才切换环境。
- Agent 使用罗盘排查时必须完整遵循 CLI Runtime 流程，不得直接查询后再补状态。
- 罗盘只用于问题查询、定位和证据链分析；不会修改业务代码、生成补丁、提交代码或执行修复。
- `start` 之后默认处于 `awaiting_confirmation`，未确认前禁止记录查询动作。
- `scene fact` 用来先展开入口、对象、上下游、配置、差异等事实；没有场景事实时禁止 `conclude`。
- `hypothesis add` 必须引用至少一个已存在的 scene fact 或 evidence，用来从事实和证据派生新假设，避免被首轮初始假设锁死。
- 推荐使用 `action plan -> action complete`：先写清楚目标、输入、成功标准和门禁，再把执行结果完成为 evidence。
- SLS 查询必须有高区分度实体锚点 `anchor`，例如订单号、支付单号、手机号、userId、traceId、枪编码、站点名；禁止用“异常/失败/余额不足/支付/订单”等泛词作为主查询。
- SLS 查询在 `anchor` 外追加关键词时，必须通过 `keyword_source` 声明来源，且来源只能是代码常量/日志模板或 SQL 表字段/表结构；不得使用 Agent 自己猜出的场景词。
- `action record` 保留为兼容入口，会直接生成 evidence，写入 action history，并把 trace/interface/method/table 等线索写入 evidence graph；`action-id` 必须唯一，避免同一编号承载两次不同查询。
- `evidence add` 会补充人工证据并进入 action history，但只能在未结论阶段使用。
- evidence 支持 `kind / strength / raw-ref`，用于区分用户口述、日志、SQL、代码、KB 和推断类证据的质量。
- `concluded` 阶段禁止继续追加 action 或 evidence；如有新信息，使用 `reopen --reason ...` 归档旧结论并进入新 revision。
- `conclude` 必须引用已存在的 evidence id，并填写高信息量的 What/Where/When/Why/Blast Radius/How/推断链，否则直接失败。
- `report` 由程序按 `technical`、`business` 或 `review` 视角生成报告，并对展示内容脱敏；`review` 适合按“时间、角色、位置、动作、结果”输出更容易同步的排查结果。

Track 门禁：

| track | 必填 input | 必填 gate |
|-------|------------|-----------|
| sls | `query`, `time_range`, `anchor` | `type`, `status`, `keyword_source` |
| sql | `sql`, `env` | `type`, `explain`, `risk` |
| code | `repo`, `target` | `type`, `scope` |
| kb | `query` | `type` |
| manual | 无 | 无 |

Evidence 质量字段：

| 字段 | 可选值 | 说明 |
|------|--------|------|
| kind | `manual`, `user`, `log`, `sql`, `code`, `kb`, `inference` | 证据类型 |
| strength | `weak`, `medium`, `strong` | 证据强度 |
| raw-ref | 任意字符串 | traceId、SQL 文件、代码位置、知识库路径等原始引用 |

## Obsidian 接入方式

第一版直接读取 Obsidian vault 的 Markdown 文件目录，不需要插件，也不需要同步数据库。

方式一：命令行指定 vault 路径。

```bash
python3 -m compass_cli kb search "入金通知" --root "/Users/you/Obsidian/工作笔记" --json
```

方式二：通过环境变量设置默认 vault。

```bash
export COMPASS_OBSIDIAN_ROOT="/Users/you/Obsidian/工作笔记"
python3 -m compass_cli kb search "清分单" --json
```

这和指定代码库路径类似，只是搜索对象从代码文件变成 Markdown 笔记。

## CLI 和 MCP 的关系

CLI 是第一优先级，因为几乎所有 Coding Agent 都能运行本地命令。

MCP 是后续增强入口，适合支持 MCP 的 Agent。未来结构应保持：

```text
compass_cli -> compass_core
compass_mcp -> compass_core
```

也就是说，CLI 和 MCP 是并列入口，底层复用同一套 Core 和 Adapter。

## 当前已实现的最小能力

- `setup-check`：检查本地配置和 Adapter 凭证缺失情况
- `intake`：把自然语言问题结构化为场景、实体、缺失项、初始假设
- `start / confirm / next`：创建受控排查会话，并由 CLI 管理状态推进
- `action plan / complete`：先规划动作，再完成动作并生成 evidence
- `action record`：兼容式事后登记，把已执行动作登记为证据，并沉淀 trace/interface/method/table 等线索
- `evidence add`：补充人工证据
- `reopen`：重开 concluded 会话，归档旧结论并进入新 revision
- `scene fact`：沉淀入口、对象、上下游、配置、差异等场景事实
- `hypothesis add`：从 scene fact 或 evidence 派生待验证假设
- `conclude`：输出必须引用 evidence、scene fact 和结构化细节的结论
- `kb search`：搜索本地 Markdown 知识库和 Obsidian vault
- `state show`：读取或初始化本地排查状态
- `report`：从状态文件生成 Markdown 或 JSON 报告，包含完整排查流程并对敏感展示值脱敏

## 验证

```bash
python3 -m pytest tests/test_compass_cli.py
```
