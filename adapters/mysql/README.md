# MySQL Adapter（测试环境数据库）

## 能力概述

直连 MySQL/PolarDB 测试库，适合在测试环境验证数据、查看表结构。

- **仅支持 SELECT / SHOW / DESC**（写操作在 SQL 分类层直接拦截）
- **自动注入 LIMIT**：未指定 LIMIT 的 SELECT 默认最多返回 100 条，防止拉全表
- **表结构查询**：通过 `information_schema` 返回行数估算 + 大小

## 可用数据库

| Profile | 环境 | 数据库 | 描述 |
|---------|------|--------|------|
| `polardb-test` | test | `yunkc_finance` | 测试环境 PolarDB 财务库 |
| `polardb-uat` | uat | `yunkc_finance` | UAT 环境 PolarDB 财务库 |
| `main-test` | test | `yunkc_base` | 测试环境主库 |
| `main-uat` | uat | `yunkc_base` | UAT 环境主库 |

## 使用方法

```python
from adapters.mysql.client import MySQLClient

client = MySQLClient()
ok = client.health_check()
```

### 方法一览

| 方法 | 用途 | 关键参数 |
|------|------|---------|
| `health_check()` | 验证连通性 | — |
| `query_sql(sql, profile_name, limit, offset)` | 执行 SELECT | 自动注入 LIMIT |
| `describe_table(table, database, profile_name)` | 查看表结构 | 支持 `db.table` 格式 |
| `list_tables(database, profile_name)` | 列出所有表 | 含行数估算和注释 |
| `list_profiles()` | 列出所有可用数据库 | — |

## 典型查询示例

**查表结构**：
```python
result = client.describe_table("yunkc_finance.user_wallet")
# 返回：columns列表、rows_approx、size_kb
```

**查数据（自动 LIMIT 100）**：
```python
result = client.query_sql(
    "SELECT * FROM user_wallet WHERE user_id = 541324"
)
# 无需手动加 LIMIT，自动注入
```

**切换数据库**：
```python
result = client.query_sql(
    "SELECT * FROM some_table LIMIT 10",
    profile_name="main-test"
)
```

## 返回格式

```python
{
    "success": True,
    "data": {
        "columns": ["col1", "col2"],
        "rows": [[val1, val2], ...],
        "count": 15,
        "truncated": False,      # True 表示结果被截断
        "sql_executed": "..."    # 实际执行的 SQL（含自动注入的 LIMIT）
    },
    "error": None
}
```

## 注意事项

- 这是**测试环境**数据，与生产数据不一致，生产数据请用 `platform` adapter
- DDL / WRITE 语句直接返回错误，不会执行
- 自动 LIMIT 默认 100 条，需要更多可传 `limit=500`
