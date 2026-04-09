# Compass Skill Review 修复计划

> **执行者**：Sonnet（或任意 Claude Code 会话）
> **生成时间**：2026-03-31
> **来源**：Opus 对 Compass Skill 全量 Review 后生成
>
> **执行方式**：按 Task 顺序逐个完成，每个 Task 包含精确的文件路径、修改内容和验证方法。
> **原则**：只改必要的，不重构、不加功能、不改架构。

---

## Task 1 — [P0] SLS config.yaml 凭证迁移到环境变量

**文件**：`/Users/a...../.claude/skills/compass/adapters/sls/config.yaml`

**当前内容**（有明文 AK/SK）：
```yaml
enabled: true

endpoint: "cn-hangzhou.log.aliyuncs.com"
access_key_id: "${ALIBABA_CLOUD_ACCESS_KEY_ID}"
access_key_secret: "${ALIBABA_CLOUD_ACCESS_KEY_SECRET}"

logstore: "all"

projects:
  prod: "k8s-log-c7fd130d77f0f4627ac91c831bffeb751"
  test: "k8s-log-caf7dea70bc8a4de89a230c59deacdd73"
  uat: "k8s-log-cc16e3815a19540a98bbc94d1e7bde437"

default_env: "prod"
```

**替换为**：
```yaml
enabled: true

endpoint: "cn-hangzhou.log.aliyuncs.com"
access_key_id: "${SLS_ACCESS_KEY_ID}"
access_key_secret: "${SLS_ACCESS_KEY_SECRET}"

logstore: "all"

projects:
  prod: "k8s-log-c7fd130d77f0f4627ac91c831bffeb751"
  test: "k8s-log-caf7dea70bc8a4de89a230c59deacdd73"
  uat: "k8s-log-cc16e3815a19540a98bbc94d1e7bde437"

default_env: "prod"
```

**验证**：读取修改后的文件，确认不包含 `LTAI5t` 和 `9RldO` 字符串。

---

## Task 2 — [P0] ES config.yaml 凭证迁移到环境变量

**文件**：`/Users/a...../.claude/skills/compass/adapters/elasticsearch/config.yaml`

**当前内容**：
```yaml
enabled: true

profiles:
  - name: "test-finance"
    env: "test"
    url: "http://es-cn-0pp0wwi7h001n7gez.elasticsearch.aliyuncs.com:9200"
    username: "elastic"
    password: "yunkc321#"
    description: "财务测试 ES"

default_profile: "test-finance"
```

**替换为**：
```yaml
enabled: true

profiles:
  - name: "test-finance"
    env: "test"
    url: "http://es-cn-0pp0wwi7h001n7gez.elasticsearch.aliyuncs.com:9200"
    username: "${ES_TEST_FINANCE_USERNAME:-elastic}"
    password: "${ES_TEST_FINANCE_PASSWORD}"
    description: "财务测试 ES"

default_profile: "test-finance"
```

**验证**：确认不包含 `yunkc321` 字符串。

---

## Task 3 — [P0] Platform config.yaml 凭证迁移到环境变量

**文件**：`/Users/a...../.claude/skills/compass/adapters/platform/config.yaml`

**当前内容**：
```yaml
enabled: true

base_url: "http://10.20.0.2:8081"

auth:
  header_user: "X-User-Name"
  header_pass: "X-Password"
  username: "dongmaowei"
  password: "n#N6yX&d4Qt#"

timeout: 30
export_timeout: 120
```

**替换为**：
```yaml
enabled: true

base_url: "http://10.20.0.2:8081"

auth:
  header_user: "X-User-Name"
  header_pass: "X-Password"
  username: "${PLATFORM_USERNAME}"
  password: "${PLATFORM_PASSWORD}"

timeout: 30
export_timeout: 120
```

**验证**：确认不包含 `dongmaowei` 和 `n#N6yX` 字符串。

---

## Task 4 — [P0] 创建 .env.example 模板

**文件**：`/Users/a...../.claude/skills/compass/.env.example`

