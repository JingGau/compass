# 系统拓扑摘要

## 核心链路

- C端 App -> 网关 -> 订单服务 / 充电服务 / 支付服务 / 财务服务
- B端 `omp-shop` -> 网关 -> 各业务后端服务
- 关键数据面：SLS（日志）、Doris（分析数据）、MySQL（业务库）、Redis（缓存）、ES（检索）

## 常见问题定位入口

- 资金与余额：`finance-server` + `ods_finance_cdc` + 钱包缓存
- 订单与支付：`order-server` / `payment-server` + `ods_order_cdc`
- 充电过程：`charge-server` + 充电订单链路日志
