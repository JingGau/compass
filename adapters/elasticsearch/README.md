# Elasticsearch Adapter

## 能力概述

查询 Elasticsearch，自动检测版本并路由到对应实现：

| ES 版本 | 实现方式 | Auth 参数 |
|---------|---------|----------|
| 6.x | 原生 urllib HTTP（不依赖 SDK） | Basic Auth Header |
| 7.x | elasticsearch-py SDK | `http_auth` |
| 8.x | elasticsearch-py SDK | `basic_auth` |

**版本检测**：Client 初始化时自动通过 HTTP 探测 `GET /` 返回的 `version.number`，无需手动配置版本。

当前连接的 ES 版本：**6.7.0**（测试环境财务 ES）

## 使用方法

```python
from adapters.elasticsearch.client import ESClient

client = ESClient()          # 使用 config.yaml 中的 default_profile
ok = client.health_check()   # 返回 bool
```

### 方法一览

| 方法 | 用途 | 关键参数 |
|------|------|---------|
| `health_check()` | 验证连通性 | — |
| `list_indices(pattern)` | 列出索引 | `pattern="*"` 支持通配符 |
| `search(index, query, size, from_)` | ES DSL 查询 | query 为 ES Query DSL dict |
| `search_keyword(index, keyword, fields, size)` | 关键字全文搜索 | fields=None 表示所有字段 |
| `aggregate(index, query, aggs, size)` | 聚合统计 | aggs 为 ES Aggregations DSL |
| `get_mapping(index)` | 查看字段结构 | — |

### 调用示例

**关键字搜索**（最常用）：
```python
result = client.search_keyword(
    index="finance_d_t_user_flow_v2",
    keyword="541324",          # user_id 或订单号
    size=20
)
```

**精确 DSL 查询**：
```python
result = client.search(
    index="v_third_flow_order_history",
    query={"term": {"user_id": 541324}},
    size=10
)
```

**聚合统计**（查某用户的交易金额分布）：
```python
result = client.aggregate(
    index="finance_d_t_user_flow_v2",
    query={"term": {"user_id": 541324}},
    aggs={"total": {"sum": {"field": "amount"}}},
    size=0
)
```

## 返回格式

所有方法统一返回：
```python
{"success": True,  "data": {...}, "error": None}
{"success": False, "data": None, "error": "错误说明"}
```

`search` 和 `search_keyword` 的 `data` 结构：
```python
{
    "total": 138890,     # 总命中数
    "hits": [
        {"_id": "xxx", "_source": {...}}
    ]
}
```

## 可用索引（测试环境，主要业务相关）

| 索引名 | 描述 | 文档数 |
|--------|------|--------|
| `finance_d_t_user_flow_v2` | 用户资金流水 | 138,890 |
| `v_third_flow_order_history` | 第三方流水订单历史 | 33,959 |
| `finance_d_t_clearing_wallet_trade_flow` | 清分钱包交易流水 | 1,218 |

> 完整索引列表通过 `list_indices()` 获取。

## 注意事项

- ES 6.x 不需要 `_type`，底层已自动处理
- 默认单次最多返回 20 条，大结果集用 `size` 参数控制（ES 6.x 最大 10000）
- 连接是懒加载的，第一次调用时建立连接并缓存版本号
- 新增其他 ES 集群：在 `config.yaml` 中添加新 profile，版本自动探测
