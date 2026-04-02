# Doris JDBC Catalog 索引

> Doris 通过 JDBC Catalog 直接穿透查询业务 MySQL/PolarDB，不走 CDC 同步。
> 这些库**不会出现在 `SHOW DATABASES` 中**，必须用三段式路径 `catalog.database.table` 访问。

## 使用方式

```sql
-- internal catalog（CDC 同步数据，SHOW DATABASES 可见）
SELECT * FROM ods_finance_cdc.ods_finance_d_t_clearing_wallet WHERE ...

-- JDBC catalog（直连业务库，SHOW DATABASES 不可见，必须用三段式）
SELECT * FROM finance_jdbc_catalog.yunkc_finance.`clearing_tp_clearing_bill` WHERE ...
```

## 已注册 JDBC Catalog

| Catalog 名 | 连接的业务库 | 涉及服务 | 关键表 |
|------------|------------|---------|--------|
| `finance_jdbc_catalog` | `yunkc_finance` | clearing_server, finance_server | 清分/钱包/提现相关的 tp 表 |
| `order_jdbc_catalog` | — | order-server, trade-order | 订单相关直查 |
| `base_jdbc_catalog` | — | base_server | 基础数据直查 |

> 完整 catalog 列表可通过 `SHOW CATALOGS` 查询。

## finance_jdbc_catalog.yunkc_finance 核心表

> 以下表是 CDC **未同步**到 `ods_finance_cdc` 的表，只能通过 JDBC Catalog 查询。

### 三方清分（Tp）相关

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `clearing_tp_clearing_bill` | 三方清分账单 | bill_number, business_type, status, amount, payer_id, payee_id |
| `clearing_tp_withdraw_bill` | 三方提现单 | withdraw_number, status, amount |
| `clearing_tp_wallet` | 三方钱包 | account_id, balance, frozen_amount |
| `clearing_tp_wallet_flow` | 三方钱包流水 | flow_id, business_type, amount |

#### 清分单状态枚举（TpClearingBillStatusEnum）

| status | 含义 |
|--------|------|
| PENDING | 待清分 |
| PROCESSING | 清分中（已提交银行，待确认） |
| CLEARED | 已入账 |
| FAIL | 清分失败（会被 Job 自动重试） |

#### 提现单状态枚举（TpWithdrawStatusEnum）

| status | 含义 |
|--------|------|
| PROCESSING | 处理中 |
| SUCCESS | 成功 |
| FAIL | 失败 |
| DISHONOUR | 已退票 |

### 清分定时任务（XXL-Job）

| Job 名 | 职责 | 触发频率 |
|--------|------|---------|
| `execTpClearing` | 扫描 PENDING/FAIL 单，提交银行 | 每日 04:00 / 16:00 |
| `confirmTpClearingResult` | 确认银行批量交易结果，PROCESSING → CLEARED/FAIL | 定时 |
| `executeTpAutoWithdrawJob` | 三方自动提现 | 定时 |
| `confirmTpWithdrawResultJob` | 确认提现结果 | 定时 |

## 排查注意事项

1. **查表前先判断在哪**：CDC 同步的表用 `ods_finance_cdc.xxx`，未同步的表用 `finance_jdbc_catalog.yunkc_finance.xxx`
2. **JDBC Catalog 查询可能较慢**：因为是穿透到业务库，建议加时间/状态过滤条件
3. **分区表仍然注意 dt_month**：CDC 表是分区表要带 dt_month，JDBC 直查的业务表不需要

## 元信息

- created_at: 2026-04-02
- source: 线上排查发现 + 代码分析
