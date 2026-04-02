# C端知识库生成规范

## 生成方式

AI 扫描后端代码（guan-zhong 网关 + charge-server + order-server）结合业务文档生成。
触发：用户说「扫描 C端知识」，AI 读 `prompts/knowledge-onboarding.md` 执行。

## 目录结构

```
knowledge/c-side/
├── _convention.md           ← 本文件（生成规范）
├── charge-flows.yaml        ← 充电业务流程（扫码→启动→充电→结束→支付）
├── api-log-keywords.yaml    ← C端接口到 SLS 日志关键字的映射
└── user-journey.yaml        ← 用户旅程（关键页面 + 调用的后端接口）
```

## 文件格式

### charge-flows.yaml — 充电业务流程

```yaml
flows:
  - id: "flow-id"                  # 唯一标识，kebab-case
    name: "流程名称"                # 如：扫码充电、充满自停
    steps:                          # 有序步骤
      - seq: 1
        action: "扫码"              # 用户动作
        entry: "guan-zhong"         # 入口服务
        api: "POST /xxx/scan"       # 调用接口
        description: "扫码识别充电桩"
    source_project: "charge-server" # 核心服务
    generated_at: "2026-04-01"
```

### api-log-keywords.yaml — 接口到日志关键字

格式与 B端一致：

```yaml
keywords:
  - api_path: "/charge/start"
    container: "charge-server"
    sls_keywords: ["startCharge", "chargeStart"]
    error_keywords: ["ChargeStartFail", "PileOffline"]
```

### user-journey.yaml — 用户旅程

```yaml
journey:
  - id: "journey-id"
    name: "旅程名称"                # 如：首次充电、扫码充电
    pages:                          # App 页面流转
      - seq: 1
        page: "扫码页"
        actions: ["扫描二维码"]
        apis:
          - method: "GET"
            path: "/pile/info"
            service: "guan-zhong"
    generated_at: "2026-04-01"
```

## 生成规则

1. **流程梳理**：从 guan-zhong 网关 Controller 入口追踪调用链
2. **接口提取**：扫描 charge-server、order-server 的 Controller 层
3. **日志关键字**：扫描 Service 层的 `log.info`/`log.error`（需 projects/*.md 已注册）
4. **用户旅程**：基于接口调用顺序推断 App 页面流转
5. **无前端代码**：C端排查依赖日志和数据库，不依赖前端代码扫描
6. **每条记录标明来源**：`generated_at` + `source_project`

## 核心服务

| 服务 | 职责 | C端角色 |
|------|------|---------|
| guan-zhong | APP 网关 | 请求路由、协议转换 |
| charge-server | 充电控制 | 启动/停止充电、桩通信 |
| order-server | 订单管理 | 订单生命周期 |
| finance_server | 财务 | 支付、退款、钱包 |
| payment-server | 支付渠道 | 第三方支付对接 |

## 更新触发

- 用户说「扫描 C端知识」→ 全量扫描后端代码，重新生成
- 排查中发现新流程 → 手动追加到对应文件
- 后端接口变更 → 影响对应 flow 和 keywords
