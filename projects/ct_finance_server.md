# ct_finance_server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/FINANCE/ct_finance_server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `ct_finance_server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `src/main/java/com/ykc/controller/BillApplyController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/UploadController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/accountManagement/DriverController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/accountManagement/MainCtpController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/accountManagement/MarketingAccountController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/accountManagement/OperatorController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/accountManagement/SubCtpController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/accountManagement/UploadFileController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/bloc/BlocCarCompanyManageController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/pay/RechargeSlipController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/pay/UnifiedPayController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/test/EasyExcelDemoController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/test/TestController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/withdrawal/PaymentSlipController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `src/main/java/com/ykc/service/accountManagementService/impl/DriverServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/accountManagementService/impl/MainCtpServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/accountManagementService/impl/MarketingAccountServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/accountManagementService/impl/OperatorServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/accountManagementService/impl/SubCtpServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/bill/impl/BillInvoiceInfoServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/bill/impl/ThirdPartIncomeSharePlanServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/bloc/impl/BlocCarCompanyManageServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/collection/impl/CompanyServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/impl/BillApplyServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/impl/BusinessSearchServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/impl/ObtainCacheServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/impl/UploadServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/pay/impl/RechargeSlipServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/withdrawal/impl/PaymentSlipServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `src/main/resources/mybatis/accountManagement/DriverMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/accountManagement/MainCtpMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/accountManagement/OrgMarketingFlowMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/accountManagement/SubCtpMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/BillAndRecordMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/BillApplyAdjustmentMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/BillApplyHistoryMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/BillApplyMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/BillInvoiceInfoHisMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/BillInvoiceInfoMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/CancelBillRecordMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/OperatorInvoiceConfigMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/StationProxyMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/bill/ThirdPartIncomeSharePlanMapper.xml` |
| Mapper XML | `src/main/resources/mybatis/collection/AccountSubjectCompanyMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `ct_finance_server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
