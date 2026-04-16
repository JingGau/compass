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
3. **内部 Adapter 优先**：统一通过 `adapters/<n>/client.py` 调用；JDBC 等外部库须经用户确认后方可调用，禁止静默使用
4. **禁止写操作**：严禁 INSERT / UPDATE / DELETE / DROP / SET / DEL 等任何写操作
5. **结果必须脱敏**：所有查询结果展示前必须经过 `guards/data-masking.md` 处理
6. **线上 SQL 必须先 EXPLAIN**：prod 环境任何 SQL 执行前必须先运行 EXPLAIN，危险查询须用户确认后才能执行（见「SQL 安全门控」）

---

## 执行模式说明

用户在首轮确认方案时同时选择执行模式：

| 模式 | 编号 | 行为 |
|------|------|------|
| 自动模式（默认） | 0 | 方案确认后全自动跑完，输出过程日志，无需中间确认 |
| 历史策略 N | 1/2/3 | 同自动模式，按匹配策略全自动执行 |
| **手动模式** | M | 每步执行前停下来，让用户确认「用哪个工具/走哪条轨道」，确认后执行该步，再停下来确认下一步 |

> 回复数字选择模式，不回复默认走 0 号自动模式；回复 `M` 进入手动模式。

**手动模式下每步格式：**

```
⏸ 下一步（Step N）
- 目的：___
- 建议工具/轨道：___（原因：___）
- 备选：___

**[确认]** **[换工具：___]** **[换轨道：___]** **[停止]**
```

> 用户确认后执行该步并输出结果，然后自动呈现下一步，继续等待确认。

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
- 可用 Adapter：（列出该环境下可用的 adapter，标注内部/外部）

## 📊 排查方案
（读取 memory/strategies.yaml 匹配后填写）

| # | 方案名 | 入轨方式 | 核心思路 | 预计耗时 |
|---|--------|---------|----------|----------|
| 0 | 自动模式（默认） | 三轨协作，动态入轨 | 证据驱动，代码/日志/数据交织推进，全自动完成 | - |
| 1 | （历史策略1） | ... | ... | ... |
| 2 | （历史策略2） | ... | ... | ... |
| 3 | （历史策略3） | ... | ... | ... |
| M | 手动模式 | 三轨协作 | 每步由用户确认工具/轨道后执行 | 按用户节奏 |

## ✋ 请确认方案
回复数字选择（0/1/2/3），或回复 M 进入手动模式。不回复默认走 0 号。说「停」或「等等」立即中断。
```

✅ **首轮输出完成，等待用户确认后继续。**

---

## SQL 安全门控（prod 环境专属）

> 完整规则、风险三档定义、交互格式、内联标注规范统一见 `guards/sql-safety.md`，本文件不重复定义。

**核心约束摘要（细节以 `guards/sql-safety.md` 为准）：**

| 要点 | 说明 |
|------|------|
| 适用范围 | prod 环境所有 Doris/MySQL SQL，强制执行；test/uat 跳过 |
| 风险三档 | 🟢 低风险自动执行 / 🟡 中风险等待确认 / 🔴 高风险必须明确确认 |
| 判定维度 | rows 行数 + type 是否全表扫描 + key 是否命中索引 + AI 综合判断 |
| 分区表 | 缺少 `dt_month` 时自动补充，不打断用户 |
| 用户改写 | 用户选「我来改写 SQL」后重新走 EXPLAIN 流程 |

---

## 工具优先级与外部库规则

**优先级顺序（从高到低）：**

1. 内部 Adapter（`adapters/<n>/client.py`）—— 直接使用
2. Platform Adapter（Doris，JDBC 访问）—— 需用户确认
3. 其他外部库 / 直连方式 —— 需用户确认

**外部库确认格式：**

```
⚠️ 当前步骤需要使用外部库：[库名/连接方式]
原因：内部 adapter 不覆盖该数据源（[说明原因]）
连接信息：[catalog/profile 名]

