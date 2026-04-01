# payment-server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/FINANCE/payment-server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `payment-server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| （本仓库未扫到 Controller） | — |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/channel/service/impl/PaymentChannelServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/order/service/impl/PayOrderBaseServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/order/service/impl/PreOrderBaseServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/order/service/impl/RefundOrderBaseServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/order/service/impl/SurplusRecordBaseServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/product/insurance/service/impl/InsurancePayServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/product/prepaid/service/impl/OrderSettlementServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/product/prepaid/service/impl/PrepaidAddOnServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/product/prepaid/service/impl/PrepaidQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/product/prepaid/service/impl/PrepaidServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/product/prepaid/service/impl/ServiceDelayMessageServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/product/prepaid/service/impl/ServiceOrdTradeNotifyServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/unified/service/impl/UnifiedPayServiceImpl.java` | 见源码 |
| ServiceImpl | `payment-server-service/src/main/java/com/ykc/payment/unified/service/impl/UnifiedRefundServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `payment-server-service/src/main/resources/repository/mysql/channel/PaymentChannelMapper.xml` |
| Mapper XML | `payment-server-service/src/main/resources/repository/mysql/compensation/CompensationItemMapper.xml` |
| Mapper XML | `payment-server-service/src/main/resources/repository/mysql/order/PaymentPayOrderMapper.xml` |
| Mapper XML | `payment-server-service/src/main/resources/repository/mysql/order/PaymentPreOrderMapper.xml` |
| Mapper XML | `payment-server-service/src/main/resources/repository/mysql/order/PaymentPreOrderServiceOrderDetailMapper.xml` |
| Mapper XML | `payment-server-service/src/main/resources/repository/mysql/order/PaymentRefundOrderFundItemMapper.xml` |
| Mapper XML | `payment-server-service/src/main/resources/repository/mysql/order/PaymentRefundOrderMapper.xml` |
| Mapper XML | `payment-server-service/src/main/resources/repository/mysql/order/SurplusRefundRecordMapper.xml` |
| Mapper XML | `payment-server-service/src/main/resources/repository/mysql/order/SurplusRefundRelationMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `payment-server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
