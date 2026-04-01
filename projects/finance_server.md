# finance_server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/FINANCE/finance_server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `finance_server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `finance_server/src/main/java/com/ykc/controller/BackstageRechargeOrRefundController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/BankAccountFlowController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/CmbBusinessController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/FinanceErrorController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/FinanceThirdPayInfoController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/FlowSideController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/FundPoolManagementController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/IdGeneratorController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/ManualClearingOrderController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/OnlineRechargeOrRefundController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/OperatorFinanceController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/OrderFinanceController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/OrionSharingFlowController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/PayChannelConfigController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/ReserveCouponRecordController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/SaasSharingFlowController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/ServiceFeeWithdrawController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/ThirdOrderController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/UserAnonymousBankAccountController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/UserChargeFlowController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/UserFlowController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/UserOnlineRechargeController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/UserOnlineRefundController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/UserWalletHandleController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/VehicleAgencyFinanceController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/VehicleAndUserFinanceController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/YkcSharingWithdrawController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/account/AnonymousAccountSupportController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/accountsubject/AccountSubjectCompanyController.java` | 见源码 |
| Controller | `finance_server/src/main/java/com/ykc/controller/accountsubject/AccountSubjectConfigController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/OperatorMaintainFeignServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/AccountFeignApiServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/ActivityFeignApiServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/BizBlackWhiteListFeignServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/CpoFundAdjustAbilityServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/DistrictFeignApiServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/EmasPushFeignApiServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/InvoiceCredentialApiServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/InvoiceRecipientInfoApiServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/InvoiceTitleApiServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/OrderFeignServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/PaymentPayApiServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/PaymentSettlementServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/UserInvoiceResourceFeignServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/VehicleOrganizationServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/feign/service/impl/ZdlFeignApiServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/payment/service/impl/PaymentChannelServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/payment/service/impl/PaymentPayServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/payment/service/impl/PaymentPreOrderServiceImpl.java` | 见源码 |
| ServiceImpl | `finance_server/src/main/java/com/ykc/payment/service/impl/RefundServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `finance_server/src/main/resources/mybatis/account/AnonymousMbrMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/account/BankAccountMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/accountsubject/AccountSubjectCompanyMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/accountsubject/AccountSubjectConfigMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/accountsubject/AccountSubjectLinkStationMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/accountsubject/AccountSubjectQuotaChangeFlowMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/accountsubject/AccountSubjectQuotaMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/accountsubject/PlatFormSubjectCompanyMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/accountsubject/SpecialSubjectMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/advance/BizRefundAdvanceBillMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/alarm/AlarmMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/alarm/AlarmNotifyMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/backstage/RechargeMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/bankAccount/FinanceDTUserAnonymousBankAccountTaskMapper.xml` |
| Mapper XML | `finance_server/src/main/resources/mybatis/bankAccount/UserAnonymousBankAccountFailRecordMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `finance_server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
