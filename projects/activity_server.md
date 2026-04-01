# activity_server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/omp/activity_server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `activity_server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `activity_server/src/main/java/com/ykc/controller/CrmAppreciationPlanController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/EnterpriseWeChatConfigController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/PlanBatchAddController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/PlanBatchEditController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/RechargeActivityController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/TaskServerController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/UserActivityRecordController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/activityorder/ActivityOrderRpcController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/activityrefund/ActivityRefundRpcController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/advertising/ActivityPropagandaAdminController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/advertising/ActivityPropagandaAppController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/advertising/AppAdAppController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/advertising/AppAdRpcController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/advertising/AppAdWebController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/advertising/CommandAdAppController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/advertising/PcAdAppController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/advertising/PcAdWebController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/battery/BatteryTestingAppController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/battery/BatteryTestingRpcController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/chargingcard/ChargingCardController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/chargingcard/ChargingCardRpcController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/creditcard/CreditCardController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/electriccard/ElectricCardBatchController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/electriccard/ElectricCardController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/electriccard/ElectricCardNumberController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/giftcard/GiftCardRpcController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/offlinecard/OfflineCardController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/rechargecard/RechargeCardBatchController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/card/rechargecard/RechargeCardController.java` | 见源码 |
| Controller | `activity_server/src/main/java/com/ykc/controller/cardcoupon/CardCouponRpcController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/activityorder/impl/ActivityOrderRpcServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/activityorder/impl/ActivityOrderUnsubscribeServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/activityrefund/impl/ActivityRefundRpcServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/advertising/impl/ActivityPropagandaServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/advertising/impl/AppAdAppServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/advertising/impl/AppAdWebServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/advertising/impl/CommandAdAppServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/battery/BatteryTestingServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/calculate/impl/AffectCalculateServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/card/impl/ElectricCardBatchServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/card/impl/ElectricCardNumberServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/card/impl/ElectricCardRecordServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/card/impl/ElectricCardServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/card/impl/RechargeCardBatchServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/card/impl/RechargeCardServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/cardcoupon/impl/CardCouponRpcServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/cardcoupon/impl/CardRpcServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/cardcoupon/impl/CouponRpcServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/contract/impl/ContractHandleServiceImpl.java` | 见源码 |
| ServiceImpl | `activity_server/src/main/java/com/ykc/service/contract/impl/ContractServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `activity_server/src/main/resources/mapper/ActivityCodeStationMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/ActivityListQueryMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/ActivityRuleMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/ChargingCardMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CouponMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmAppreciationPlanMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmDTOfflineCardRelationMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmDTOfflinePileRelationMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmDTTimingChargeConfigRelationDao.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmDTTimingChargeGunRecordMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmDTTimingChargeStartupRecordMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmDTTimingReadyChargeRecordMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmSTHelpDocumentMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmSTOfflineCardRecordMapper.xml` |
| Mapper XML | `activity_server/src/main/resources/mapper/CrmSTTimingChargeConfigMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `activity_server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
