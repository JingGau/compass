# Platform Adapter（Doris 数据查询）

## 能力概述

通过平台数据查询服务查询 Apache Doris，支持 SQL 查询、条数预估、异步导出。

- **协议**：HTTP POST，JSON-RPC 2.0，响应为 SSE 格式
- **底层存储**：Apache Doris 分析数据库
- **数据范围**：生产数据（CDC 实时同步），覆盖订单、财务、基础数据

## 协议说明

响应格式为 SSE，业务数据嵌套在内层 JSON：
```
HTTP Response Body:
event: message
data: {"result": {"content": [{"text": "{\"result\":{\"data\":[[...]],\"columns\":[...]}}"}]}}
```
Client 已封装二次解析，调用方直接拿结构化结果。

## 使用方法

```python
from adapters.platform.client import PlatformClient

client = PlatformClient()
health = client.health_check()
# {"adapter":"platform","status":"ok|error|disabled","latency_ms":12,"environment":"prod","error":None}
```

### 方法一览

| 方法 | 用途 | 返回 data 结构 |
|------|------|--------------|
| `health_check()` | 验证连通性 | `{adapter,status,latency_ms,environment,error}` |
| `query_sql(sql)` | 执行 SELECT SQL | `{columns, rows, result}` |
| `count(sql)` | 预估查询总条数（先 count 再决定是否查） | int |
| `export_async(sql)` | 创建异步导出任务（大结果集） | `{task_id}` |
| `get_export_status(task_id)` | 查询导出进度/下载链接 | `{status, url}` |
| `list_databases()` | 列出所有数据库 | — |
| `list_tables(database)` | 列出指定数据库的表 | — |
| `describe_table(table)` | 查看表结构（支持 `db.table` 格式） | — |

## ⚠️ 分区表强制要求

以下表为 Doris 分区表，查询**必须**包含 `dt_month = 'YYYY-MM-01'` 过滤，否则报错：

| 表名 | dt_month 含义 |
|------|--------------|
| `ods_order_cdc.ods_order_s_t_charging_record_history` | 充电记录月份 |
| `ods_order_cdc.ods_order_d_t_pay_detail` | 支付明细月份 |
| `ods_finance_cdc.ods_finance_d_t_user_flow` | 资金流水月份 |

## 可用数据库

| 数据库 | 内容 |
|--------|------|
| `ods_base_cdc` | 用户、电站、充电桩等基础信息 |
| `ods_order_cdc` | 充电订单、支付明细、结算 |
| `ods_finance_cdc` | 钱包、资金流水、清分账单 |
| `ods_charge_cdc` | 充电过程、时序数据 |
| `dwd` | 数据仓库明细层（21 张宽表，适合统计） |
| `ads` / `dws` / `dim` | 聚合层、维度表 |

## 核心表速查

**用户表**（无分区）：
```sql
SELECT user_id, user_phone, user_nick_name, vehicle_org_id
FROM ods_base_cdc.ods_base_s_t_charging_user
WHERE user_phone = '138xxxxxxxx'
```

**充电记录**（⚠️ 分区表）：
```sql
SELECT record_id, trade_seq, trade_status, start_time, paied_amount
FROM ods_order_cdc.ods_order_s_t_charging_record_history
WHERE dt_month = '2026-03-01' AND uid = {user_id}
ORDER BY start_time DESC LIMIT 10
```

**资金流水**（⚠️ 分区表）：
```sql
SELECT flow_id, trade_type, amount, balance, create_time
FROM ods_finance_cdc.ods_finance_d_t_user_flow
WHERE dt_month = '2026-03-01' AND user_id = {user_id}
ORDER BY create_time DESC LIMIT 10
```

**钱包**（无分区）：
```sql
SELECT user_id, balance, freeze_amount, update_time
FROM ods_finance_cdc.ods_finance_d_t_user_wallet
WHERE user_id = {user_id}
```

## 大结果集策略

```
先 count() 预估行数
  ≤ 100 条  → 直接 query_sql 查询
  100~1000  → query_sql 查前 100 条，告知总数
  > 1000 条 → 使用 export_async 导出到 OSS，再 get_export_status 获取下载链接
```

## 注意事项

- 只支持 SELECT 语句（写操作由 guards 层拦截）
- 单次默认超时 30s，导出超时 120s
- 日期字符串使用单引号：`dt_month = '2026-03-01'`（不是双引号）
