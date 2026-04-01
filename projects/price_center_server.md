# price_center_server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/omp/price_center_server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `price_center_server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `src/main/java/com/ykc/controller/activity/AlipayActivityController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/activity/CoffeeMakerActivityController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/activity/NewStationActivityController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/activity/SellPriceYkcActivityController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/baseController/BaseController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/baseController/ImportFailRecordController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/contract/ContractController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/flowSide/DrainageIncomeStationPriceOperatorController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/flowSide/DrainageIncomeStationPriceStandardController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/flowSide/FlowCostActivityController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/flowSide/FlowCostPriceSpecialController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/flowSide/FlowCostPriceSpecialOperatorController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/flowSide/FlowCostPriceStandardController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/flowSide/ReferralTrafficIncomeActivityController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/flowSide/ReferralTrafficIncomePriceSpecialController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/flowSide/ReferralTrafficIncomePriceStandardController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/globalStationActivity/ApiGlobalStationActivityController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/globalStationActivity/GlobalStationActivityController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/gray/GrayController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/gray/GrayStationController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/memberStation/MemberStationController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/memberStation/MemberStationSpecialController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/open/ForeignFlowController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/open/ForeignPurchaseController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/open/ForeignSellController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/platformFee/PlatformFeeController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/price/PriceController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/price/foreign/BurialPointPriceQueryController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/price/foreign/ForeignPriceController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/price/foreign/ForeignPriceRpcController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `src/main/java/com/ykc/service/activity/impl/AlipayActivityServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/activity/impl/CoffeeMakerActivityServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/activity/impl/FlowCostActivityServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/activity/impl/NewStationActivityServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/activity/impl/PriceActivityFailServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/activity/impl/ReferralTrafficIncomeActivityServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/activity/impl/SellPriceYkcActivityServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/activityTask/impl/ActivityTaskServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/calculate/impl/AffectCalculateServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/calculate/record/impl/PriceConfigVerifyRecordServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/FlowCostActivityOldServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/FlowCostSpecialOldServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/FlowCostStandardOldServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/FlowImportDataServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/ImportFailRecordServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/PurchaseStandardOldServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/ReferralTrafficIncomeActivityOldServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/ReferralTrafficIncomeSpecialOldServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/ReferralTrafficIncomeStandardOldServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/common/impl/SellKaStandardOldServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `src/main/resources/mapper/activity/AlipayActivityMapper.xml` |
| Mapper XML | `src/main/resources/mapper/activity/FlowActivityFailMapper.xml` |
| Mapper XML | `src/main/resources/mapper/activity/FlowCostActivityMapper.xml` |
| Mapper XML | `src/main/resources/mapper/activity/FlowCostActivityOperatorMapper.xml` |
| Mapper XML | `src/main/resources/mapper/activity/ReferralTrafficIncomeActivityMapper.xml` |
| Mapper XML | `src/main/resources/mapper/activity/ReferralTrafficIncomeActivityOperatorMapper.xml` |
| Mapper XML | `src/main/resources/mapper/activity/SellPriceYkcActivityMapper.xml` |
| Mapper XML | `src/main/resources/mapper/activityTask/AutoAddActivityTaskMapper.xml` |
| Mapper XML | `src/main/resources/mapper/drainageIncomeStandard/DrainageIncomeStationPriceStandardMapper.xml` |
| Mapper XML | `src/main/resources/mapper/drainageIncomeStandard/DrainageIncomeStationPriceStandardOperatorMapper.xml` |
| Mapper XML | `src/main/resources/mapper/failRecord/ImportFailRecordMapper.xml` |
| Mapper XML | `src/main/resources/mapper/flowSide/FlowCostPriceSpecialMapper.xml` |
| Mapper XML | `src/main/resources/mapper/flowSide/FlowCostPriceSpecialOperatorMapper.xml` |
| Mapper XML | `src/main/resources/mapper/flowSide/FlowCostPriceStandardMapper.xml` |
| Mapper XML | `src/main/resources/mapper/flowSide/FlowSpecialFailMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `price_center_server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
