# bank_ability_center

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `/Users/dongmaowei/workspace/projects/FINANCE/bank_ability_center` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `bank_ability_center`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| Controller | `src/main/java/com/ykc/controller/IncomingPartsController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/account/AccountController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/back/CmbTradeCallbackEntryController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/cashOut/CashOutController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/injection/BankMchtRpcController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/injection/InjectionController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/open/BankAlipayPayafteruseOpenController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/pay/BankAlipayPayafteruseRpcController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/pay/UnifiedPayController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/pay/WxPayScoreController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/register/RegisterController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/risk/BankMchtRiskRpcController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/trade/IndependentAccountController.java` | 见源码 |
| Controller | `src/main/java/com/ykc/controller/trade/download/BankTradeDownloadRpcController.java` | 见源码 |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `src/main/java/com/ykc/service/account/impl/AccountServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/cashOut/impl/CashOutServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/http/impl/IncomingHttpServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/http/impl/PayHttpServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/http/impl/PljhrmsHttpServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/http/impl/TradeNTSHttpServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/http/impl/WxPayScoreHttpServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/incoming/impl/MerchantServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/injection/impl/InjectionServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/notify/impl/CmbTradeCallbackNotifyServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/pay/impl/UnifiedPayServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/pay/impl/WxPayScoreServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/register/impl/RegisterBusinessServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/risk/impl/MchtRiskServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/trade/impl/IndependentAccountServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/trade/impl/TradeDownloadServiceImpl.java` | 见源码 |
| ServiceImpl | `src/main/java/com/ykc/service/trade/impl/TradeServiceImpl.java` | 见源码 |


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
| 通用 | `bank_ability_center`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
