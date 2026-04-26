# 场景分类

**职责**：判断问题属于 C端、B端、财务、订单、充电或混合场景，匹配问题类别，生成初始待验证假设，确定需要哪些能力。

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

**财务/支付/结算**：
- 描述中提到「支付」「退款」「入金」「清分」「分账」「结算」「提现」「垫资」「商户」「账户」
- 给了支付单号、清分单号、退款单号、商户 ID 等财务侧线索
- → 优先构建支付单 → 入金单 → 清分单 → 退款/垫资单 → 钱包/提现的证据链

**订单/计费**：
- 描述中提到「订单」「结算价」「价格」「退差」「计费」「金额不对」
- → 优先确认订单状态、计费明细、支付/退款状态，再决定是否进入财务链路

**充电实时链路**：
- 描述中提到「启动失败」「停止失败」「桩」「枪」「实时单」「充电中」「上报」
- → 优先确认用户、站桩枪、实时单、设备指令和充电日志

**混合场景**（C端现象由 B端配置/操作引起）：
- 描述同时包含用户侧现象（「用户充电失败」）和后台侧操作（「后台改了价格/配置」）
- 或问题链路横跨前后台（如 B端修改钱包 → C端余额不对）
- → 标记 `scene: mixed`，在查询规划阶段同时准备 B端追溯链和 C端数据查询两条路径
- → 排查方案中拆为**方案 A（B端配置/操作侧）**和**方案 B（C端数据/日志侧）**供用户选择

## 问题类别匹配

1. 读取 `memory/categories.yaml`，按关键字匹配
2. 找到匹配 → 使用已有类别（便于关联历史策略）
3. 多个类别都匹配（关键字命中率相近）→ 列出候选类别，让用户确认或选择
4. 未找到 → 创建新类别描述（排查结束后写入 categories.yaml）

## 初始假设规则

- 最多输出 3 个假设，全部标记为 `待验证`。
- 每个假设必须写明“需要验证的证据”。
- 不允许把经验判断写成结论。
- 若缺少最小定位实体，只能输出粗粒度假设，并提示补实体后再验证。

## 输出格式（结构化，供 query-planning.md 接收）

```yaml
classification:
  scene: "c-side"              # c-side | b-side | finance | order | charging | mixed | unknown
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
  initial_hypotheses:
    - id: "H1"
      statement: "支付成功事件未推进订单状态"
      needed_evidence:
        - "支付单状态"
        - "订单状态流转日志"
      status: "待验证"
```

**交接规则**：此输出传递给 `query-planning.md`（Step 4），其中：
- `scene` 决定是否执行 B端三层追溯
- `category` 用于策略匹配的类别维度
- `required_capabilities` 是初步建议，Step 4 环境探查后可能裁剪
- `involved_services` 用于 Step 3 读取 `projects/<service>.md`
- `user_role` 决定方案展示深度
