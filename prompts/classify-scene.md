# 场景分类

**职责**：判断问题属于 C端还是 B端，匹配问题类别，确定需要哪些能力。

> **本阶段只做分类与能力方向判断，禁止执行查询。** 具体用哪些 adapter、哪套策略，必须在读完 `strategies.yaml` 并展示方案后，经用户确认再执行。

## 判断逻辑

**B端**（omp-shop 商户管理后台）：
- 描述中提到「后台」「管理页面」「omp」「商户」「运营」
- 问题是「页面不显示」「列表空了」「功能按钮灰了」
- → 读取 `knowledge/b-side/` 走三层追溯链

**C端**（用户 App）：
- 描述中提到「用户」「App」「充电」「扫码」「支付」「余额」
- 给了手机号、订单号等用户侧线索
- → C 端请求经 `guan-zhong` 网关进入后端，代码理解阶段优先读 `projects/guan-zhong.md`
- → 直接构建数据+日志查询

**无法判断**：
- 问用户：「这个问题是在 App 端还是后台管理端？」

**混合场景**（C端现象由 B端配置/操作引起）：
- 描述同时包含用户侧现象（「用户充电失败」）和后台侧操作（「后台改了价格/配置」）
- 或问题链路横跨前后台（如 B端修改钱包 → C端余额不对）
- → 标记 `scene: mixed`，在查询规划阶段同时准备 B端追溯链和 C端数据查询两条路径
- → 排查方案中拆为**方案 A（B端配置/操作侧）**和**方案 B（C端���据/日���侧）**供用户选择

## 问题类别匹配

1. 读取 `memory/categories.yaml`，按关键字匹配
2. 找到匹配 → 使用已有类别（便于关联历史策略）
3. 多个类别都匹配（关键字命中率相近）→ 列出候选类别，让用户确认或选择
4. 未找到 → 创建新类别描述（排查结束后写入 categories.yaml）

## 输出格式（结构化，供 query-planning.md 接收）

```yaml
classification:
  scene: "c-side"              # c-side | b-side | mixed | unknown
  category:
    id: "cat-001"              # 匹配到的类别 ID，新类别为 null
    name: "充电订单-支付失败"     # 类别名称
    match_source: "matched"    # matched | new | ambiguous
  required_capabilities:       # 初步判断需要的 adapter 列表（query-planning 阶段会根据环境探查修正）
    - adapter: "platform"
      reason: "查订单数据"
    - adapter: "sls"
      reason: "查错误日志"
  involved_services:           # 初步判断涉及的服务（用于 Step 3 代码理解）
    - "order-server"
    - "payment-server"
  user_role: "technical"       # technical | business（基于实体提取阶段的信号判断）
```

**交接规则**：此输出传递给 `query-planning.md`（Step 4），其中：
- `scene` 决定是否执行 B端三层追溯
- `category` 用于策略匹配的类别维度
- `required_capabilities` 是初步建议，Step 4 环境探查后可能裁剪
- `involved_services` 用于 Step 3 读取 `projects/<service>.md`
- `user_role` 决定方案展示深度
