# 策略归档与自我优化

**职责**：排查结束后，将本次经验写入策略库，自动维护策略生命周期（合并/淘汰/进化），不打扰用户。

> 本步骤全自动执行，只在关键节点以简报通知用户，不询问、不中断流程。

---

## 一、收集用户反馈

```
这次排查有帮助吗？
  A. 有帮助，快速定位了问题       (rating: 5)
  B. 部分帮助，找到线索但未完全定位 (rating: 3)
  C. 没帮助，方向不对             (rating: 1)
  D. 跳过
```

---

## 二、策略归档

### 2.1 使用了历史策略

| 用户反馈 | 执行操作 |
|---------|---------|
| A / B（有帮助） | `usage_count` +1；`last_used` 更新；`user_ratings` 追加；`effectiveness` 重算（avg/5）；`avg_rounds` 加权更新（新值×0.3 + 旧值×0.7）；用户微调了步骤则 `modification_count` +1 |
| C（没帮助） | `usage_count` +1；`user_ratings` 追加 1；`effectiveness` 重算 |
| D（跳过） | `usage_count` +1；`last_used` 更新；`user_ratings` 不追加；`effectiveness` 不重算；`modification_count` 正常更新 |

> 跳过不影响后续生命周期管理，仍正常执行合并/淘汰/进化检查。

---

### 2.2 全新排查路径

当没有命中历史策略、AI 从零规划且成功定位问题时，执行以下归档：

```
Step 1：提取 pattern
  - category / keywords / entity_types / services / scene

Step 2：记录 plan
  - 按实际执行的查询步骤记录
  - 标注 adapter、action、template、source、环境/profile

Step 3：初始化 score
  - effectiveness: A→1.0 / B→0.6 / C→0.2
  - usage_count: 1
  - user_ratings: [rating]
  - modification_count: 0

Step 4：设置 meta
  - created_from: "first_use"
  - related_projects: 本次读取的 projects/*.md 列表
  - pinned: false

Step 5：写入 strategies.yaml
  - id 格式: "stg_{timestamp}"

Step 6：简报通知
  「已归档为新策略「{category}」。」
```

---

### 2.3 预设策略首次使用

- 将 `presets` 中的策略复制到 `strategies` 列表
- 更新 score 和 meta
- `presets` 中原始记录保留不变（作为基准，不可修改）

---

## 三、策略生命周期管理（全自动）

> AI 自动执行，完成后以简报通知，不询问用户、不中断流程。

### 3.1 保护规则（以下策略不参与合并/淘汰）

| 保护条件 | 说明 |
|---------|------|
| `pinned: true` | 用户手动标记保留 |
| 最近 5 次排查使用过 | 活跃策略不干扰 |
| `presets` 中的原始策略 | 永久保留作为基准 |

> 用户标记方式：排查中说「保留这个策略」或「标记不可删除」。

---

### 3.2 自动合并

**触发**：同一 `category` 下策略数超过 `limits.max_per_category`（默认 5）

**操作**：
1. 排除受保护策略
2. 找到 plan 步骤重合 ≥ 70% 的相似策略
3. 合并：`plan` 取效果最好的路径，`score` 取加权平均
4. 旧策略移入 `memory/archived-strategies.yaml`
5. 新策略标记 `created_from: "merged"`

**简报通知**：
```
[策略维护] 自动合并「{category}」下 {n} 个相似策略 → 保留最佳路径。
已归档: {id列表}。如需恢复，查看 memory/archived-strategies.yaml。
```

---

### 3.3 自动淘汰

**触发**：策略总数超过 `limits.max_total`（默认 50）

**淘汰候选**（排除受保护策略，符合任一条件）：

| 条件 | 阈值 |
|------|------|
| effectiveness 过低 | < `limits.min_effectiveness`（0.3） |
| 长期未使用 | 超过 `limits.stale_days`（180天） |
| 低频且低效 | `usage_count` ≤ 1 且 effectiveness < 0.5 |

**操作**：按优先级排序（低效 > 过期 > 低频），淘汰至总数回到上限以下，移入 `memory/archived-strategies.yaml`

**简报通知**：
```
[策略维护] 自动归档了 {n} 个低效/过期策略。当前策略库: {当前数}/{上限}。
如需恢复，查看 memory/archived-strategies.yaml。
```

---

### 3.4 自动进化

**触发**：某策略 `modification_count` ≥ `limits.evolution_trigger`（默认 3）

**操作**：
1. 用最近一次成功排查的实际路径覆盖 `plan`
2. `modification_count` 重置为 0
3. `last_updated` 更新
4. `created_from` 追加 "optimized"

**简报通知**：
```
[策略进化] 「{策略名}」已根据最近 {n} 次微调自动优化。
```

---

## 四、辅助更新

| 操作 | 说明 |
|------|------|
| 更新问题分类 | 新类别追加到 `memory/categories.yaml`；已有类别 `frequency` +1 |
| 写入审计日志 | 每次查询记录一条到 `memory/audit-log.yaml`，含 adapter、环境/profile、SQL/关键字、行数、耗时 |
| 知识缺口提醒 | 排查涉及未注册服务时提示「{服务名} 尚未注册到知识库，是否现在注册？」 |
| 清理临时文件 | 清理本次排查生成的大结果集临时文件 |

---

## 五、自动压缩检查（归档后自动触发）

每次归档完成后，AI 自动检查以下条件并执行，无需用户参与：

| 检查条件 | 自动执行 |
|---------|---------|
| 策略总数 > `limits.max_total` | 自动淘汰（→ 3.3） |
| 同 category 策略数 > `limits.max_per_category` | 自动合并（→ 3.2） |
| 某策略 `modification_count` ≥ `limits.evolution_trigger` | 自动进化（→ 3.4） |
| `audit-log.yaml` 超过 500 条 | 自动归档 30 天前的记录 |

所有操作结果以简报通知用户，不中断排查流程。