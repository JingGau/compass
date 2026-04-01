# Redis Adapter（缓存状态查询）

## 能力概述

查询 Redis 缓存状态，适用于排查会话、分布式锁、计数器等实时状态问题。

- **只读操作**：只提供读方法，不暴露写命令
- **安全分级**：内置 READ / WRITE / DANGEROUS 命令分类，防止 AI 误用危险命令
- **SCAN 代替 KEYS**：模糊查 key 使用非阻塞的 SCAN
- **支持 standalone 和 cluster 模式**

## 可用连接

| Profile | 环境 | 描述 | DB |
|---------|------|------|----|
| `finance-test` | test | 测试环境-财务 Redis | db30 |
| `finance-uat` | uat | UAT 环境-财务 Redis | db30 |
| `activity-test` | test | 测试环境-活动 Redis | db10 |
| `activity-uat` | uat | UAT 环境-活动 Redis | db10 |
| `price-test` | test | 测试环境-价格 Redis | db10 |
| `price-uat` | uat | UAT 环境-价格 Redis | db12 |
| `redis2-test` | test | 测试环境-Redis2 | db0 |

> Redis 实际有 db0-db100，可通过 `info("keyspace")` 查看各 db 的 key 数量。
> 默认 profile 为 `finance-test`（db30）。

## 使用方法

```python
from adapters.redis.client import RedisClient

client = RedisClient()
ok = client.health_check()
```

### 方法一览

| 方法 | 用途 | 关键参数 |
|------|------|---------|
| `health_check()` | 验证连通性 | — |
| `get_value(key)` | 按类型自动读取 key 值 | 自动识别 string/hash/list/set/zset |
| `key_info(key)` | 查看 key 的类型和 TTL | — |
| `scan_keys(pattern, count)` | 模糊查找 key（非阻塞） | pattern 支持 `*` 通配符 |
| `info(section)` | 查看 Redis INFO | server/memory/clients/keyspace 等 |
| `hgetall(key)` | 获取 Hash 类型所有字段 | — |

## 典型查询示例

**查用户会话**：
```python
# 先扫描含用户ID的key
result = client.scan_keys("*session*541324*", count=10)
# 再读 key 值
result = client.get_value("session:541324")
```

**查分布式锁**：
```python
result = client.scan_keys("*lock*order*598002873*", count=5)
result = client.key_info("lock:order:598002873")  # 看 TTL
```

**查 keyspace（各 db 的 key 数量）**：
```python
result = client.info("keyspace")
# 返回：{db30: {keys: 5071, expires: 0, avg_ttl: 0}, ...}
```

**查内存使用**：
```python
result = client.info("memory")
```

## 命令安全分级

| 类型 | 示例 | AI 行为 |
|------|------|---------|
| READ | GET / HGETALL / SCAN / TTL | 直接使用 |
| WRITE | SET / DEL / EXPIRE | 不暴露（无对应方法） |
| DANGEROUS | KEYS / FLUSHDB / FLUSHALL | 禁止，SCAN 替代 KEYS |

> `KEYS *` 在大库中会阻塞 Redis，必须用 `scan_keys()` 替代。

## 注意事项

- config.yaml 中默认 profile 为 `finance-test`（db30），跨 profile 查询时指定 `profile_name` 参数
- Hash 类型的 value 用 `hgetall(key)` 或 `get_value(key)`（后者自动判断类型）
- SCAN 不保证返回所有结果，`total_scanned` 字段显示实际扫描到的数量