**[确认使用]** **[换内部方案]** **[跳过此步]**
```

> 用户选「换内部方案」时，AI 必须尝试用内部 adapter 改写；确实无法覆盖时再提示外部库。

---

## 安全门控（执行查询前必检）

| 查询类型 | 必读文件 |
|---------|---------|
| SQL（prod） | `guards/sql-safety.md`（权威，含三档交互格式） |
| SQL（test/uat） | `guards/sql-safety.md` |
| Redis | `guards/redis-safety.md` |
| ES | `guards/es-safety.md` |
| 所有结果展示 | `guards/data-masking.md` |
| 上下文占用 | `guards/context-limits.yaml` |
| 临时文件 | `guards/temp-files.yaml` |

---

## 首次配置门禁

在开始任何排查前，如果检测到 `.env` 不存在、`CODE_ROOT` 未配置、或 `CODE_ROOT` 路径不可用，必须先进入 `prompts/setup.md`，并禁止调用任何 adapter。

配置原则：

- 用户手动准备的核心文件只有 `.env`。
- 最小必填只有 `CODE_ROOT`；只做代码排查时不需要数据源凭证。
- Python 环境必须自动探测：`COMPASS_PYTHON` → skill `.venv` → `VIRTUAL_ENV` → 当前 Python → PATH 中的 `python3/python`。探测可自动执行，创建 venv 或安装依赖必须先确认。
- SLS / Platform / MySQL / Redis / ES 凭证按需填写；缺失时只标记对应 adapter 不可用，不阻断其他轨道。
- `config/code-repos.yaml` 通常由 setup 生成或使用仓库默认配置，项目目录特殊时才手动编辑。
- 使用 `tools/setup_check.py` 的 `inspect_setup / render_setup_report` 输出配置检查结果。

---

## 默认工具边界

| 允许 | 需用户确认 | 禁止 |
|------|-----------|------|
| 读/写本 Skill 目录内文件 | JDBC 等外部库调用 | `curl` 未登记的业务 HTTP 接口 |
| 通过 `adapters/<n>/client.py` 执行查询 | Platform adapter（Doris JDBC） | 本机 `mysql` / `redis-cli` 直连 |
| | | 工作区其他未登记 MCP |

---

## Harness 工具调用协议（v3 主线）

> 从 v3 开始，流程控制以 `tools/` 工具返回信号为准，Prompt 仅负责步骤内推理与展示格式。

### 必须调用的工具

- `tools/session_state.py`：`read_state / write_state / mark_checkpoint / assert_step_complete / advance_step`
- `tools/context_injector.py`：`get_context`（按步骤注入）
- `tools/sensors.py`：`sense_flow_deviation / sense_query_result / sense_context_size / sense_log_track_progress`
- `tools/compressor.py`：`compress`（体积超阈值时强制调用）
- `tools/action_cards.py`：`InvestigationAction / render_before_card / render_safety_gate_card / render_after_card / build_pending_confirmation`
- `tools/sql_gate.py`：`assess_sql_explain`（prod SQL EXPLAIN 风险判定）
- `tools/evidence_graph.py`：`EvidenceGraph`（沉淀页面、接口、方法、表、日志线索）

### Action Card 协议（强制）

任何查询、日志搜索、代码读取、Redis/ES 访问都必须先构造 `InvestigationAction`，再按统一协议执行。**禁止直接调用 adapter 或直接读代码后再补过程说明**。

每个动作的强制顺序：

1. 构造 `InvestigationAction`，写明目的、工具、环境、查询对象、成功标准。
2. 输出 `render_before_card(action)`，让用户看到即将执行的内容。
3. 输出对应 Safety Gate；SQL 使用 `assess_sql_explain` 后再 `render_safety_gate_card`。
4. 若 `gate.requires_confirmation=true`，必须 `build_pending_confirmation` 并暂停；用户明确回复「确认执行」前禁止执行。
5. 执行查询 / 读代码 / 拉日志。
6. 构造 `ActionResult`，输出 `render_after_card(action, result)`。
7. 将 `ActionResult.leads` 写入 `EvidenceGraph`，作为下一步候选来源。

| 轨道 | 执行前必须展示 | 执行后必须提取 |
|------|----------------|----------------|
| SLS | query、时间范围、limit、容器/服务 | traceId/tlogId、接口、服务、异常时间、可继续查的代码/DB/链路 |
| SQL | 完整 SQL、环境、EXPLAIN SQL 和风险 | 返回行数、关键字段、相关表、是否指向代码/日志 |
| 代码 | 应用、文件/类/方法、来源线索 | 页面→接口→Controller→Service→Mapper→表、日志关键字、业务分支 |
| Redis/ES | 命令/索引/查询体、范围限制 | key/index、命中摘要、是否指向 SQL/代码/日志 |

### 每轮最小调用顺序

1. `read_state`
2. `sense_flow_deviation`
3. `get_context`
4. （每个动作前）`InvestigationAction -> render_before_card -> Safety Gate`
5. （风险需确认时）`build_pending_confirmation -> write_state -> 暂停`
6. （执行后）`ActionResult -> render_after_card -> EvidenceGraph.add_result_leads`
7. （查询后）`sense_query_result + mark_checkpoint`
8. （推进前）`assert_step_complete`
9. （必要时）`sense_context_size -> compress`
10. `advance_step`
11. `write_state`

### 强制门禁

- `assert_step_complete.ok=false`：禁止推进，必须补完缺失项。
- `sense_log_track_progress.complete=false`：禁止进入 Step 7。
- `sense_context_size.action in {COMPRESS, EMERGENCY_COMPRESS}`：必须先压缩再继续。

---

## 能力注册表

### Adapters

| Adapter | 用途 | 环境覆盖 | 类型 | 状态 |
|---------|------|---------|------|------|
| platform | Doris 分析数据查询 | 仅 prod | 外部（JDBC） | ✅ |
| sls | SLS 日志查询 | prod / test / uat | 内部 | ✅ |
| mysql | MySQL/PolarDB 数据库查询 | test / uat | 内部 | ✅ |
| redis | Redis 缓存状态查询 | test / uat | 内部 | ✅ |
| elasticsearch | ES 全文检索 | test（仅 test-finance） | 内部 | ✅ |

> 凭证通过环境变量注入（`${VAR}` 语法），`adapters/base.py` 自动读取 `.env`。

### Projects

`projects/` 下每个 `.md` 是已注册项目的代码导航地图，路径基于 `config/code-repos.yaml`，用户在 `.env` 设置 `CODE_ROOT`。

### 策略系统

`memory/strategies.yaml` 存储所有排查经验，多维度评分自动匹配最佳方案。

---

## 排查流程

> 总览表：8步顺序执行，不可跳步，不可并行。交互细节见各引用文件。

| Step | 名称 | 触发条件 | 执行逻辑摘要 | 完成标志 | 引用 |
|------|------|---------|------------|---------|------|
| 1 | 实体提取 | 用户描述完问题，首轮回复中执行 | 识别 user_id / org_id / 订单号 / 服务名 / 时间范围等；缺失项标注 ❓ 并追问；只识别不推断 | 实体表格输出，追问已发出 | `prompts/entity-extraction.md` |
| 2 | 场景分类 | Step 1 完成后，同在首轮回复中 | 判断 C端/B端；匹配 categories.yaml 类别；类别匹配度影响策略评分 | 场景 + 类别已输出 | `prompts/classify-scene.md` |
| 3 | 代码理解 | 有 projects/ 注册项目时执行；否则跳过 | 读 `projects/<服务名>.md`；提取核心类、日志关键字、表名、Redis key 模式；结果带入 Step 4 | 代码导航完成或跳过声明已输出 | `prompts/query-planning.md` Step 0 |
| 4 | 查询规划 | Step 3 完成后，首轮回复末尾 | 环境探查 → 策略匹配（Top 3 + 0/M）→ 入轨声明（🔵🟡🟢）→ 步骤表格展示 → **等待用户确认模式和入轨** | 用户回复确认编号或 M | `prompts/query-planning.md` |
| 5 | 安全门控 | 每次调用 adapter 前逐次触发 | prod SQL **强卡** EXPLAIN 三档（🟢自动/🟡等确认/🔴必须明确确认）；外部库强卡确认；结果展示前脱敏 | 门控通过或用户确认 | `guards/sql-safety.md` 等 |
| 6 | 执行查询 | Step 5 通过后立即执行 | 按所选模式推进：自动模式全跑输出进度表；手动模式每步停下确认工具/轨道；**日志轨强制走四步：关键字查日志 → 提取链路ID（traceId/tlogId）→ 拉全链路 → 触发代码轨**；空结果最多重试 3 次后强制暂停 | 三轨收敛或路径耗尽 | `adapters/<n>/client.py` + `prompts/query-planning.md` |
| 7 | 结果分析 | Step 6 收敛后自动进入 | 输出结论卡片 → 排查过程卡片（技术用户）→ 查询结果明细 → 建议操作；业务用户跳过过程卡片 | 结论卡片 + 操作选项已输出 | `prompts/result-analysis.md` |
| 8 | 策略归档 | **Step 7 结论卡片输出完毕后自动触发，不等用户说结束** | 向用户收集反馈评分 → 将本次排查路径、有效关键字、根因标签写入 strategies.yaml → 更新匹配度评分；**不可跳过** | 反馈收集完毕，归档简报已输出 | `prompts/strategy-improvement.md` |

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
> 第一条回复必须包含「问题复述、识别实体、场景判断、环境与工具、排查方案、确认」六个部分，并提示用户选择执行模式（0=自动 / M=手动）；
> 执行时采用三轨协作法（代码/日志/数据交织推进），开始前必须声明入轨方式；
> 自动模式下方案确认后全自动跑完，输出过程，无需中间确认；
> 手动模式下每步停下来让用户确认工具/轨道后再执行；
> prod 环境 SQL 必须先 EXPLAIN，低风险自动执行，中风险等待确认，高风险必须明确确认（细节见 `guards/sql-safety.md`）；内部 adapter 优先，JDBC 等外部库须用户确认。