**创建此新文件**，内容如下：
```bash
# Compass Skill 环境变量模板
# 复制为 .env 后填入实际值，.env 已被 .gitignore 排除

# ===== SLS =====
SLS_ACCESS_KEY_ID=
SLS_ACCESS_KEY_SECRET=

# ===== Elasticsearch =====
ES_TEST_FINANCE_USERNAME=elastic
ES_TEST_FINANCE_PASSWORD=

# ===== Platform (Doris) =====
PLATFORM_USERNAME=
PLATFORM_PASSWORD=

# ===== MySQL (已在用，此处仅汇总) =====
# MYSQL_POLARDB_TEST_HOST=
# MYSQL_POLARDB_TEST_PORT=3306
# MYSQL_POLARDB_TEST_USER=
# MYSQL_POLARDB_TEST_PASSWORD=
# MYSQL_POLARDB_UAT_HOST=
# MYSQL_POLARDB_UAT_PORT=3306
# MYSQL_POLARDB_UAT_USER=
# MYSQL_POLARDB_UAT_PASSWORD=
# MYSQL_MAIN_TEST_HOST=
# MYSQL_MAIN_TEST_PORT=3306
# MYSQL_MAIN_TEST_USER=
# MYSQL_MAIN_TEST_PASSWORD=
# MYSQL_MAIN_UAT_HOST=
# MYSQL_MAIN_UAT_PORT=3306
# MYSQL_MAIN_UAT_USER=
# MYSQL_MAIN_UAT_PASSWORD=

# ===== Redis (已在用，此处仅汇总) =====
# REDIS_FINANCE_TEST_HOST=
# REDIS_FINANCE_TEST_PASSWORD=
# REDIS_FINANCE_UAT_HOST=
# REDIS_FINANCE_UAT_PASSWORD=
# REDIS_ACTIVITY_TEST_HOST=
# REDIS_ACTIVITY_TEST_PASSWORD=
# REDIS_ACTIVITY_UAT_HOST=
# REDIS_ACTIVITY_UAT_PASSWORD=
# REDIS_PRICE_TEST_HOST=
# REDIS_PRICE_TEST_PASSWORD=
# REDIS_PRICE_UAT_HOST=
# REDIS_PRICE_UAT_PASSWORD=
# REDIS_REDIS2_TEST_HOST=
# REDIS_REDIS2_TEST_PASSWORD=
```

---

## Task 5 — [P0] 创建 .gitignore

**文件**：`/Users/a...../.claude/skills/compass/.gitignore`

**创建此新文件**，内容如下：

```gitignore
# 敏感配置（环境变量实际值）
../.env

# Python
__pycache__/
*.pyc
.venv/

# 排查临时文件
/tmp/

# 审计日志（含脱敏记录，不入库）
memory/audit-log.yaml
memory/audit-archive/

# OS
.DS_Store
```

**注意**：不排除 `config.yaml`（因为凭证已迁移到环境变量，config.yaml 可以安全入库）。不排除 `.env.example`（模板文件需要入库）。

---

## Task 6 — [P1] categories.yaml 补充退款类代码级关键词

**文件**：`/Users/a...../.claude/skills/compass/memory/categories.yaml`

**找到**：
```yaml
  - id: "cat-refund"
    name: "充电订单-退款问题"
    keywords: ["退款", "退费", "退款失败", "退款超时", "未退款"]
    scene: "c-side"
    primary_services: ["finance_server", "payment-server"]
    frequency: 0
```

**替换为**：
```yaml
  - id: "cat-refund"
    name: "充电订单-退款问题"
    keywords: ["退款", "退费", "退款失败", "退款超时", "未退款", "refund", "refundAmount", "returnMoney", "chargeBack", "退款申请", "退款审核"]
    scene: "c-side"
    primary_services: ["finance_server", "payment-server"]
    frequency: 0
```

---

## Task 7 — [P1] SKILL.md 能力注册表补充环境覆盖信息

**文件**：`/Users/a...../.claude/skills/compass/SKILL.md`

**找到**能力注册表中的 Adapters 表格：
```markdown
| Adapter        | 用途                        | 环境/版本              | 适用场景                          | 状态      |
|----------------|-----------------------------|------------------------|----------------------------------|-----------|
| platform       | Doris 分析数据查询            | 仅 prod                | 订单/交易/账单等业务数据统计与明细查询  | ✅ 可用   |
| sls            | SLS 日志查询                 | prod / test / uat      | 接口调用链追踪、错误日志定位、关键字搜索 | ✅ 可用   |
| mysql          | MySQL/PolarDB 数据库查询      | 多 profile（按库区分）   | 业务表数据核查、配置验证、关联关系排查   | ✅ 可用   |
| redis          | Redis 缓存状态查询            | 多 profile，standalone/cluster | 会话状态、分布式锁、计数器、缓存一致性 | ✅ 可用   |
| elasticsearch  | ES 全文检索                  | 多 profile，6.x/7.x/8.x 自动适配 | 历史记录检索、流水全文搜索、聚合分析 | ✅ 可用   |
```

