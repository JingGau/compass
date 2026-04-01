# reconciliation_server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/FINANCE/reconciliation_server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `reconciliation_server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `reconciliation-application/src/main/java/com/ykc/reconciliation/controller/cpo/StationSettleSummaryController.java` | 见源码 |
| Controller | `reconciliation-application/src/main/java/com/ykc/reconciliation/controller/cpo/monthlyserv/CpoMonthlyBillController.java` | 见源码 |
| Controller | `reconciliation-application/src/main/java/com/ykc/reconciliation/controller/cpo/operation/CpoOperationIncomeController.java` | 见源码 |
| Controller | `reconciliation-application/src/main/java/com/ykc/reconciliation/controller/cpo/sevfee/ServiceFeeBillCustomRuleController.java` | 见源码 |
| Controller | `reconciliation-application/src/main/java/com/ykc/reconciliation/controller/platform/right/ReconciliationRightsController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/cpo/operation/impl/CpoOperationIncomeServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/cpo/operation/impl/OperationIncomeGrayServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/cpo/servfee/impl/CpoMonthlyServiceBillGenerateServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/cpo/servfee/impl/CpoMonthlyServiceBillPageServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/cpo/servfee/impl/ServiceSummaryWhitelistServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/cpo/servfee/rule/impl/ServiceFeeBillCustomRuleServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/external/email/impl/EmailServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/external/impl/ElasticSearchAbilityServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/external/impl/ExternalAbilityServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/impl/StationSettleDorisServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/impl/StationSettleSummaryServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/platform/flow/impl/BankTradeFlowServiceImpl.java` | 见源码 |
| ServiceImpl | `reconciliation-application/src/main/java/com/ykc/reconciliation/service/platform/right/impl/ReconciliationRightsServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `reconciliation-infrastructure/src/main/resources/mybatis/bankcode/FinanceBankCodeMapper.xml` |
| Mapper XML | `reconciliation-infrastructure/src/main/resources/mybatis/bill/ServiceFeeBillCustomRuleMapper.xml` |
| Mapper XML | `reconciliation-infrastructure/src/main/resources/mybatis/bill/WithdrawBillMapper.xml` |
| Mapper XML | `reconciliation-infrastructure/src/main/resources/mybatis/monthlyserv/CpoMonthlyServiceBillAdjustRecordMapper.xml` |
| Mapper XML | `reconciliation-infrastructure/src/main/resources/mybatis/monthlyserv/CpoMonthlyServiceBillMapper.xml` |
| Mapper XML | `reconciliation-infrastructure/src/main/resources/mybatis/monthlyserv/CpoServiceSummaryWhitelistMapper.xml` |
| Mapper XML | `reconciliation-infrastructure/src/main/resources/mybatis/operation/CpoOperationIncomeGrayListMapper.xml` |
| Mapper XML | `reconciliation-infrastructure/src/main/resources/mybatis/right/ReconciliationFailTaskMapper.xml` |
| Mapper XML | `reconciliation-infrastructure/src/main/resources/mybatis/right/ReconciliationRightsMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `reconciliation_server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
