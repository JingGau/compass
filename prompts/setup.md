# 首次配置引导

当用户触发「配置」「setup」「初始化」，或 Compass 检测到 `.env` 不存在 / `CODE_ROOT` 不可用时，执行本流程。

## 配置原则

安装后用户需要手动准备的核心文件只有 `.env`。

| 类型 | 是否必填 | 说明 |
|------|----------|------|
| `.env` | 必填 | 从 `.env.example` 复制，保存本机路径和各 adapter 凭证 |
| `CODE_ROOT` | 最小必填 | 指向本机代码仓库根目录；只做代码排查时仅此项即可 |
| Python 环境 | 自动探测 | 优先使用 `COMPASS_PYTHON` / skill `.venv` / 当前虚拟环境 / 当前 Python / PATH |
| SLS / Platform / MySQL / Redis / ES 凭证 | 按需填写 | 需要查对应数据源时再填；未填则该 adapter 标记不可用 |
| `config/code-repos.yaml` | 通常自动生成 | 目录特殊或项目名不一致时才手动编辑 |

> 不再从 MCP 配置中推断连接信息。Compass 的主路径是内部 adapter 读取 `.env`，再通过 adapter `health_check()` 验证。
> Python 环境只自动探测，不静默创建 venv、不静默安装依赖；需要创建或安装时，先展示命令并等待用户确认。

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
- Python 环境是否可用、来自哪里、版本号是多少
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

可选 Python 覆盖配置：

```dotenv
# 不填时自动探测；只有你想强制使用某个 Python 时才填写
COMPASS_PYTHON=/Users/<you>/workspace/compass/.venv/bin/python
```

按需数据源配置：

```dotenv
# SLS：查日志 / 拉 traceId 时需要
SLS_DEFAULT_ENV=prod
SLS[0].NAME=PROD
SLS[0].ENV=prod
SLS[0].DESC=生产环境 SLS 日志 Project
SLS[0].ENDPOINT=cn-hangzhou.log.aliyuncs.com
SLS[0].PROJECT=
SLS[0].ACCESS_KEY_ID=
SLS[0].ACCESS_KEY_SECRET=
SLS[0].LOGSTORE=all

# Platform：查 prod Doris 时需要
PLATFORM_DEFAULT_PROFILE=PROD
PLATFORM[0].NAME=PROD
PLATFORM[0].ENV=prod
PLATFORM[0].DESC=生产环境 Doris 查询平台
PLATFORM[0].BASE_URL=http://10.20.0.2:8081
PLATFORM[0].USERNAME=
PLATFORM[0].PASSWORD=

# ES：查 test-finance ES 时需要
ES_DEFAULT_PROFILE=FINANCE_TEST
ES[0].NAME=FINANCE_TEST
ES[0].ENV=test
ES[0].DESC=财务测试环境 ES
ES[0].URL=
ES[0].USERNAME=elastic
ES[0].PASSWORD=

# MySQL / Redis：test/uat 数据核验或缓存核验时需要
MYSQL_DEFAULT_PROFILE=FINANCE_TEST
MYSQL[0].NAME=FINANCE_TEST
MYSQL[0].ENV=test
MYSQL[0].DESC=财务测试环境 MySQL/PolarDB
MYSQL[0].HOST=
MYSQL[0].PORT=3306
MYSQL[0].USER=
MYSQL[0].PASSWORD=
MYSQL[0].DATABASE=yunkc_finance

REDIS_DEFAULT_PROFILE=FINANCE_TEST
REDIS[0].NAME=FINANCE_TEST
REDIS[0].ENV=test
REDIS[0].DESC=财务测试环境 Redis，钱包/清分相关缓存
REDIS[0].HOST=
REDIS[0].PORT=6379
REDIS[0].PASSWORD=
REDIS[0].DB=30
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

## Step 5 — Python 环境与依赖验证

Compass 自动探测 Python 的优先级：

1. `.env` 或运行环境中的 `COMPASS_PYTHON`
2. skill 目录下 `.venv/bin/python`
3. 当前激活的 `VIRTUAL_ENV`
4. 当前运行 Codex 的 Python
5. PATH 中的 `python3` / `python`

要求 Python 版本为 3.10+。

如果未检测到可用 Python，输出建议：

```bash
python3 -m venv .venv
```

如果检测到 Python 但缺依赖，输出建议安装命令；安装动作必须等待用户确认后执行。若来源是 `COMPASS_PYTHON` / skill `.venv` / `VIRTUAL_ENV`，安装命令使用该 Python；若来源是当前 Python 或 PATH，优先建议创建 skill `.venv` 后再安装。

## Step 6 — Adapter 连通性验证

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

## Step 7 — 完成口径

完成时告诉用户：

- 最小配置是否已就绪
- `.env` 位置
- `CODE_ROOT` 当前值
- Python 来源、版本、是否使用 `.venv`
- 已可用 adapter
- 未配置 adapter 对排查能力的影响
- 后续可以直接说「使用罗盘查线上问题：...」

## 更新已有配置

用户说「更新配置」「重新配置」时：

1. 运行 `inspect_setup`
2. 询问要更新哪部分：`CODE_ROOT` / SLS / Platform / MySQL / Redis / ES
3. 只更新 `.env` 中对应变量
4. 重新运行对应 adapter 的 `health_check`
