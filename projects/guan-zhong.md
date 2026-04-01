# guan-zhong

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/TRADE/guan-zhong` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `guan-zhong`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `src/main/java/com/ykc/guanzhong/page/customer/controller/TiNetCustomerController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/guanzhong/page/fleet/controller/FleetController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/battery/impl/BatteryCheckServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/battery/impl/BatteryOrderServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/battery/impl/BatteryReportQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/battery/impl/BatteryReportServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/charge/impl/ChargeServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/common/impl/CommonServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/common/impl/LocationServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/device/impl/GunQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/device/impl/PathPlanningServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/device/impl/StationQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/fleet/impl/FleetServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/frame/impl/IndexServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/help/impl/AppealServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/help/impl/FAQServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/market/impl/AdsServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/market/impl/MarketServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/order/impl/HistoryOrderServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/order/impl/OrderEvalServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/order/impl/RealtimeOrderServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/guanzhong/service/order/impl/UserOrderServiceImpl.java` | 见源码 |


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
| 通用 | `guan-zhong`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
