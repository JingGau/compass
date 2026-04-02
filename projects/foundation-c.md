# foundation-c

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | Java 后端（扫描：Java/Maven） |
| 代码根路径 | `omp/foundation-c` |
| SLS 容器名 | 待从部署或 `application*.yml` 的 `spring.application.name` 核对 |
| 关联数据库 | 待从配置核对 |
| 所属端 | B端+C端（视接口而定） |
| 一句话职责 | 本地仓库 `foundation-c`，路径由磁盘扫描得到 |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 说明 |
|--------|-----------------------------|------|
| （本仓库未扫到 Controller） | — |


### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|-----------------------------|------|
| ServiceImpl | `foundation-c-service/src/main/java/com/ykc/foundationc/device/service/impl/ChargingGunQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-c-service/src/main/java/com/ykc/foundationc/device/service/impl/ChargingPileQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-c-service/src/main/java/com/ykc/foundationc/device/service/impl/ChargingStationQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-c-service/src/main/java/com/ykc/foundationc/operator/service/impl/OperatorQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-c-service/src/main/java/com/ykc/foundationc/organization/service/impl/OrganizationQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-c-service/src/main/java/com/ykc/foundationc/system/service/impl/DistrictQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-c-service/src/main/java/com/ykc/foundationc/user/service/impl/AlipayServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-c-service/src/main/java/com/ykc/foundationc/user/service/impl/ChargingUserQueryServiceImpl.java` | 见源码 |
| ServiceImpl | `foundation-c-service/src/main/java/com/ykc/foundationc/user/service/impl/WechatServiceImpl.java` | 见源码 |


### 数据层（Mapper XML 抽样）
| 配置/Mapper | 路径 |
|---------------|------|
| Mapper XML | `foundation-c-service/src/main/resources/com/ykc/foundationc/device/infrastructure/repository/mysql/ChargingGunMapper.xml` |
| Mapper XML | `foundation-c-service/src/main/resources/com/ykc/foundationc/device/infrastructure/repository/mysql/ChargingPileMapper.xml` |
| Mapper XML | `foundation-c-service/src/main/resources/com/ykc/foundationc/device/infrastructure/repository/mysql/ChargingStationMapper.xml` |
| Mapper XML | `foundation-c-service/src/main/resources/com/ykc/foundationc/operator/infrastructure/repository/mysql/OperatorMapper.xml` |
| Mapper XML | `foundation-c-service/src/main/resources/com/ykc/foundationc/organization/infrastructure/repository/mysql/OrganizationMapper.xml` |
| Mapper XML | `foundation-c-service/src/main/resources/com/ykc/foundationc/system/infrastructure/repository/mysql/DistrictMapper.xml` |
| Mapper XML | `foundation-c-service/src/main/resources/com/ykc/foundationc/user/infrastructure/repository/mysql/ChargingUserMapper.xml` |


## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| 接口/HTTP 问题 | 先打开上表 Controller，再跟到 ServiceImpl | sls + mysql |
| 落库/配置 | Mapper XML + 对应 Entity | mysql |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| 通用 | `foundation-c`、ERROR、traceId |

## 元信息
- generated_at: 2026-03-28
- generated_by: filesystem scan (workspace/projects)
- last_verified: 2026-03-28
- source: structure-scan-no-yaml
