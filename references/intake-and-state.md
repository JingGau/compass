# Intake And State Reference

## Problem Intake

首轮只做结构化和方案确认，不调用 adapter。缺少最小定位实体时暂停追问。

默认环境规则：

- 排查默认使用线上环境 `prod`。
- 只有用户明确说 `test`、`uat`、`测试环境`、`预发` 等非线上环境时，才切换环境。
- Agent 不得因为安全、方便或猜测而自行改用 test/uat。

| 场景 | 最小定位实体 | 常见补充实体 |
|------|--------------|--------------|
| C端充电 | user_id/手机号/订单号 三选一 + 时间范围 | 站 ID、桩 ID、枪号、支付单号、异常文案 |
| B端后台 | 页面/功能 + 操作对象 + 时间范围 | org_id、operator_id、请求参数、截图文案 |
| 支付/财务 | 支付单号/订单号/用户ID 三选一 + 时间范围 | 商户 ID、渠道流水、清分单号、退款单号 |
| 订单/计费 | 订单号/用户ID + 时间范围 | 结算价、支付方式、退款状态、业务类型 |
| 日志异常 | 服务名 + 时间范围 + 异常现象 | traceId、tlogId、接口、关键字 |

首轮必须提取：原始问题、标准化问题、识别实体、缺失实体、场景类别、最多 3 个候选排查方向、首步策略。

缺失规则：

- 缺少最小定位实体：追问订单号 / 用户ID / 手机号 / 时间范围中最容易获得的一项。
- 缺少时间范围：不得自行扩大查询，只能建议最近 30 分钟 / 1 小时 / 当天供用户确认。
- 用户只描述现象但无对象：先追问对象，不泛查。

## 首轮回复模板

```text
## 问题复述
（一句话复述用户问题）

## Problem Intake
- 原始问题：___
- 标准化问题：___
- 影响范围：单用户 / 多用户 / 单订单 / 批量 / 未知

## 识别实体
| 实体 | 值 | 来源 | 置信度 |
|------|----|------|--------|

## 缺失实体
| 缺失项 | 是否阻断 | 可替代信息 | 追问 |
|--------|----------|------------|------|

## 场景判断
- 场景：C端 / B端 / 财务 / 订单 / 充电 / 暂不确定
- 类别：（对应 memory/categories.yaml）

## 候选排查方向（非正式假设）
| # | 方向 | 可能需要的证据 |
|---|------|----------------|

这些方向只用于帮助选择第一批证据动作，不写入正式 `hypotheses`。正式假设必须在 `scene fact` / `evidence` / `change` 之后通过 `hypothesis add` 创建。

## 环境与工具
- 使用环境：prod（默认）/ test / uat；未明确指定时填 prod
- 可用 Adapter：___

## 请确认
首轮只需要确认是否开始排查；确认后执行 `compass confirm`，后续由 `next --json.task` 决定下一步。缺失实体阻断时先补充信息；用户随时可以说“停/等等/暂停”打断。
```

## Investigation State

状态必须由 CLI/Core 维护。概念结构如下：

```yaml
problem:
  scene: C端/B端/财务/订单/充电/暂不确定
  environment: prod/test/uat
  symptom: 用户可见现象或业务异常
  impact: 单用户/多用户/单订单/批量/未知
entities:
  user_id: 已知或 null
  order_no: 已知或 null
  pay_no: 已知或 null
  time_range: 已知或 null
environment: prod/test/uat
evidence:
  - id: E1
    source: SQL/SLS/代码/Redis/ES/用户补充
    summary: 证据摘要
    kind: manual/user/log/sql/code/kb/inference
    strength: weak/medium/strong
    raw_ref: traceId/SQL/代码位置/知识库路径
    supports: H1
hypotheses:
  - id: H1
    statement: 待验证假设
    status: 待验证/支持/排除
    source_facts: [scene_fact_name]
    source_evidence: [E1]
investigation_hints:
  - id: D1
    type: candidate_direction
    statement: 候选排查方向，不是正式假设
    status: reference_only
scene_facts:
  - category: entrypoint/object/upstream/downstream/config/variant
    name: 可引用名称
    value: 事实值
    source: 用户补充/SLS/代码/SQL/KB
    evidence: [E1]
action_plan:
  - action_id: A1
    track: sls/sql/code/kb/manual
    objective: 本次动作要验证什么
    success_criteria: 什么结果算验证成功
    status: planned/completed
action_history:
  - action_id: A1
    track: sls/sql/code/kb/manual
    input: 查询输入或检索条件
    gate: 安全门控结果
    output: 摘要、发现、线索、证据 ID
revision: 1
conclusion_history:
  - revision: 1
    status: superseded
    summary: 被修订的旧结论
    reopen_reason: 重开原因
ruled_out: []
next_actions: []
```

## Evidence Chain

证据充足时：

```text
结论：___
可信度：高/中/低
证据：
1. [E1][SQL/表名或日志来源] ___
待验证：
- ___
下一步：
- ___
```

证据不足时必须降级：

```text
待验证假设：___
已有线索：___
缺失证据：___
建议下一步：___
```
