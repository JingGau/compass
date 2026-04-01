# 策略归档与自我优化

**职责**：排查结束后，将本次经验写入策略库，**自动**维护策略生命周期（合并/淘汰/进化），不打扰用户。

## 一、收集用户反馈

```
这次排查有帮助吗？
  A. 有帮助，快速定位了问题 (rating: 5)
  B. 部分帮助，找到了线索但未完全定位 (rating: 3)
  C. 没帮助，方向不对 (rating: 1)
  D. 跳过
```

## 二、策略归档

### 2.1 使用了历史策略

**有帮助（A/B）**：
- `usage_count` +1
- `last_used` 更新为当前日期
- `user_ratings` 追加评分
- `effectiveness` 重新计算：`avg(user_ratings) / 5`
- `avg_rounds` 更新：加权平均（新值权重 0.3，旧值权重 0.7）
- 如果用户微调了步骤 → `modification_count` +1

**没帮助（C）**：
- `usage_count` +1
- `user_ratings` 追加 1
- `effectiveness` 重新计算

**跳过（D）**：
- `usage_count` +1（确实使用了该策略）
- `last_used` 更新为当前日期
- `user_ratings` **不追加**（无评分数据）
- `effectiveness` **不重新计算**（保持上一次的值）
- `modification_count` 正常更新（如果用户微调了步骤）
- 仍然执行后续的策略归档和生命周期管理

### 2.2 全新排查路径

当没有匹配到历史策略、AI 从零规划的查询路径成功定位问题时：

```
Step 1: 提取本次排查的 pattern
  - category / keywords / entity_types / services / scene

Step 2: 记录 plan
  - 按实际执行的查询步骤记录
  - 标注 adapter、action、template、source
  - 记录实际使用的环境/profile

Step 3: 初始化 score
  - effectiveness: 根据用户反馈（A→1.0, B→0.6, C→0.2）
  - usage_count: 1
  - user_ratings: [rating]
  - modification_count: 0

Step 4: 设置 meta
  - created_from: "first_use"
  - related_projects: 本次排查中读取的 projects/*.md 列表
  - pinned: false

Step 5: 写入 strategies.yaml 的 strategies 列表
  - id 格式: "stg_{timestamp}"

Step 6: 简短通知
  "已归档为新策略「{category}」。"
```

### 2.3 预设策略首次使用

预设策略 (`presets` 列表) 被首次使用时：
- 复制到 `strategies` 列表
- 更新 score 和 meta
- 保留 `presets` 中的原始记录不变（作为基准）

## 三、策略生命周期管理（全自动）

策略库的维护**完全由 AI 自动执行**，不需要用户逐条决策。只在执行完成后以简报形式通知。

### 3.1 保护规则（不可触碰的策略）

以下策略**绝不会被合并或淘汰**：

| 保护条件 | 说明 |
|---------|------|
| `pinned: true` | 用户手动标记为「保留」的策略 |
| 最近 5 次排查使用过 | 活跃策略不应被打扰 |
| `presets` 中的原始策略 | 预设策略永远保留作为基准 |

用户标记 `pinned` 的方式：排查中说"保留这个策略"或"标记不可删除"。

### 3.2 自动合并

**触发条件**：同一 `category` 下策略数超过 `limits.max_per_category`（5个）

**自动操作**：
1. 排除受保护的策略
2. 在剩余策略中找到 plan 高度相似的（步骤重合 >= 70%）
3. 合并为一个综合策略：`plan` 取效果最好的路径，`score` 取加权平均
4. 旧策略移入 `memory/archived-strategies.yaml`
5. 新策略 `created_from: "merged"`

**归档后通知**（简报，不询问）：
```
[策略维护] 自动合并了「钱包-余额异常」下 3 个相似策略 → 保留最佳路径。
已归档: stg_008, stg_015。如需恢复，查看 memory/archived-strategies.yaml。
```

### 3.3 自动淘汰

**触发条件**：策略总数超过 `limits.max_total`（50个）

**淘汰候选**（排除受保护策略后，符合任一条件）：
- `effectiveness` < `limits.min_effectiveness`（0.3）
- 超过 `limits.stale_days`（180天）未使用
- `usage_count` <= 1 且 `effectiveness` < 0.5

**自动操作**：
1. 按淘汰优先级排序（低效 > 过期 > 低频）
2. 淘汰足够数量使总数回到上限以下
3. 移入 `memory/archived-strategies.yaml`

**淘汰后通知**：
```
[策略维护] 自动归档了 3 个低效/过期策略。当前策略库: 48/50。
如需恢复某个策略，查看 memory/archived-strategies.yaml。
```

### 3.4 自动进化

**触发条件**：某策略的 `modification_count` >= `limits.evolution_trigger`（3次）

**自动操作**：
1. 用最近一次成功排查的实际执行路径覆盖 `plan`
2. `modification_count` 重置为 0
3. `last_updated` 更新
4. `created_from` 追加 "optimized"

**进化后通知**：
```
[策略进化] 「钱包-余额异常」策略已根据最近 3 次微调自动优化。
```

## 四、辅助更新

### 4.1 更新问题分类（memory/categories.yaml）
- 新问题类别 → 追加写入
- 已有类别 → `frequency` +1

### 4.2 写入审计日志（memory/audit-log.yaml）
每次执行过的查询记录一条，含 adapter、环境/profile、SQL/关键字、行数、耗时。

### 4.3 知识缺口提醒
如果排查过程中记录了知识缺口（涉及某服务但 `projects/` 中无对应文件）：
```
本次排查涉及 charge_server，但尚未注册到知识库。
注册后可读代码辅助排查。是否现在注册？
```

### 4.4 清理临时文件
如果排查过程中生成了临时文件（大结果集），在此步骤清理。

## 五、自动压缩检查

每次归档后 AI 自动检查并执行（不需要用户参与）：
- 策略总数 > `limits.max_total` → 自动淘汰（3.3）
- 同 category 策略数 > `limits.max_per_category` → 自动合并（3.2）
- 策略 `modification_count` >= `limits.evolution_trigger` → 自动进化（3.4）
- `audit-log.yaml` 超过 500 条 → 自动归档 30 天前的记录

所有自动操作的结果以简报通知用户，不中断排查流程。
