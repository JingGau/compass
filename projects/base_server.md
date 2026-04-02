# base_server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `omp/base_server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `base_server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `base_server/src/main/java/com/ykc/baseserver/cClient/stationOperator/controller/StationOperatorCRpcController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/cClient/user/controller/ChargingUserRpcController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/carTeam/controller/CarTeamV2Controller.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/carTeam/controller/OrgChargePlanController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/account/AccountController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/accountingSubject/AccountingSubjectController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/activity/ActivityController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/allmessage/AllMessageController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/allmessage/AllMessageWebController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/allmessage/RemoteCacheController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/autoConfigStationRule/AutoConfigStationRuleController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/autoConfigStationRule/RpcAutoConfigStationRuleController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/barriergate/BarrierGateController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/barriergate/BarrierGateForOperateController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/blackwhitelist/BlackWhiteListController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/cache/BaseCacheController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/cache/ClearCacheController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/cache/GunCacheController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/cache/PileCacheController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/cache/StationCacheController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/cache/VehicleOrgCacheController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/carTeam/CarTeamController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/carTeam/CarTeamWebController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/central/BizBlackWhiteController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/central/BizSpecialConfigController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/central/rpc/CentralBizBlackWhiteRpcController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/central/rpc/CentralBizSpecialRpcController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/chargingstation/BusChargingStationController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/chargingstation/ChargingStationController.java` | 见源码 |
| Controller | `base_server/src/main/java/com/ykc/baseserver/core/controller/chargingstation/ChargingStationExtController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/device/service/impl/ChargeStationLabelServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/device/service/impl/ChargingGunCServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/device/service/impl/ChargingPileCServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/device/service/impl/ChargingPileGunCheckServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/device/service/impl/ChargingStationCServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/device/service/impl/CpoAppPileGunServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/device/service/impl/ParkFeeServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/device/service/impl/StationPictureServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/stationOperator/service/impl/StationOperatorCServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/cClient/user/service/impl/ChargingUserCServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/carTeam/impl/VehicleOrganizationExtServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/central/impl/BizBlackWhiteServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/central/impl/BizSpecialConfigServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/central/impl/CentralBizRpcAbilityServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/chargingstation/impl/ChargingStationFeeReverseServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/dashboard/impl/DataDashboardServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/iop/IopMatchPushStationServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/offlinecard/OfflineCardServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/orgExt/impl/VehicleOrgExtServiceImpl.java` | 见源码 |
| ServiceImpl | `base_server/src/main/java/com/ykc/baseserver/core/service/parkinglock/ParkingLockServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `base_server/src/main/resources/mybatis/activity/ActivityMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/allmessage/AllMessageMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/autoConfigStationRule/AutoConfigRulePriorityMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/autoConfigStationRule/AutoConfigStationBlackRosterMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/autoConfigStationRule/AutoConfigStationChangeRecordMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/autoConfigStationRule/AutoConfigStationRuleMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/autoConfigStationRule/AutoConfigStationWhiteRosterMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/bank/AgreementSignFailRecordMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/barrier/BarrierGatePlatConfigMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/barrier/BaseSTBarrierGateMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/barriergate/BarrierGateMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/base/carTeam/CtpOcrRecordMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/base/carTeam/CtpOrganizationOcrConfigMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/base/device/ChargingGunExtMapper.xml` |
| Mapper XML | `base_server/src/main/resources/mybatis/base/device/ChargingGunV2Mapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `base_server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
