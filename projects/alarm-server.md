# alarm-server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/TRADE/alarm-server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `alarm-server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `alarm-service/src/main/java/com/ykc/controller/AbnOrderMessageController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/AlarmChargeMoneyController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/AlarmDeviceRecordController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/AlarmPileTroubleRecordController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/AlarmPlaceholderController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/AlarmRuleController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/AlarmStationController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/AlarmUserArrearsRecordController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/AlarmUserController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/OccOrderController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/OccupancyFeeOrderController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/VoiceMoveCarConfigController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/VoiceMoveCarController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/app/AppOperatorOccupyController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/open/BaseCacheSyncController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/open/HandlePileOfflineController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/open/MonitorMessageController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/pile/PileOfflineController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/rpc/AlarmAccessController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/rpc/OccupyOrderQueryRpcController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/rpc/StationAlarmConfigController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/rpc/TroubleRecordQueryRpcController.java` | 见源码 |
| Controller | `alarm-service/src/main/java/com/ykc/controller/web/WebOperatorOccupyController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| （本仓库未扫到 ServiceImpl） | — |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| （未扫到 mapper 目录下 xml） | — |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `alarm-server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