**替换为**：
```markdown
| Adapter        | 用途                        | 环境覆盖                          | 适用场景                          | 状态      |
|----------------|-----------------------------|----------------------------------|----------------------------------|-----------|
| platform       | Doris 分析数据查询            | 仅 prod                          | 订单/交易/账单等业务数据统计与明细查询  | ✅ 可用   |
| sls            | SLS 日志查询                 | prod / test / uat                | 接口调用链追踪、错误日志定位、关键字搜索 | ✅ 可用   |
| mysql          | MySQL/PolarDB 数据库查询      | test / uat（无 prod profile）     | 业务表数据核查、配置验证、关联关系排查   | ✅ 可用   |
| redis          | Redis 缓存状态查询            | test / uat（无 prod profile）     | 会话状态、分布式锁、计数器、缓存一致性   | ✅ 可用   |
| elasticsearch  | ES 全文检索                  | test（仅 test-finance 一个 profile） | 历史记录检索、流水全文搜索、聚合分析   | ✅ 可用   |
```

---

## Task 8 — [P2] redis/client.py scan_keys 完善迭代逻辑

**文件**：`/Users/a...../.claude/skills/compass/adapters/redis/client.py`

当前 `scan_keys` 方法在 `cursor == 0` 时停止，这是正确的（Redis SCAN 返回 cursor=0 表示迭代完成）。但问题是 `len(keys)` 可能因为 count 参数只是建议值而漏 key。实际上当前实现已经是循环 SCAN 直到 cursor=0 或达到 count 上限，逻辑本身是正确的。

**复核后结论**：`scan_keys` 实现无 bug，原 review 中「cursor 被丢弃」的判断有误——代码是在 while 循环中持续迭代的。**此 Task 跳过，无需修改。**

---

## Task 9 — [P2] 在 SKILL.md 的「交互原则 > 流程交互」中补充快捷确认机制

**文件**：`/Users/a...../.claude/skills/compass/SKILL.md`

**找到**：
```markdown
### 流程交互

- **首轮必须先分析与方案，再执行**（见文首「首轮回复门禁」）；禁止用户一问就直连数据源
```

**替换为**：
```markdown
### 流程交互

- **首轮必须先分析与方案，再执行**（见文首「首轮回复门禁」）；禁止用户一问就直连数据源
- **快捷确认**：当用户描述中明确包含查询目标、环境、时间范围（三要素齐全），且只涉及单一数据源时，方案展示可精简为「单方案 + 确认」，不强制展示 Top3 策略对照表
```

---

## 执行完成后的验证清单

执行完 Task 1~7、9 后，依次验证：

1. `grep -r "LTAI5t" /Users/a...../.claude/skills/compass/adapters/` — 应返回空
2. `grep -r "yunkc321" /Users/a...../.claude/skills/compass/adapters/` — 应返回空
3. `grep -r "dongmaowei" /Users/a...../.claude/skills/compass/adapters/` — 应返回空
4. `grep -r 'n#N6yX' /Users/a...../.claude/skills/compass/adapters/` — 应返回空
5. `cat /Users/a...../.claude/skills/compass/.gitignore` — 应存在且包含 `.env`
6. `cat /Users/a...../.claude/skills/compass/.env.example` — 应存在且包含 `SLS_ACCESS_KEY_ID`
7. `grep "refundAmount" /Users/a...../.claude/skills/compass/memory/categories.yaml` — 应命中 cat-refund
8. `grep "无 prod profile" /Users/a...../.claude/skills/compass/SKILL.md` — 应命中 mysql 和 redis 行
9. `grep "快捷确认" /Users/a...../.claude/skills/compass/SKILL.md` — 应命中

---

## 不在本次范围内（记录备忘）

| 编号 | 内容 | 原因 |
|------|------|------|
| F1 | 子 Agent 返回结果的脱敏 | 需要改 adapter 基类或主 Agent 调用逻辑，影响面大，需单独评估 |
| F2 | 补充 prod 环境 MySQL/Redis profile | 需要获取生产凭证，不是代码问题 |
| F3 | SKILL.md 大幅精简 | 需要完整重写测试，风险高，择期做 |
| F4 | platform/client.py SSE 超时重试 | 当前没有实际问题报告，暂不改 |
