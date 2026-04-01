# 系统拓扑

> 描述业务系统宏观结构，帮助 AI 在场景分类阶段快速判断问题涉及哪些服务。

## C 端（用户 App）

无前端代码，排查只能依赖日志和数据库。

### 核心服务

| 服务 | 代码路径 | 职责 | SLS 容器名（推测） |
|------|---------|------|------------------|
| charge-server | TRADE/charge-server | 计费服务，充电过程核心控制 | charge-server |
| charge-business-server | TRADE/charge-business-server | 计费业务服务 | charge-business-server |
| order-server | TRADE/order-server | 订单服务，订单生命周期管理 | order-server |
| trade-order-server | TRADE/trade-order-server | 交易订单系统，高性能交易处理 | trade-order-server |
| finance_server | FINANCE/finance_server | 财务主服务：钱包、支付、发票、对账 | finance-server |
| payment-server | FINANCE/payment-server | 支付服务，支付渠道接入 | payment-server |
| guan-zhong | TRADE/guan-zhong | 充电业务应用（关中） | guan-zhong |
| hangu | TRADE/hangu | 函谷关通用网关服务 | hangu |

### 辅助服务

| 服务 | 代码路径 | 职责 |
|------|---------|------|
| flow-charge-server | TRADE/flow-charge-server | 流量计费服务 |
| crop-order-server | TRADE/crop-order-server | 订单服务（另一套） |
| order-foundation | TRADE/order-foundation | 新订单结算系统 |
| mq-consumer | TRADE/mq-consumer | MQ 消费者，异步任务处理 |
| trade-sync-server | TRADE/trade-sync-server | 充电交易数据同步 |
| poly_server | TRADE/poly_server | 聚合服务 |
| poly-statistics-server | TRADE/poly-statistics-server | 聚合统计服务 |
| alarm-server | TRADE/alarm-server | 告警服务 |

## B 端（omp-shop 商户管理后台）

有完整前端代码（Vue），可通过「页面 → 接口 → 日志」三层追溯。

### 前端

| 项目 | 代码路径 | 技术栈 |
|------|---------|--------|
| omp-shop | omp/omp-shop | Vue 2 + Element UI |

### 关联后端服务

| 服务 | 代码路径 | 职责 | SLS 容器名（推测） |
|------|---------|------|------------------|
| base_server | omp/base_server | 基础服务：机构、车队、电站、桩管理 | base-server |
| finance_server | FINANCE/finance_server | 财务：钱包、充值、扣款、发票 | finance-server |
| statistics_server | omp/statistics_server | 统计报表服务 | statistics-server |
| activity_server | omp/activity_server | 活动/营销服务 | activity-server |
| price_center_server | omp/price_center_server | 价格中心：电价、服务费 | price-center-server |
| open_api_server | omp/open_api_server | 开放 API 服务 | open-api-server |
| device-status | omp/device-status | 设备状态服务 | device-status |
| status-server | omp/status-server | 状态服务 | status-server |
| event_tracing_server | omp/event_tracing_server | 埋点采集 | event-tracing-server |

## FINANCE 专属服务

| 服务 | 代码路径 | 职责 |
|------|---------|------|
| clearing_server | FINANCE/clearing_server | 清算服务：计费、记账、清分、结算 |
| invoice-server | FINANCE/invoice-server | 收票服务 |
| reconciliation_server | FINANCE/reconciliation_server | 对账系统 |
| bank_ability_center | FINANCE/bank_ability_center | 银行能力中心 |
| ct_finance_server | FINANCE/ct_finance_server | 财务核算服务 |
| unionpay_acquire_server | FINANCE/unionpay_acquire_server | 银联接入服务 |

## 服务间调用关系（常见链路）

```
充电流程:
  App → hangu(网关) → charge-server(充电控制)
                    → order-server(创建订单)
                    → trade-order-server(交易处理)
                    → finance_server(计费结算)
                    → payment-server(支付)

B端操作:
  omp-shop → base_server(基础数据)
           → finance_server(钱包/发票)
           → statistics_server(报表)
           → price_center_server(电价)

支付链路:
  finance_server → payment-server → bank_ability_center/unionpay_acquire_server

清分结算:
  clearing_server → finance_server → reconciliation_server

异步处理:
  各服务 → MQ → mq-consumer → 业务处理
```

## 元信息
- generated_at: 2026-03-28
- generated_by: manual + workspace-index.yaml
- last_verified: 2026-03-28
- source: initial-setup
