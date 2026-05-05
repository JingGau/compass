# Safety And Capabilities Reference

## Safety Gates

| 查询类型 | 必读文件 |
|---------|---------|
| SQL（prod） | `guards/sql-safety.md` |
| SQL（test/uat） | `guards/sql-safety.md` |
| Redis | `guards/redis-safety.md` |
| ES | `guards/es-safety.md` |
| 所有结果展示 | `guards/data-masking.md` |
| 上下文占用 | `guards/context-limits.yaml` |
| 临时文件 | `guards/temp-files.yaml` |

prod SQL 摘要：

- 必须先 EXPLAIN。
- 低风险可自动执行。
- 中风险等待确认。
- 高风险必须明确确认。
- 分区表缺少 `dt_month` 时自动补充，不打断用户。

SLS 摘要：

- 查询必须有 `input.anchor`，且 anchor 必须是高区分度实体：订单号、支付单号、用户ID、手机号、traceId、枪编码、站点名等。
- 未指定时间窗时默认 `-7d`；若能从订单创建、支付创建、事件发生时间等证据推断时间窗，优先用推断时间窗并记录依据。
- 默认 logstore 固定为 `all`；使用非 `all` logstore 必须用户确认。
- `query` 必须原样包含 `anchor`，禁止先用泛词大范围扫日志。
- `anchor` 外的额外关键词必须来自代码常量/日志模板或 SQL 字段/表结构，并用 `gate.keyword_source` 声明为 `code/sql/schema/table_field/code_sql`。
- 禁止使用 Agent 自己猜测的泛关键词：异常、失败、余额不足、支付、订单、充值、退款、回调等。

## Tool Priority

1. 内部 Adapter：`adapters/<n>/client.py`
2. Platform Adapter：Doris JDBC，需用户确认
3. 其他外部库 / 直连方式：需用户确认

## Data Source Fallback

当内部 CDC 库、常规 Doris 库或 `SHOW DATABASES` 找不到目标表时，必须按 `knowledge/data-source-index.md` 的顺序处理：

1. 先从代码 Mapper/XML/DAO/实体类确认真实表名和字段名。
2. 再查 Doris Internal Catalog，例如 `ods_finance_cdc`、`ods_order_cdc`。
3. 如果 CDC 未同步或 `SHOW DATABASES` 不可见，读取 `knowledge/doris-jdbc-catalogs.md`，使用 Doris JDBC Catalog 三段式路径 `catalog.database.table`。
4. 如果问题环境是 test/uat，或用户明确允许结构验证，再查 `mysql` adapter profile。
5. 仍找不到时必须向用户说明已查路径和缺口，不得猜 catalog、库名或表名。

切换数据源时，action/evidence 必须记录切换原因，例如“CDC 未同步该 tp 表，改查 `finance_jdbc_catalog.yunkc_finance`”。

外部库确认格式：

```text
当前步骤需要使用外部库：[库名/连接方式]
原因：内部 CDC/JDBC catalog/MySQL profile 不覆盖该数据源（说明原因）
连接信息：[catalog/profile 名]

[确认使用] [换内部方案] [跳过此步]
```

用户选“换内部方案”时，必须尝试用内部 adapter 改写。

## Setup Gate

开始排查前，如 `.env` 不存在、`CODE_ROOT` 未配置、或 `CODE_ROOT` 路径不可用，必须先进入 `prompts/setup.md`，禁止调用 adapter。

配置原则：

- 用户手动准备的核心文件只有 `.env`。
- 最小必填只有 `CODE_ROOT`；只做代码排查时不需要数据源凭证。
- Python 环境自动探测：`COMPASS_PYTHON` → skill `.venv` → `VIRTUAL_ENV` → 当前 Python → PATH 中的 `python3/python`。
- 创建 venv 或安装依赖必须先确认。
- SLS / Platform / MySQL / Redis / ES 凭证按需填写；缺失时只标记对应 adapter 不可用。

## Default Boundaries

| 允许 | 需用户确认 | 禁止 |
|------|-----------|------|
| 读/写本 Skill 目录内文件 | JDBC 等外部库调用 | 修改业务代码、生成补丁、提交代码或执行修复 |
| 通过 `adapters/<n>/client.py` 执行查询 | Platform adapter（Doris JDBC） | 本机 `mysql` / `redis-cli` 直连 |
| | | `curl` 未登记的业务 HTTP 接口；工作区其他未登记 MCP |

## Capability Registry

### Adapters

| Adapter | 用途 | 环境覆盖 | 类型 |
|---------|------|---------|------|
| platform | Doris 分析数据查询 | 仅 prod | 外部（JDBC） |
| sls | SLS 日志查询 | prod / test / uat | 内部 |
| mysql | MySQL/PolarDB 数据库查询 | test / uat | 内部 |
| redis | Redis 缓存状态查询 | test / uat | 内部 |
| elasticsearch | ES 全文检索 | test（仅 test-finance） | 内部 |

凭证通过环境变量注入，`adapters/base.py` 自动读取 `.env`。

### Projects

`projects/` 下每个 `.md` 是已注册项目的代码导航地图，路径基于 `config/code-repos.yaml`，用户在 `.env` 设置 `CODE_ROOT`。

### Strategies

`memory/strategies.yaml` 存储排查经验，多维度评分匹配方案。
