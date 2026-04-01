# foundation

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/omp/foundation` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `foundation`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| （本仓库未扫到 Controller） | — |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/aggregation/service/impl/OperatorDeviceServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/BarrierGateMaintainServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/BarrierGateQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargeTogetherPileServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingGunMaintainServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingGunQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingPileBrandServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingPileClusterModelServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingPileClusterServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingPileExtServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingPileMaintainServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingPileModelServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingPileQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingStationExtServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingStationMaintainServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ChargingStationQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/DeviceOperationRecordServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ParkingLockMaintainServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/ParkingLockQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-service/src/main/java/com/ykc/foundation/device/service/impl/PileAfterSalesServiceMaintainServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/BarrierGateCameraMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargeTogetherPileMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingDeviceJoinMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingGunMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingPileBrandMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingPileClusterMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingPileClusterModelMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingPileExtMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingPileMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingPileModelMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingStationAttributeMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingStationExtMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingStationLabelsMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingStationMapper.xml` |
| Mapper XML | `foundation-service/src/main/resources/com/ykc/foundation/device/infrastructure/repository/mysql/ChargingStationOperatorMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `foundation`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
