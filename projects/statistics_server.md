# statistics_server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `omp/statistics_server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `statistics_server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/AppOperatorStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/BaseController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/BusStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/CouponStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/CpoLargeScreenController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/CpoWorkbenchController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/DailyBillSummmaryController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/DataDashboardStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/DemoController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/EmpDigitalStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/EmpYEmsStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/ErrorMessageController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/FleetOverviewStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/FleetReconcileController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/FleetStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/HistoryOrderStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/HistoryOrderStatisticsExcelController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/HiveController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/MailSendController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/NewCpoStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/NewOperatorOrderStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/NewOrderCompareStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/NewOrgOrderStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/NewYkcOrderStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/NewYkcStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/OffLineExportController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/OperatorOrderStatisticsController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/OperatorOrderStatisticsExcelController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/OperatorSmallController.java` | 见源码 |
| Controller | `statistics-server-web/src/main/java/com/ykc/statistics/controller/OrderCharStatisticsController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/cache/impl/CacheServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/cpo/impl/NewCpoStatisticsServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/finance/impl/DailyFlowSummaryServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/finance/impl/IncomeAndExpendSummaryServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/BaseServerServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/BigDataServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/ClickServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/CollectionPaymentStatisticsServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/CpoLargeScreenServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/EmpDigitalStatisticsServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/EmpYEmsStatisticsServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/ErrorMessageServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/FleetReconcileServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/FleetStatisticsServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/GunServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/HistoryOrderStatisticsServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/HiveServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/MailSendServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/MonthAmountPowerHistoryServiceImpl.java` | 见源码 |
| ServiceImpl | `statistics-server-service/src/main/java/com/ykc/statistics/service/impl/NewYkcStatisticsServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/AdsFleetStationOrderLabelDtMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/AdsOperatorStationOrderAggDtMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/BMSChargeMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/BatterChargeMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/DailyBillSummaryDao.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/FinanceDataSummaryMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/FleetDayReconcileMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/FleetMonthReconcileMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/HiveMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/MonthAmountPowerHistoryMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/OperatorMonthReconcileMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/OperatorReconcileAccountMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/OuterOrderMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/OuterProviderMapper.xml` |
| Mapper XML | `statistics-server-web/src/main/resources/mybatis/OuterStationMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `statistics_server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
