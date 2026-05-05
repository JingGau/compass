# SLS Adapter（阿里云日志服务）

## 能力概述

通过 aliyun-log-python-sdk 查询阿里云 SLS，支持全文搜索、字段过滤、SQL 分析、错误统计。

- **默认环境**：prod
- **多环境**：prod / test / uat 三套 SLS Project 独立
- **日志库**：`all`（聚合所有服务）或指定单个服务的 logstore

## 使用方法

Agent 排查时不要裸调本 adapter；先通过 `compass action plan` 规划 SLS action，再用 `compass action env --action-id <id>` 生成 `COMPASS_ADAPTER_MODE=runtime` 等 runtime 变量后执行查询。人工本地调试不设置这些变量。

```python
from adapters.sls.client import SLSClient

client = SLSClient()
ok = client.health_check()
```

### 方法一览

| 方法 | 用途 | 关键参数 |
|------|------|---------|
| `health_check()` | 验证连通性 | — |
| `query_logs(query, env, from_time, to_time, limit, offset)` | 执行 SLS 查询 | query 支持全文和 SQL 分析 |
| `search_keyword(keyword, env, from_time, limit, container)` | 关键字搜索（query_logs 简化版） | container 可限定服务容器 |
| `analyze_errors(env, from_time, top_n, container)` | 高频错误聚合统计 | 返回 Top N 错误 |
| `list_logstores(env)` | 列出所有 logstore | — |

## 查询语法速查

### 全文搜索
```
orderId:598002873          # 按订单号搜索
138xxxxxxxx                # 按手机号搜索
trade_seq:320101000...     # 按流水号搜索
```

### 字段过滤
```
level:ERROR                          # 错误日志
__tag__:_container_name_:finance-server   # 指定容器
level:ERROR AND service:finance      # 组合条件
```

### 常用服务容器名

| 服务 | container name | 对应 logstore |
|------|---------------|--------------|
| 财务服务 | `finance-server` | `finance-server` |
| 订单服务 | `order-server` | `order-server` |
| 充电服务 | `charge-server` | `charge-server` |
| 结算服务 | `clearing-server` | `clearing-server` |
| 基础服务 | `base-server` | `base-server` |
| 支付服务 | `payment-server` | `payment-server` |

### SQL 分析
```
* | SELECT COUNT(*) GROUP BY level
level:ERROR | SELECT message, COUNT(*) AS cnt GROUP BY message ORDER BY cnt DESC LIMIT 10
```

## 时间格式

未指定 `from_time` 时默认最近一周（`-7d`）。如果业务证据能推断事件时间，例如订单创建或支付创建时间，应传入推断出的时间窗并在 action/evidence 记录依据。

| 格式 | 示例 | 说明 |
|------|------|------|
| 相对时间 | `-1h`, `-30m`, `-7d` | 最近 N 时间 |
| 固定锚点 | `now` | 当前时间 |
| ISO 格式 | `2026-03-28 16:00:00` | 精确时间点 |
| Unix 时间戳 | `1743158400` | 秒级 |

## 典型查询示例

**按订单号查日志（最常用）**：
```python
result = client.search_keyword(
    keyword="598002873",
    container="finance-server",
    from_time="-7d"
)
```

**查某服务最近的错误**：
```python
result = client.analyze_errors(
    container="finance-server",
    from_time="-7d",
    top_n=10
)
```

**跨服务联合查询（用 all logstore）**：
```python
result = client.query_logs(
    query="320101000... AND (ERROR OR Exception)",
    from_time="-7d",
    limit=50
)
```

## 注意事项

- 查询范围最大 7 天（guards/query-limits.yaml 限制），超出会截断
- 单次最多返回 500 条
- 默认查 prod 环境，测试环境排查传 `env="test"`
- 默认 logstore 固定为 `all`；显式指定其他 logstore 前必须用户确认
- `analyze_errors` 返回的是聚合统计，不是原始日志
