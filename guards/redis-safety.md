# Redis 安全规则

AI 在调用 Redis adapter 前，必须遵守以下规则。

## 命令分级

| 级别 | 命令 | 策略 |
|------|------|------|
| **READ_ONLY** | GET, MGET, EXISTS, TYPE, TTL, PTTL, SCAN, HGETALL, HGET, HKEYS, HLEN, LRANGE, LLEN, SMEMBERS, SCARD, ZRANGE, ZCARD, INFO, DBSIZE, OBJECT | ✅ 允许执行 |
| **WRITE** | SET, SETNX, DEL, EXPIRE, PERSIST, HSET, HDEL, LPUSH, RPUSH, LPOP, RPOP, SADD, SREM, ZADD, ZREM, INCR, DECR, APPEND | ❌ 禁止执行 |
| **DANGEROUS** | KEYS, FLUSHALL, FLUSHDB, CONFIG, SHUTDOWN, DEBUG, SLAVEOF, REPLICAOF, BGSAVE, BGREWRITEAOF, MONITOR, CLIENT KILL | ❌ 严禁执行 |

## 规则

1. **只读**：adapter 客户端仅暴露只读方法，不提供写操作接口
2. **禁用 KEYS 命令**：使用 SCAN 替代，防止大库阻塞
3. **SCAN 结果上限**：单次 scan_keys 最多返回 100 个 key
4. **大 Hash 防护**：如果 HGETALL 的字段数超过 500，建议用 HSCAN 分批读取
5. **Cluster 注意**：cluster 模式下，部分命令行为不同（如 SCAN 只扫当前节点）

## 敏感 Key 模式

以下 key 模式可能包含敏感数据，查询结果需脱敏：

| Key 模式 | 包含内容 | 脱敏要求 |
|---------|---------|---------|
| `user:token:*` | 登录 Token | 完全隐藏值 |
| `session:*` | 会话信息 | 脱敏手机号、用户名 |
| `pay:*` / `payment:*` | 支付信息 | 脱敏银行卡、金额可展示 |
| `sms:code:*` | 短信验证码 | 完全隐藏值 |

## 查询限制

| 限制项 | 值 |
|--------|-----|
| 单次 SCAN 返回上限 | 100 keys |
| LRANGE 最大范围 | 0 ~ 99（100 条） |
| ZRANGE 最大范围 | 0 ~ 99（100 条） |
| SMEMBERS 最大展示 | 前 100 个 |
