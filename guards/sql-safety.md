# SQL 安全规则

**prod 环境所有 SQL 执行前必须强制 EXPLAIN，三档判定，不可绕过，不可跳过，自动模式亦不例外。**

> 本文件是 SQL 安全的**唯一权威来源**。SKILL.md、query-planning.md、result-analysis.md 中涉及 EXPLAIN 的规则均以本文件为准，其他文件只做引用，不得自行定义细节。

---

## 语句白名单

| 允许 | 禁止（直接拒绝，不展示给用户执行） |
|------|------------------------------------|
| `SELECT` | `DELETE` / `UPDATE` / `INSERT` |
| `SHOW DATABASES` / `SHOW TABLES` / `SHOW COLUMNS` | `DROP` / `ALTER` / `TRUNCATE` / `CREATE` |
| `DESC` / `DESCRIBE` | `GRANT` / `REVOKE` |
| `EXPLAIN` | `CALL` / `EXECUTE` 存储过程 |

检查方式：对 SQL 做大写处理后，检查是否以禁止关键字开头，或包含 `; DELETE` / `; UPDATE` 等注入模式。

---

## EXPLAIN 预评估（仅 Doris/MySQL，prod 环境强制执行）

### 执行流程

```
生成 SQL
  ↓
执行 EXPLAIN {SQL}
  ↓
AI 分析 EXPLAIN 结果，按以下优先级判断风险等级
  ↓
按风险等级输出对应交互格式
```

### 风险判定（满足任一条件即触发对应等级）

| 风险等级 | 触发条件 | 处理方式 |
|---------|---------|---------|
| 🟢 低风险 | rows < 10万，且 type ≠ ALL，且 key 非 NULL | 自动执行，无需确认 |
| 🟡 中风险 | rows 10万～100万；或 key = NULL 但 type ≠ ALL | 黄色警告，展示详情，建议优化，等待确认 |
| 🔴 高风险 | rows > 100万；或 type = ALL（全表扫描）；或 AI 综合判断有严重性能风险 | 红色警告，必须用户明确输入确认才能执行 |

> **AI 综合判断**：结合业务表量级、查询复杂度、是否有 WHERE 条件等，AI 认为存在性能风险时可将等级上调，但不得下调。

### 分区表强制过滤

以下 Doris 表为分区表，查询必须包含 `dt_month = 'YYYY-MM-01'`：
- `ods_order_cdc.ods_order_s_t_charging_record_history`
- `ods_order_cdc.ods_order_d_t_pay_detail`
- `ods_finance_cdc.ods_finance_d_t_user_flow`

AI 发现目标表是分区表但 SQL 中缺少 `dt_month` 时，自动从实体池中的时间信息补充，不打断用户。

---

## 交互格式（三档统一规范）

### 🟢 低风险 — 自动执行

```
✅ EXPLAIN 通过（type=range, rows≈26,000, key=idx_user_id）
准备执行：
    SELECT ... FROM t_user_wallet WHERE user_id = 123456
执行中…
```

> 无需用户操作，自动继续。

---

### 🟡 中风险 — 黄色警告，等待确认

```
🟡 EXPLAIN 警告
┌─────────────────────────────────────────┐
│ 预估扫描：~680,000 行（中风险）          │
│ 风险原因：扫描行数较多 / 未命中索引      │
│ 涉及表：t_user_wallet                   │
└─────────────────────────────────────────┘

准备执行：
    SELECT * FROM t_user_wallet WHERE status = 1 AND org_id = 789

建议优化：可在 (org_id, status) 上建联合索引，预计扫描降至千行级

**[确认执行]** **[我来改写 SQL]** **[跳过此步]**
```

---

### 🔴 高风险 — 红色警告，必须明确确认

```
🔴 EXPLAIN 高风险，已暂停
┌─────────────────────────────────────────┐
│ 预估扫描：~2,300,000 行（高风险）        │
│ 风险原因：全表扫描（type=ALL）           │
│ 涉及表：t_user_wallet                   │
└─────────────────────────────────────────┘

准备执行：
    SELECT * FROM t_user_wallet WHERE status = 1

建议优化：增加 user_id 或时间范围条件；或在 status 字段加索引

⚠️ 请明确回复「确认执行」才会继续，其他回复均视为取消。

**[确认执行]** **[我来改写 SQL]** **[跳过此步]**
```

> 用户选「我来改写 SQL」：等待用户提供新 SQL，重新走 EXPLAIN 流程。
> 用户选「跳过此步」：记录该步状态为 `❌ 跳过（高风险）`，继续下一步。

---

## 环境适用范围

| 环境 | EXPLAIN 要求 |
|------|-------------|
| prod | **强卡，任何模式下不得绕过**（含自动模式、手动模式、重试流程） |
| test / uat | 跳过，直接执行 |

---

## 用户确认的例外

若 `memory/confirmations.yaml` 中记录了「低风险 SELECT 无需逐条确认」，则 🟢 低风险的 SELECT 可直接执行（但仍记录审计日志）。首次使用时必须询问用户是否启用此例外。

---

## EXPLAIN 结果内联标注规范

在排查过程卡片（result-analysis.md）中，每个涉及 prod SQL 的步骤须在工具/环境列内联标注 EXPLAIN 结果，格式如下：

| 风险等级 | 内联标注示例 |
|---------|------------|
| 🟢 低风险 | `mysql / prod（EXPLAIN ✅ type=range, rows≈1,200, key=idx_user_id）` |
| 🟡 中风险 | `mysql / prod（EXPLAIN 🟡 rows≈68万, key=NULL，用户已确认）` |
| 🔴 高风险已确认 | `mysql / prod（EXPLAIN 🔴 type=ALL, rows≈230万，用户确认执行）` |
| 🔴 高风险已跳过 | `mysql / prod（EXPLAIN 🔴 type=ALL, rows≈230万，用户跳过）` |