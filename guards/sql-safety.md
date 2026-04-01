# SQL 安全规则

所有 SQL 执行前必须经过以下检查流程，**不可跳过**。

## 语句白名单

| 允许 | 禁止（直接拒绝，不展示给用户执行） |
|------|------------------------------------|
| `SELECT` | `DELETE` / `UPDATE` / `INSERT` |
| `SHOW DATABASES` / `SHOW TABLES` / `SHOW COLUMNS` | `DROP` / `ALTER` / `TRUNCATE` / `CREATE` |
| `DESC` / `DESCRIBE` | `GRANT` / `REVOKE` |
| `EXPLAIN` | `CALL` / `EXECUTE` 存储过程 |

检查方式：对 SQL 做大写处理后，检查是否以禁止关键字开头，或包含 `; DELETE` / `; UPDATE` 等注入模式。

## EXPLAIN 预评估（仅 Doris/MySQL）

```
生成 SQL
  ↓
EXPLAIN {SQL}  →  读取 rows 字段（预估扫描行数）
  ↓
< 10 万行   →  正常，展示给用户确认后执行
10万~100万  →  黄色警告：显示预估行数，建议加过滤条件
> 100 万行  →  红色警告：必须用户明确输入"确认执行"才能执行
```

展示格式：
```
准备执行：
    SELECT ... FROM ... WHERE ...

预估扫描：~26,000 行（低风险）

确认执行？
```

## 分区表强制过滤

以下 Doris 表为分区表，查询必须包含 `dt_month = 'YYYY-MM-01'`：
- `ods_order_cdc.ods_order_s_t_charging_record_history`
- `ods_order_cdc.ods_order_d_t_pay_detail`
- `ods_finance_cdc.ods_finance_d_t_user_flow`

AI 发现目标表是分区表但 SQL 中缺少 `dt_month` 时，自动从实体池中的时间信息补充，不打断用户。

## 用户确认的例外

若 `memory/confirmations.yaml` 中记录了「低风险 SELECT 无需逐条确认」，则扫描 < 10 万行的 SELECT 可直接执行（但仍记录审计日志）。首次使用时必须询问。
