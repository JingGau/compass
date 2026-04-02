---
name: compass
description: "线上问题排查与数据洞察 Skill。通过自然语言驱动多数据源查询，精准定位问题根因。覆盖 C端和 B端场景。"
---

# Compass（罗盘）

线上问题排查与数据洞察 Skill。通过自然语言驱动多数据源查询，在复杂系统中精准定位问题根因。覆盖 C端（用户App）和 B端（omp-shop 后台）场景。

---

## 首轮回复门禁（违反即流程错误）

用户刚描述完问题的**第一条回复**里，**禁止**：

- 调用 Shell 执行 `python` / `mysql` / `redis-cli` 或任何 `adapters/*/client.py`
- 在未展示方案前，直接查库、查日志、查 Redis、查 ES、查 Doris

**必须先**让用户**看得见**：

1. **复述与实体**：用户问题一句话复述 + 已识别实体清单（缺什么要追问）
2. **场景与类别**：判断 C端 / B端 / 暂不确定 + 对应 `memory/categories.yaml` 的类别
3. **环境意识**：说明将用哪个环境（prod/test/uat）及哪些 adapter 在该环境可用
4. **策略与方案**：必读 `memory/strategies.yaml` 做匹配，用表格展示 **历史策略 Top 3** + 0号自动模式 + 自定义，多线索拆多方案
5. **征求确认**：`[0 自动模式（默认）]` / `[策略 1/2/3]` / `[4 自定义思路]`

用户不表态 → 默认走 0 号；用户说「停」「等等」→ 立即中断。

---

## 默认工具边界（仅用罗盘内能力）

| 允许 | 说明 |
|------|------|
| 读/写本 Skill 目录内文件 | `SKILL.md`、`prompts/`、`knowledge/`、`memory/`、`projects/`、`guards/`、`adapters/*/config.yaml` 等 |
| **执行查询** | **仅**通过 `adapters/<name>/client.py`（用本仓库内 Python/venv 调用） |

| 默认禁止（除非用户**明确说**要用） | 说明 |
|------|------|
| 工作区里**其他 MCP**（如独立 MySQL、SLS、ES MCP） | 与罗盘 adapter 重复且环境不一致 |
| 随意 `curl` 未在知识库/项目中登记的业务 HTTP 接口 | 不属于罗盘约定能力 |
| 本机 `mysql` / `redis-cli` 直连（绕过 adapter） | 绕过统一门禁与审计；**禁止** |

---

## 安全约束（硬性，不可绕过）

1. SQL 执行前必须经过 `guards/sql-safety.md` 检查（MySQL + Platform）
2. Redis 操作前必须经过 `guards/redis-safety.md` 检查
3. ES 查询前必须经过 `guards/es-safety.md` 检查
4. 所有查询结果展示必须经过 `guards/data-masking.md` 脱敏
5. 未经用户确认不得执行任何查询；**且不得跳过「实体+场景+策略/方案展示」直接进入查询**
6. 严禁执行任何写操作（INSERT / UPDATE / DELETE / DROP / SET / DEL 等）
7. 结果集上下文占用必须遵守 `guards/context-limits.yaml` 限制
8. 临时文件管理遵守 `guards/temp-files.yaml` 规范

---

## 能力注册表

### Adapters（数据源 — 数据在哪、怎么查）

| Adapter        | 用途                        | 环境覆盖                          | 状态      |
|----------------|-----------------------------|----------------------------------|-----------|
| platform       | Doris 分析数据查询            | 仅 prod                          | ✅ 可用   |
| sls            | SLS 日志查询                 | prod / test / uat                | ✅ 可用   |
| mysql          | MySQL/PolarDB 数据库查询      | test / uat（无 prod profile）     | ✅ 可用   |
| redis          | Redis 缓存状态查询            | test / uat（无 prod profile）     | ✅ 可用   |
| elasticsearch  | ES 全文检索                  | test（仅 test-finance 一个 profile） | ✅ 可用   |

> 凭证管理：所有 adapter 凭证通过环境变量注入（`${VAR}` 语法），`adapters/base.py` 自动读取 `.env`。

### Projects（代码导航 — 代码在哪、怎么读）

`projects/` 下每个 `.md` 文件是已注册项目的**代码导航地图**。

> 路径基于 `config/code-repos.yaml` 解析，每个用户在本机 `.env` 设置自己的 `CODE_ROOT`。

### 策略系统（经验 — 历史上类似问题怎么查的）

`memory/strategies.yaml` 存储所有排查经验，通过多维度评分自动匹配最佳方案。

---

## 排查流程（入口指针）

每个 Step 的详细逻辑在对应 prompt 文件中，本文件只列步骤和关键约束。

| Step | 名称 | 详细逻辑文件 | 关键约束 |
|------|------|-------------|---------|
| 1 | 实体提取 | `prompts/entity-extraction.md` | 只识别实体，不推荐查询 |
| 2 | 场景分类 | `prompts/classify-scene.md` | 判断 C端/B端，匹配类别 |
| 3 | 代码理解 | `prompts/query-planning.md` Step 0 | 有 projects 注册时执行，否则跳过 |
| 4 | 查询规划 | `prompts/query-planning.md` | 含环境探查、策略匹配、方案展示 |
| 5 | 安全门控 | `guards/sql-safety.md` 等 | SQL/Redis/ES 检查 + 脱敏 |
| 6 | 执行查询 | `adapters/<name>/client.py` | 首次确认后全自动，空结果自动换路径 |
| 7 | 结果分析 | `prompts/result-analysis.md` | 结论卡片面向提问者，独立可复制 |
| 8 | 策略归档 | `prompts/strategy-improvement.md` | 收集反馈 → 归档 → 自优化 |

> **低阶模型**：读 `prompts/lite-flow.md`，4步精简流程，不做代码理解和多方案。

---

## 特殊入口

| 用户说 | 执行 |
|--------|------|
| "配置" / "setup" / "初始化" | 读取 `prompts/setup.md`，引导首次配置 |
| "注册项目" | 读取 `prompts/project-onboarding.md`，扫描代码生成导航地图 |
| "扫描前端整理知识" | 读取 `prompts/knowledge-batch-scan.md`，批量扫描生成 |
| "注册页面" | 读取 `prompts/knowledge-onboarding.md` |
| "加个 XX 能力" | 读取 `adapters/_convention.md`，创建新 adapter |
| "知识库现状" | 汇总 projects/ + adapter 状态 + 策略数量 |
| "看更多" / "下钻" | 从临时文件加载下一批结果 |
