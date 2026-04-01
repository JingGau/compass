# Elasticsearch 安全规则

AI 在调用 Elasticsearch adapter 前，必须遵守以下规则。

## 操作分级

| 级别 | 操作 | 策略 |
|------|------|------|
| **READ_ONLY** | _search, _count, _cat/indices, _mapping, _settings, _analyze | ✅ 允许执行 |
| **WRITE** | index (写文档), _update, _delete, _bulk | ❌ 禁止执行 |
| **DANGEROUS** | _delete_by_query, _reindex, _close, _open, _shrink, _split, _clone | ❌ 严禁执行 |
| **ADMIN** | _create (index), _aliases (修改), _template (修改), _snapshot | ❌ 严禁执行 |

## 规则

1. **只读**：adapter 客户端仅暴露 search / search_keyword / aggregate / list_indices / get_mapping 方法
2. **查询结果上限**：单次 search 的 `size` 不超过 100
3. **深分页防护**：`from + size` 不超过 10000（ES 默认 max_result_window），超过时建议使用 scroll 或 search_after
4. **通配符索引限制**：禁止对 `*` 执行 search（全索引扫描），必须指定具体索引名或前缀模式
5. **聚合防护**：aggregation 的 terms/histogram 的 `size` 不超过 1000，防止内存溢出

## 索引敏感度

| 索引模式 | 包含内容 | 注意事项 |
|---------|---------|---------|
| `user-*` / `account-*` | 用户信息 | 结果需脱敏（手机号、身份证） |
| `payment-*` / `trade-*` | 交易信息 | 金额可展示，银行卡需脱敏 |
| `log-*` / `audit-*` | 日志/审计 | 可能含 PII，按字段脱敏 |
| `.kibana*` / `.security*` | 系统索引 | 禁止查询 |

## 查询限制

| 限制项 | 值 |
|--------|-----|
| 单次 search size 上限 | 100 |
| from + size 上限 | 10,000 |
| 聚合 terms size 上限 | 1,000 |
| 禁止全索引通配符 search | `*` |

## 版本兼容注意

| ES 版本 | 差异 |
|---------|------|
| 6.x | `total` 直接返回数字；type 仍存在 |
| 7.x | `total` 为 `{value, relation}` 对象；type 逐步废弃 |
| 8.x | Security 默认开启；`body` 参数废弃，需用关键字参数 |

adapter 已自动处理这些差异，AI 不需要关注版本细节。
