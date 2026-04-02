# charge-business-server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `TRADE/charge-business-server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `charge-business-server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| （本仓库未扫到 Controller） | — |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `charge-business-service/src/main/java/com/ykc/chargebusiness/processdata/service/impl/BatteryBMSDataServiceImpl.java` | 见源码 |
| ServiceImpl | `charge-business-service/src/main/java/com/ykc/chargebusiness/processdata/service/impl/ChargePeriodPowerServiceImpl.java` | 见源码 |
| ServiceImpl | `charge-business-service/src/main/java/com/ykc/chargebusiness/processdata/service/impl/ChargePeriodProcessServiceImpl.java` | 见源码 |
| ServiceImpl | `charge-business-service/src/main/java/com/ykc/chargebusiness/processdata/service/impl/OrderTrendServiceImpl.java` | 见源码 |
| ServiceImpl | `charge-business-service/src/main/java/com/ykc/chargebusiness/processdata/service/impl/SmokeStatusServiceImpl.java` | 见源码 |
| ServiceImpl | `charge-business-service/src/main/java/com/ykc/chargebusiness/processdata/service/impl/TradeDataServiceImpl.java` | 见源码 |
| ServiceImpl | `charge-business-service/src/main/java/com/ykc/chargebusiness/processdata/service/impl/VinCheckServiceImpl.java` | 见源码 |
| ServiceImpl | `charge-business-service/src/main/java/com/ykc/chargebusiness/reservation/service/impl/ChargeReservationServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `charge-business-service/src/main/resources/mappers/BMSChargeMapper.xml` |
| Mapper XML | `charge-business-service/src/main/resources/mappers/BatterChargeMapper.xml` |
| Mapper XML | `charge-business-service/src/main/resources/mappers/ChargeGunReservationRecordMapper.xml` |
| Mapper XML | `charge-business-service/src/main/resources/mappers/DeviceChargingMapper.xml` |
| Mapper XML | `charge-business-service/src/main/resources/mappers/OrderChargingBmsRecordMapper.xml` |
| Mapper XML | `charge-business-service/src/main/resources/mappers/TChargeSettlementMapper.xml` |
| Mapper XML | `charge-business-service/src/main/resources/mappers/TDeviceServerDealNewMapper.xml` |
| Mapper XML | `charge-business-service/src/main/resources/mappers/TbDeviceServerNewMapper.xml` |
| Mapper XML | `charge-business-service/src/main/resources/mappers/TradeChargingMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `charge-business-server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
