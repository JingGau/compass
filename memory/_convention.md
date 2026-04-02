# 记忆系统生成规范

## 定位

记忆 = 用户个人积累的排查经验，与知识库（通用领域事实）互补：
- **知识库**（knowledge/）：通用、可共享的业务事实（页面、接口、流程）
- **记忆**（memory/）：个人积累的排查策略、分类经验、决策偏好

## 目录结构

```
memory/
├── _convention.md              ← 本文件（生成规范）
├── categories.yaml             ← 问题分类库（AI 场景匹配用）
├── confirmations.yaml          ← 用户通用决策（避免重复询问）
├── strategies.yaml             ← 活跃策略（当前有效）
├── archived-strategies.yaml    ← 归档策略（低效/过时）
├── audit-log.yaml              ← 审计日志（脱敏记录，不入库）
└── audit-archive/              ← 审计归档目录
```

## 文件格式

### categories.yaml — 问题分类库

```yaml
categories:
  - id: "cat-xxx"                     # 唯一标识
    name: "分类名称"                   # 中文
    keywords: ["kw1", "kw2"]          # 匹配关键词
    scene: "c-side / b-side / both"   # 适用端
    primary_services: ["svc1"]        # 主要后端服务
    frequency: 0                      # 累计匹配次数（自动更新）
```

### strategies.yaml — 排查策略

每条策略四部分：

```yaml
strategies:
  - id: "strategy_xxx_YYYYMMDD"
    pattern:                           # 1. 什么问题（匹配用）
      category: "cat-xxx"
      keywords: ["kw1"]
      entity_types: ["user_id"]
      services: ["svc1"]
      scene: "c-side"
    plan:                              # 2. 怎么查（查询路径）
      - step: 1
        adapter: "sls / mysql / redis / platform"
        action: "一句话说明"
        template: "查询模板含 {entity} 占位符"
        env_profile: "prod / test"
        source: "代码来源（如有）"
    score:                             # 3. 效果（排序用）
      effectiveness: 0.0              # 成功率 0.0~1.0
      usage_count: 0
      last_used: null
      avg_rounds: null
      user_ratings: []
      modification_count: 0
    meta:                              # 4. 来源信息
      created_at: "2026-04-01"
      created_from: "first_use / merged / optimized / preset"
      last_updated: "2026-04-01"
      related_projects: ["proj1"]
      pinned: false
```

### confirmations.yaml — 用户决策

```yaml
confirmations:
  - id: "conf-xxx"
    question: "什么情况下问的"
    answer: "用户的选择"
    created_at: "2026-04-01"
```

## 管理阈值

| 规则 | 阈值 | 动作 |
|------|------|------|
| 同分类策略数 > 5 | 自动提醒 | 合并同类策略 |
| 策略总数 > 50 | 自动提醒 | 淘汰低效策略 |
| effectiveness < 0.3 | 自动提醒 | 归档到 archived-strategies.yaml |
| 180 天未使用 | 自动提醒 | 建议归档 |
| 微调次数 ≥ 3 | 触发进化 | 自动优化策略 |

## 匹配权重

```yaml
matching_weights:
  category: 0.30       # 问题分类匹配度
  keywords: 0.20       # 关键字命中率
  entity_types: 0.10   # 实体类型覆盖度
  services: 0.15       # 涉及服务匹配度
  effectiveness: 0.15  # 历史成功率
  recency: 0.10        # 时间衰减因子
```

## 生成方式

- **categories.yaml**：首次 setup 时预置通用分类，排查过程中自动更新 frequency
- **strategies.yaml**：首次 setup 预置 seed 策略（effectiveness=0），每次成功排查后自动沉淀
- **confirmations.yaml**：排查过程中发现用户偏好时记录，用户说「重置决策」可清除
- **audit-log.yaml**：每次查询自动追加脱敏记录，定期归档到 audit-archive/

## 0号策略（自动模式）

定义在 `prompts/query-planning.md` 中，是执行原则而非正式策略：
- 不依赖 strategies.yaml 的匹配
- AI 基于全部上下文（问题 + 知识库 + 代码）直接规划查询路径
- 每次排查默认使用，策略匹配作为补充参考
