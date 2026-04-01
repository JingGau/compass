# invoice-server

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/FINANCE/invoice-server` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `invoice-server`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| （本仓库未扫到 Controller） | — |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/activity/service/impl/CpoInvoiceServiceActivityServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/credential/service/impl/CpoCredentialHistoryServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/credential/service/impl/CpoCredentialSearchServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/credential/service/impl/CpoCredentialServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/credential/service/impl/CpoCredentialStateSearchServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/credential/service/impl/CpoCredentialTodoServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/doris/service/impl/DorisServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/equity/service/impl/CpoCredentialEquityAdjustServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/equity/service/impl/CpoCredentialEquitySearchServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/equity/service/impl/CpoCredentialEquityServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/baiwang/impl/BaiWangAuthServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/baiwang/impl/BaiWangCloudTitleServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/baiwang/impl/BaiWangFeignServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/baiwang/impl/BaiWangInvoiceEmailServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/baiwang/impl/BaiWangInvoicingServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/baiwang/impl/BaiWangLoginServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/baiwang/impl/BaiWangOpenInvoiceJobServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/baiwang/impl/BaiWangOrderServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/cinvoice/impl/InvoiceRecipientInfoServiceImpl.java` | 见源码 |
| ServiceImpl | `invoice-server-service/src/main/java/com/ykc/invoice/invoice/service/cinvoice/impl/InvoiceTitleServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/CpoApplyRecordMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/CpoApplyRecordRelationMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/CpoInvoiceInfoMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/CpoMonthlyServiceInvoiceBillMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/CpoServiceFeeApplyBlackMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/DateBillMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/DateBillOrderRelMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/HisInvoiceAdjustMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/IncomeInvoiceWrongCodeMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/InvoiceRecipientInfoMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/InvoiceTitleMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/MonthBillAdjustMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/MonthBillMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/MonthBillStationRelMapper.xml` |
| Mapper XML | `invoice-server-service/src/main/resources/repository/mysql/OperatorConfigMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `invoice-server`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
