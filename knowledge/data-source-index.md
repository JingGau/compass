# 数据源索引与查找顺序

> 目标：当内部库、CDC 表或常规 `SHOW DATABASES` 找不到数据时，Agent 不能猜库名或放弃，应按固定顺序定位真实数据源，并把切换依据记录到 action/evidence。

## 数据源分层

| 层级 | 数据源 | 访问方式 | 适用场景 | 注意事项 |
|------|--------|----------|----------|----------|
| 1 | 代码与项目知识库 | `projects/`、代码仓库、Mapper/XML/实体类 | 确认服务、表名、字段名、日志关键词 | 先确认“代码真实使用什么表/字段”，再查数据 |
| 2 | Doris Internal Catalog | `platform` adapter 查询 Doris CDC/数仓库 | 生产数据、订单/财务/基础/充电 CDC、统计宽表 | `SHOW DATABASES` 可见；分区表要带 `dt_month` |
| 3 | Doris JDBC Catalog | `platform` adapter 三段式 SQL | CDC 未同步但 Doris 已注册 catalog 的业务库直查 | `SHOW DATABASES` 不可见；必须 `catalog.database.table` |
| 4 | MySQL adapter profile | `mysql` adapter | test/uat 验证、查看表结构、非生产问题 | 当前仅 test/uat；不能和 prod 日志混查成同一证据链 |
| 5 | 未登记外部直连 | 用户确认后临时接入 | 内部 adapter/JDBC catalog 都无法覆盖 | 必须说明原因、连接名、只读风险与查询范围 |

## Doris Internal Catalog

这些库通常可通过 `SHOW DATABASES` 看到，适合优先查生产 CDC/数仓数据。

| 数据库 | 内容 | 常见服务 |
|--------|------|----------|
| `ods_base_cdc` | 用户、电站、桩枪、运营商等基础数据 | base/user/station |
| `ods_order_cdc` | 充电订单、支付明细、订单结算 | order/trade-order |
| `ods_finance_cdc` | 钱包、资金流水、清分账单 | finance/clearing |
| `ods_charge_cdc` | 充电过程、实时状态、桩交互 | charge/pile |
| `dwd` | 明细宽表，适合跨域分析 | 数仓 |
| `ads` / `dws` / `dim` | 聚合层、服务层、维表 | 数仓 |

分区表规则见 `guards/sql-safety.md` 和 `adapters/platform/README.md`。常见分区字段是 `dt_month = 'YYYY-MM-01'`。

## Doris JDBC Catalog

JDBC Catalog 是 Doris 穿透业务 MySQL/PolarDB 的方式，适合查 CDC 未同步的数据。它们不会出现在 `SHOW DATABASES` 结果里，必须使用三段式路径。

```sql
SELECT *
FROM finance_jdbc_catalog.yunkc_finance.`clearing_tp_clearing_bill`
WHERE bill_number = '...'
LIMIT 20;
```

已知 catalog 详见 `knowledge/doris-jdbc-catalogs.md`。

| Catalog | 业务库 | 典型场景 |
|---------|--------|----------|
| `finance_jdbc_catalog` | `yunkc_finance` | 三方清分、钱包、提现、结算相关 tp 表 |
| `order_jdbc_catalog` | 待补充 | 订单相关直查 |
| `base_jdbc_catalog` | 待补充 | 基础数据直查 |

## MySQL Adapter Profiles

MySQL adapter 当前用于 test/uat，不用于默认 prod 线上排查。

| Profile | 环境 | 数据库 | 用途 |
|---------|------|--------|------|
| `polardb-test` | test | `yunkc_finance` | 测试环境财务库 |
| `polardb-uat` | uat | `yunkc_finance` | UAT 财务库 |
| `main-test` | test | `yunkc_base` | 测试环境基础主库 |
| `main-uat` | uat | `yunkc_base` | UAT 基础主库 |

## 表找不到时的固定流程

1. **先从代码确认真实表名和字段名**
   - 查 Mapper/XML/DAO/Repository/实体类。
   - 记录服务、类方法、表名、字段名来源。
   - 禁止只凭业务词猜 `table_name`。

2. **查 Doris Internal Catalog**
   - 用 `SHOW DATABASES`、`SHOW TABLES FROM db`、`DESC db.table` 确认。
   - 如果是分区表，SQL 必须带 `dt_month`。
   - 查不到时记录“查过哪些库/表模式，未命中”。

3. **查 Doris JDBC Catalog 索引**
   - 读取 `knowledge/doris-jdbc-catalogs.md`。
   - 根据服务/业务库选择 catalog。
   - 使用三段式路径 `catalog.database.table`。
   - 不要因为 `SHOW DATABASES` 看不到 catalog 就认为不存在。

4. **必要时查 MySQL adapter profile**
   - 仅当问题环境是 test/uat，或用户明确允许用非生产数据做结构验证。
   - 不能把 test/uat 查询结果当作 prod 事实，只能作为结构或逻辑参考。

5. **仍找不到时向用户说明缺口**
   - 说明已查路径：代码、internal catalog、JDBC catalog、profiles。
   - 给出下一步需要的连接或库名。
   - 不得自造库名、catalog 名或表名。

## Action 记录要求

当从一个数据源切换到另一个数据源时，action/evidence 必须写清楚：

| 字段 | 要求 |
|------|------|
| objective | 本次切换要验证什么 |
| input | SQL、catalog/profile、表名、实体锚点 |
| summary | 查到/未查到什么 |
| finding | 数据源选择依据，例如“CDC 未同步该 tp 表，改查 finance_jdbc_catalog” |
| raw-ref | 代码位置、知识库路径、SQL 摘要或 catalog 路径 |

## 外部直连确认模板

```text
当前步骤需要使用外部库：[库名/连接方式]
原因：内部 CDC/JDBC catalog/MySQL profile 均未覆盖，或已确认目标表不在已登记数据源中
依据：[代码表名/配置项/知识库路径/用户提供信息]
连接信息：[catalog/profile/只读连接名]
查询范围：[实体ID + 时间窗 + LIMIT]

[确认使用] [换内部方案] [跳过此步]
```
