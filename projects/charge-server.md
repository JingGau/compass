# charge-server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/TRADE/charge-server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `charge-server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `device-business-web/src/main/java/com/ykc/devicebusiness/controller/ChargeController.java` | 见源码 |
| Controller | `device-business-web/src/main/java/com/ykc/devicebusiness/controller/OpenController.java` | 见源码 |
| Controller | `device-business-web/src/main/java/com/ykc/devicebusiness/controller/QrCodeController.java` | 见源码 |
| Controller | `device-business-web/src/main/java/com/ykc/devicebusiness/controller/V2ChargeController.java` | 见源码 |
| Controller | `device-business-web/src/main/java/com/ykc/devicebusiness/controller/rpc/ChargeRpcController.java` | 见源码 |
| Controller | `device-business-web/src/main/java/com/ykc/devicebusiness/controller/rpc/CommandDownRpcController.java` | 见源码 |
| Controller | `device-business-web/src/main/java/com/ykc/devicebusiness/controller/rpc/StartStopChargeRpcController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/BMSBatterChargeServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/CommandDownServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/CommandUpServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/FinanceServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/FreeChargeServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/GunNewServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/GunServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/NotifyServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/OrderNewServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/OrderServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/QrCodeServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/ReserveServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/StatisticServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/UserNewServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/UserServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/V2ChargeServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/service/impl/VehicleServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/session/service/impl/SessionCacheServiceImpl.java` | 见源码 |
| ServiceImpl | `device-business-service/src/main/java/com/ykc/devicebusiness/session/service/impl/SessionDataServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `device-business-web/src/main/resources/mapper/ChargeTimeMetricsMapper.xml` |
| Mapper XML | `device-business-web/src/main/resources/mapper/TBMSChargeMapper.xml` |
| Mapper XML | `device-business-web/src/main/resources/mapper/TBatterChargeMapper.xml` |
| Mapper XML | `device-business-web/src/main/resources/mapper/TChargeSettlementMapper.xml` |
| Mapper XML | `device-business-web/src/main/resources/mapper/TDeviceServerDealNewMapper.xml` |
| Mapper XML | `device-business-web/src/main/resources/mapper/TbDeviceServerNewMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `charge-server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
