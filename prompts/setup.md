# 首次配置引导

当用户触发「配置」「setup」「初始化」，或 Compass 检测到 `.env` 不存在 / `CODE_ROOT` 不可用时，执行本流程。

## 配置原则

安装后用户需要手动准备的核心文件只有 `.env`。

| 类型 | 是否必填 | 说明 |
|------|----------|------|
| `.env` | 必填 | 从 `.env.example` 复制，保存本机路径和各 adapter 凭证 |
| `CODE_ROOT` | 最小必填 | 指向本机代码仓库根目录；只做代码排查时仅此项即可 |
| SLS / Platform / MySQL / Redis / ES 凭证 | 按需填写 | 需要查对应数据源时再填；未填则该 adapter 标记不可用 |
| `config/code-repos.yaml` | 通常自动生成 | 目录特殊或项目名不一致时才手动编辑 |

> 不再从 MCP 配置中推断连接信息。Compass 的主路径是内部 adapter 读取 `.env`，再通过 adapter `health_check()` 验证。

## 触发条件

- 用户说「配置」「初始化」「setup」「更新配置」「重新配置」
- 首次运行 Compass 时 `.env` 不存在
- `.env` 存在但 `CODE_ROOT` 为空或路径不存在
- 用户要使用某个 adapter，但对应环境变量缺失

## Step 1 — 运行配置检查

使用 `tools/setup_check.py` 检查当前状态：

```python
from tools.setup_check import inspect_setup, render_setup_report

report = inspect_setup("<compass_skill_root>")
print(render_setup_report(report))
```

输出给用户：

- `.env` 是否存在
- `CODE_ROOT` 是否已配置且路径存在
- 哪些 adapter 已配置，哪些缺变量
- 下一步需要用户补什么

若 `report.minimum_ready == false`，禁止开始线上排查，先完成 Step 2。

## Step 2 — 创建或更新 `.env`

如果 `.env` 不存在，提示用户：

```bash
cp .env.example .env
```

最小可用配置：

```dotenv
CODE_ROOT=/Users/<you>/workspace/projects
```

按需数据源配置：

```dotenv
# SLS：查日志 / 拉 traceId 时需要
SLS_ACCESS_KEY_ID=
SLS_ACCESS_KEY_SECRET=

# Platform：查 prod Doris 时需要
PLATFORM_USERNAME=
PLATFORM_PASSWORD=

# ES：查 test-finance ES 时需要
ES_TEST_FINANCE_USERNAME=elastic
ES_TEST_FINANCE_PASSWORD=

# MySQL / Redis：test/uat 数据核验或缓存核验时需要
MYSQL_POLARDB_TEST_HOST=
MYSQL_POLARDB_TEST_USER=
MYSQL_POLARDB_TEST_PASSWORD=
REDIS_FINANCE_TEST_HOST=
REDIS_FINANCE_TEST_PASSWORD=
```

## Step 3 — 配置代码仓库路径

询问用户：

```text
请提供你的代码仓库根目录，例如：
/Users/xxx/workspace/projects
```

处理规则：

- 写入 `.env` 的 `CODE_ROOT`
- 若项目目录与默认扫描不一致，再更新 `config/code-repos.yaml`
- `config/code-repos.yaml` 可以从 `config/code-repos.yaml.example` 复制生成

## Step 4 — 生成或校验项目导航

若 `projects/` 已有导航文件，先使用现有文件。

若需要新项目入驻：

- 执行 `prompts/project-onboarding.md`
- Java 后端：扫描 Controller → Service → Mapper
- Vue 前端：扫描 router → api → views
- 输出 `projects/<name>.md`

## Step 5 — Adapter 连通性验证

只验证已配置的 adapter。不要因为某个按需 adapter 未配置而阻断整个 Compass。

| Adapter | 验证方式 | 未配置时 |
|---------|----------|----------|
| SLS | `SLSClient().health_check()` | 日志轨不可用，但代码轨仍可用 |
| Platform | `PlatformClient().health_check()` | prod Doris 不可用；SQL 工单建议仍可生成 |
| MySQL | `MySQLClient(profile).health_check()` | test/uat SQL 不可用 |
| Redis | `RedisClient(profile).health_check()` | 缓存核验不可用 |
| ES | `ElasticsearchClient(profile).health_check()` | ES 检索不可用 |

输出配置报告：

| Adapter | 配置状态 | 连通状态 | 可用环境 | 影响 |
|---------|----------|----------|----------|------|
| SLS | 已配置 / 缺变量 | ok / error / skipped | prod/test/uat | ___ |
| Platform | 已配置 / 缺变量 | ok / error / skipped | prod | ___ |
| MySQL | 已配置 / 缺变量 | ok / error / skipped | test/uat | ___ |
| Redis | 已配置 / 缺变量 | ok / error / skipped | test/uat | ___ |
| ES | 已配置 / 缺变量 | ok / error / skipped | test | ___ |

## Step 6 — 完成口径

完成时告诉用户：

- 最小配置是否已就绪
- `.env` 位置
- `CODE_ROOT` 当前值
- 已可用 adapter
- 未配置 adapter 对排查能力的影响
- 后续可以直接说「使用罗盘查线上问题：...」

## 更新已有配置

用户说「更新配置」「重新配置」时：

1. 运行 `inspect_setup`
2. 询问要更新哪部分：`CODE_ROOT` / SLS / Platform / MySQL / Redis / ES
3. 只更新 `.env` 中对应变量
4. 重新运行对应 adapter 的 `health_check`
