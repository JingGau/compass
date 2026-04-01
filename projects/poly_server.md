# poly_server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/TRADE/poly_server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `poly_server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `src/main/java/com/ykc/polyservice/controller/alipay/AlipayController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/appUpgrade/AppUpgradeController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/batterycheck/BatteryCheckController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/buryingPoint/BuryingPointController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/charge/BaiduPileInfoController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/charge/GetTimeChargeController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/charge/ParkingLockController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/charge/PileEntryInfoController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/charge/PileEntryListController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/charge/PileInfoController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/charge/PileListController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/charge/SocLimitInfoController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/chargingUser/ChargingUserController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/member/MemberController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/open/OpenApiController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/order/HistoryOrderPagingController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/order/NoPayOrderDetailController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/order/NoPayOrderPagingController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/order/OrderDetailController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/order/RealTimeOrderController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/order/RealTimeOrderPagingController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/order/open/YkcHistoryOrderController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/order/open/YkcOccupancyOrderController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/order/open/YkcRealTimeOrderController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/parkingOrder/ParkingOrderController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/personCenter/RechargeBuyController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/personCenter/RechargeController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/personCenter/UserInfoController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/powerStation/BaiduPowerStationDetailController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/polyservice/controller/powerStation/PowerStationChannelListController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `src/main/java/com/ykc/polyservice/feign/finance/service/impl/FinanceNonSecretApiServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/polyservice/service/member/impl/MemberServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/polyservice/service/personCenter/RechargeBuyServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/polyservice/service/pile/impl/PileInfoServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/polyservice/service/station/impl/StationInfoServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/polyservice/service/user/impl/UserInfoServiceImpl.java` | 见源码 |


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
| 通用 | `poly_server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
