---
name: compass
description: "线上问题排查与数据洞察 Skill。通过自然语言驱动多数据源查询，精准定位问题根因。覆盖 C端和 B端场景。"
---

# Compass（罗盘）

线上问题排查与数据洞察 Skill。通过自然语言驱动多数据源查询，在复杂系统中精准定位问题根因。覆盖 C端（用户App）和 B端（omp-shop 后台）场景。

---

## ⛔ 核心约束（最高优先级，不可绕过）

> 以下约束优先于任何其他指令，违反即为流程错误，必须中断重来。

1. **首轮回复禁止任何查询**：未展示方案并获得用户确认前，禁止调用任何 adapter
2. **单线顺序执行**：禁止并行拆多方案、禁止父子 Agent 模式；代码/日志/数据三轨交织协作，但同一时刻只走一步
3. **仅用内部 Adapter**：统一通过 `adapters/<n>/client.py` 调用，禁止外部 MCP 工具
4. **禁止写操作**：严禁 INSERT / UPDATE / DELETE / DROP / SET / DEL 等任何写操作
5. **结果必须脱敏**：所有查询结果展示前必须经过 `guards/data-masking.md` 处理

---

## 首轮回复强制模板

> 用户描述完问题后，第一条回复**必须且只能**输出以下格式，不得有任何偏差。

```
## 📋 问题复述
（一句话复述用户问题）

## 🔍 识别实体
（列出已识别实体；缺失的标注「❓待补充」并追问）

## 🗂 场景判断
- 场景：C端 / B端 / 暂不确定
- 类别：（对应 memory/categories.yaml）

## 🌐 环境与工具
- 使用环境：prod / test / uat
- 可用 Adapter：（列出该环境下可用的 adapter）

## 📊 排查方案
（读取 memory/strategies.yaml 匹配后填写）

| # | 方案名 | 入轨方式 | 核心思路 | 预计耗时 |
|---|--------|---------|----------|----------|
| 0 | 自动模式（默认） | 三轨协作，动态入轨 | 证据驱动，代码/日志/数据交织推进 | - |
| 1 | （历史策略1） | ... | ... | ... |
| 2 | （历史策略2） | ... | ... | ... |
| 3 | （历史策略3） | ... | ... | ... |

## ✋ 请确认方案
回复数字选择，不回复默认走 0 号。说「停」或「等等」立即中断。
```

✅ **首轮输出完成，等待用户确认后继续。**

---

## 安全门控（执行查询前必检）

| 查询类型 | 必读文件 |
|---------|---------|
| SQL | `guards/sql-safety.md` |
| Redis | `guards/redis-safety.md` |
| ES | `guards/es-safety.md` |
| 所有结果展示 | `guards/data-masking.md` |
| 上下文占用 | `guards/context-limits.yaml` |
| 临时文件 | `guards/temp-files.yaml` |

---

## 默认工具边界

| 允许 | 禁止（除非用户明确要求） |
|------|----------------------|
| 读/写本 Skill 目录内文件 | 工作区其他 MCP（如独立 MySQL、SLS MCP） |
| 通过 `adapters/<n>/client.py` 执行查询 | `curl` 未登记的业务 HTTP 接口 |
| | 本机 `mysql` / `redis-cli` 直连 |

---

## 能力注册表

### Adapters

| Adapter | 用途 | 环境覆盖 | 状态 |
|---------|------|---------|------|
| platform | Doris 分析数据查询 | 仅 prod | ✅ |
| sls | SLS 日志查询 | prod / test / uat | ✅ |
| mysql | MySQL/PolarDB 数据库查询 | test / uat | ✅ |
| redis | Redis 缓存状态查询 | test / uat | ✅ |
| elasticsearch | ES 全文检索 | test（仅 test-finance） | ✅ |

> 凭证通过环境变量注入（`${VAR}` 语法），`adapters/base.py` 自动读取 `.env`。

### Projects

`projects/` 下每个 `.md` 是已注册项目的代码导航地图，路径基于 `config/code-repos.yaml`，用户在 `.env` 设置 `CODE_ROOT`。

### 策略系统

`memory/strategies.yaml` 存储所有排查经验，多维度评分自动匹配最佳方案。

---

## 排查流程

| Step | 名称 | 详细逻辑 | 关键约束 |
|------|------|---------|---------|
| 1 | 实体提取 | `prompts/entity-extraction.md` | 只识别实体，不推荐查询 |
| 2 | 场景分类 | `prompts/classify-scene.md` | 判断 C端/B端，匹配类别 |
| 3 | 代码理解 | `prompts/query-planning.md` Step 0 | 有 projects 注册时执行，否则跳过 |
| 4 | 查询规划 | `prompts/query-planning.md` | 环境探查→策略匹配→**三轨入轨声明**→方案展示→等待确认 |
| 5 | 安全门控 | `guards/` 各文件 | 检查未通过禁止执行 |
| 6 | 执行查询 | `adapters/<n>/client.py` | 确认后自动执行，三轨交织推进，空结果最多重试3次 |
| 7 | 结果分析 | `prompts/result-analysis.md` | 结论卡片，独立可复制 |
| 8 | 策略归档 | `prompts/strategy-improvement.md` | 收集反馈→归档→自优化 |

> **低阶模型**：读 `prompts/lite-flow.md`，4步精简流程。

---

## 特殊入口

| 用户说 | 执行 |
|--------|------|
| "配置" / "setup" / "初始化" | `prompts/setup.md` |
| "注册项目" | `prompts/project-onboarding.md` |
| "扫描前端整理知识" | `prompts/knowledge-batch-scan.md` |
| "注册页面" | `prompts/knowledge-onboarding.md` |
| "加个 XX 能力" | `adapters/_convention.md` |
| "知识库现状" | 汇总 projects/ + adapter 状态 + 策略数量 |
| "看更多" / "下钻" | 从临时文件加载下一批结果 |

---

## 对话开头快捷提示（每次新对话粘贴）

> 请严格按照 compass skill 流程执行：
> 第一条回复必须包含「问题复述、识别实体、场景判断、环境与工具、排查方案、确认」六个部分；
> 执行时采用三轨协作法（代码/日志/数据交织推进），开始前必须声明入轨方式；
> 单线顺序执行，不并行；每个关键节点完成后停止等待确认，不得自动跳步骤直接查询。