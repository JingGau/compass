# Compass Harness（罗盘）

Compass 是一个本地优先的线上问题排查 Skill。它把用户的自然语言问题转成可执行的排查工单，通过代码、日志、数据库、缓存和知识库建立证据链，最后输出可追溯结论。

它不是公共 MCP 服务，也不是单独的大模型应用。推荐使用方式是：

```text
User -> Agent -> Compass Skill -> CLI Runtime -> Adapter -> Data Source
```

## 适合什么场景

- C 端、B 端、财务、订单、充电等线上问题排查。
- 用户输入不完整，需要先结构化问题、补实体、再排查。
- 需要同时看代码、SLS 日志、SQL、Redis、ES、业务知识库的问题。
- 需要输出“根因、证据、影响面、待验证假设、后续建议”的问题。

不适合用来直接修代码、执行写 SQL、泛查日志、绕过权限或脱敏规则。

## 从零开始的推荐路径

第一次使用时，按这个顺序走：

1. 复制 `.env.example` 为 `.env`，先填 `CODE_ROOT`。
2. 运行 `setup-check`，确认最小配置可用。
3. 按需填写 SLS / Platform / MySQL / Redis / ES 环境变量。
4. 注册或扫描项目，生成 `projects/<服务名>.md` 代码导航地图。
5. 用自然语言提问，例如“使用罗盘查线上问题：...”，首轮确认方案后再开始查询。

如果只是让 Compass 帮你读代码链路，通常只需要完成第 1、2、4 步；如果要查线上日志和数据，再补第 3 步。

## 目录说明

```text
compass/
  SKILL.md              # Agent 必须遵循的排查规则
  README.md             # 给用户看的使用说明
  .env.example          # 本机配置模板
  compass_cli/          # CLI 入口
  compass_core/         # 状态机、intake、报告、证据链
  adapters/             # sls / platform / mysql / redis / elasticsearch
  guards/               # SQL / Redis / ES / SLS / 脱敏 / 查询限制
  knowledge/            # 本地知识库
  memory/               # 本地策略、状态、审计记录
  projects/             # 代码导航地图
  prompts/              # setup、项目注册、查询规划、结果分析流程
  tools/                # setup check、证据图、上下文注入等工具
```

## 首次配置

进入 Compass 目录后，先复制配置模板：

```bash
cd /Users/dongmaowei/.cursor/skills/compass
cp .env.example .env
```

最小可用配置只需要 `CODE_ROOT`，用于让 Compass 找到本机代码仓库：

```dotenv
CODE_ROOT=/Users/<you>/workspace/projects
```

所有数据源都使用数组式 profile 配置：

```dotenv
# 通用格式：ADAPTER[index].FIELD=value
# 通用字段：NAME / ENV / DESC / LINK
```

如果要查 SLS 日志，补充：

```dotenv
SLS_DEFAULT_ENV=prod
SLS[0].NAME=PROD
SLS[0].ENV=prod
SLS[0].DESC=生产环境 SLS 日志 Project
SLS[0].ENDPOINT=cn-hangzhou.log.aliyuncs.com
SLS[0].PROJECT=
SLS[0].ACCESS_KEY_ID=
SLS[0].ACCESS_KEY_SECRET=
SLS[0].LOGSTORE=all
SLS[0].LINK=
```

如果要查 Redis / MySQL / Platform / ES，再按需增加 profile：

```dotenv
REDIS_DEFAULT_PROFILE=FINANCE_TEST
REDIS[0].NAME=FINANCE_TEST
REDIS[0].ENV=test
REDIS[0].DESC=财务测试环境 Redis，钱包/清分相关缓存
REDIS[0].HOST=
REDIS[0].PORT=6379
REDIS[0].PASSWORD=
REDIS[0].DB=30
REDIS[0].LINK=

MYSQL_DEFAULT_PROFILE=FINANCE_TEST
MYSQL[0].NAME=FINANCE_TEST
MYSQL[0].ENV=test
MYSQL[0].DESC=财务测试环境 MySQL/PolarDB
MYSQL[0].HOST=
MYSQL[0].PORT=3306
MYSQL[0].USER=
MYSQL[0].PASSWORD=
MYSQL[0].DATABASE=yunkc_finance
MYSQL[0].LINK=

PLATFORM_DEFAULT_PROFILE=PROD
PLATFORM[0].NAME=PROD
PLATFORM[0].ENV=prod
PLATFORM[0].DESC=生产环境 Doris 查询平台
PLATFORM[0].BASE_URL=http://10.20.0.2:8081
PLATFORM[0].USERNAME=
PLATFORM[0].PASSWORD=

ES_DEFAULT_PROFILE=FINANCE_TEST
ES[0].NAME=FINANCE_TEST
ES[0].ENV=test
ES[0].DESC=财务测试环境 ES
ES[0].URL=
ES[0].USERNAME=elastic
ES[0].PASSWORD=
```

`.env` 是本机私有配置，已被 `.gitignore` 排除，不要提交真实凭证。

## 配置检查

配置完成后运行：

```bash
python3 -m compass_cli setup-check --json
```

检查重点：

- `.env` 是否存在。
- `CODE_ROOT` 是否填写且路径存在。
- Python 版本是否为 3.10+。
- SLS / Platform / MySQL / Redis / ES 哪些 adapter 已可用。
- 哪些 adapter 缺少变量，以及缺失后影响哪条排查轨道。

只做代码排查时，数据源凭证可以先不填；对应 adapter 会标记为不可用，但不会阻断代码轨。

## 配置代码仓库

默认情况下，Compass 会从 `.env` 的 `CODE_ROOT` 找项目。目录结构简单时，只配 `CODE_ROOT` 即可。

如果项目名和目录不一致，或者项目位于多层目录下，复制并修改 `config/code-repos.yaml`：

```bash
cp config/code-repos.yaml.example config/code-repos.yaml
```

示例：

```yaml
code_root: ${CODE_ROOT}

projects:
  omp-shop: OMP/omp-shop
  finance_server: FINANCE/finance_server
  order_server: TRADE/order_server
```

路径规则：

- 绝对路径会直接使用。
- 相对路径会拼接 `CODE_ROOT`。
- 未配置的项目会尝试在 `CODE_ROOT` 下按项目名发现。

## 根据代码地址扫描项目

Compass 需要 `projects/<name>.md` 作为代码导航地图。这个文件会记录 Controller、Service、Mapper、表、Redis key、日志关键字、页面和接口映射。

单个项目注册时，可以这样对 Agent 说：

```text
使用 compass 注册 finance_server，代码路径是 /Users/me/workspace/projects/FINANCE/finance_server
```

如果项目已经在 `config/code-repos.yaml` 中配置，也可以只说：

```text
使用 compass 注册 finance_server
```

扫描规则：

- Java 后端：扫描 Controller -> Service -> Mapper/XML -> Entity -> Redis key -> 日志关键字。
- Vue 前端：扫描 router -> api -> views，建立页面到后端接口的映射。
- React 前端：扫描 pages/router -> api -> components，建立页面到接口的映射。
- Python 服务：扫描入口、路由装饰器、handler/service、依赖文件。

批量扫描前端和关联后端时，可以说：

```text
使用 compass 扫描前端整理知识，项目是 omp-shop，选择 C：前端到后端全链路深度扫描
```

扫描完成后，Agent 应展示将要写入的 `projects/*.md` 内容或 diff，确认后再写入。已有同名文件时，应先展示差异，不要直接覆盖。

## 怎么提问

最有效的问题包含“现象 + 定位实体 + 时间范围”。例如：

```text
使用罗盘排查：用户支付成功但订单没有推进，订单号 123456，今天上午 10:00 到 10:30。
```

```text
使用 compass 查一下：手机号 15921195068 在今天下午切换支付方式后礼品卡不展示。
```

```text
用罗盘看 B 端问题：运营在 omp-shop 账户管理页面给机构充值失败，机构 ID 是 10001，操作时间 2026-04-28 10:20 左右。
```

```text
使用 compass 只走代码轨：帮我从 omp-shop 页面入口追到 finance_server 后端接口，不查线上数据。
```

缺少最小定位实体时，Compass 会先追问，不会直接查：

- C 端充电：`user_id / 手机号 / 订单号` 三选一 + 时间范围。
- 支付/财务：`支付单号 / 订单号 / 用户ID` 三选一 + 时间范围。
- B 端后台：页面/功能 + 操作对象 + 时间范围。
- 日志异常：服务名 + 时间范围 + 异常现象，最好有 `traceId` 或 `tlogId`。

## 推荐排查流程

普通用户只需要自然语言触发 Skill；Agent 会负责调用 CLI Runtime。底层最小流程是：

```bash
python3 -m compass_cli start "用户礼品卡不展示，手机号 15921195068，今天下午" --json
python3 -m compass_cli confirm --mode auto --json
python3 -m compass_cli next --json
```

之后每一步都应该遵循：

```text
scene fact -> action plan -> action complete -> hypothesis add -> conclude -> report -> strategy keep/discard
```

对话中的确认方式：

- 回复 `0` 或“开始/确认/可以”：进入自动模式，Agent 按证据链持续推进。
- 回复 `M`：进入手动模式，每一步查询前都让你确认工具、轨道和查询范围。
- 回复“停/等等/暂停”：中断当前排查，不继续调用 adapter。
- 当 Agent 提示 SQL 风险、外部库、非 `all` logstore 或缺少关键实体时，需要你明确确认或补充信息。

关键命令：

```bash
python3 -m compass_cli scene fact --category entrypoint --name app_payment_ways --value "/app/gun/payment-ways-v2" --source "用户描述/SLS trace" --json

python3 -m compass_cli action plan \
  --action-id A1 \
  --track sls \
  --source SLS \
  --objective "确认财务是否返回礼品卡" \
  --success-criteria "拿到 payment-ways-v2 trace 中财务返回和最终响应差异" \
  --input "query=15921195068 AND payment-ways-v2" \
  --input "time_range=2026-04-25 16:40~17:10" \
  --input "anchor=15921195068" \
  --gate "type=sls" \
  --gate "status=passed" \
  --gate "keyword_source=code" \
  --json

python3 -m compass_cli action complete \
  --action-id A1 \
  --summary "财务返回礼品卡，最终响应无礼品卡" \
  --finding "finance returned subPayWay=3" \
  --supports H2 \
  --json

python3 -m compass_cli report --audience technical
python3 -m compass_cli report --audience business
python3 -m compass_cli report --audience review
```

## 安全规则

- 默认使用 `prod` 排查；只有用户明确指定 `test/uat/测试/预发` 才切换环境。
- 首轮只做问题结构化和方案确认，未确认前禁止调用 adapter。
- Compass 只用于查询、定位和证据链分析，不修改业务代码、不提交代码、不执行修复。
- 禁止任何写操作，例如 `INSERT / UPDATE / DELETE / DROP / SET / DEL`。
- 所有展示给用户的查询结果必须脱敏。
- prod SQL 必须先 `EXPLAIN`，中高风险必须等待用户确认。
- SLS 默认使用 `SLS_LOGSTORE=all`；如需使用其他 logstore，必须先让用户确认。
- SLS 查询必须有高区分度实体锚点，例如订单号、支付单号、手机号、userId、traceId、枪编码、站点名。
- SLS 额外关键词必须来自代码常量、日志模板、SQL 字段或表结构，并用 `keyword_source` 声明，不能凭感觉猜。

Track 门禁：

| track | 必填 input | 必填 gate |
|-------|------------|-----------|
| sls | `query`, `time_range`, `anchor` | `type`, `status`, `keyword_source` |
| sql | `sql`, `env`，prod 还需 `explain_text` | `type`（`status` / `risk` / `explain` 由 runtime 真实评估 EXPLAIN 后写入） |
| code | `repo`, `target` | `type`, `scope` |
| kb | `query` | `type` |
| manual | 无 | 无 |

prod SQL 中/高风险时 runtime 会把 action 标为 `requires_confirmation`，需要 `python3 -m compass_cli action confirm --action-id <id> --note "..."` 后才能 `action complete`。

## 常用命令

```bash
# 检查配置
python3 -m compass_cli setup-check --json

# 结构化一个问题，不实际查询
python3 -m compass_cli intake "订单 123456 支付成功但状态未推进，今天上午" --json

# 搜索本地知识库（同时搜 markdown 文档 + 学习的 yaml 知识）
python3 -m compass_cli kb search "清分单 入金通知" --json

# 录入一条可复用的小颗粒知识（≤300 字）
python3 -m compass_cli kb learn --statement "C 端订单号是 19 位数字，前 14 位是 yyyyMMddHHmmss" --tag order --tag id-rule

# 召回与当前问题最相关的 top-N 通用知识
python3 -m compass_cli kb suggest --query "用户订单号 19 位匹配不到" --top 5

# 列出已学习的全部知识
python3 -m compass_cli kb list

# 登记一笔与故障相关的变更
python3 -m compass_cli change record --type deploy --target order-server@v1.2.3 \
  --description "上线 v1.2.3，含 SQL DDL" --event-at "2026-04-29 13:30" --source jenkins-#1234

# 故障时间线（合并 changes / scene_facts / evidence / actions 的 event_at）
python3 -m compass_cli timeline

# 查看当前状态
python3 -m compass_cli state show --json

# 生成报告
python3 -m compass_cli report --audience technical
```

## v4 增强能力（专业化）

| 能力 | 命令/字段 | 作用 |
|------|-----------|------|
| 通用知识库 | `kb learn / kb suggest / kb list` + `start` 自动召回 | 排查中沉淀小颗粒事实/规则，下次自动注入上下文 |
| 变更登记 | `change record / change list` | 把发布、配置、灰度等变更结构化进 timeline |
| 故障时间线 | `timeline` + report 头部表 | 把 changes / scene_facts / evidence / actions 按 event_at 排序 |
| baseline / diff 事实 | `scene fact --category baseline / --category diff` | 显式登记"正常态 vs 异常态"对比，category=diff 强制有对比词 |
| 根因反思 | `next` 自动输出"反思三问" + `prompts/result-analysis.md` 五问模板 | 防止把"现象"当根因；强制回答"为什么之前没出"和"同类还有谁" |
| 反证条件 | `hypothesis add --falsifiable "<反证>"` | 让结论可证伪；conclude 时若支持假设缺反证会软警告 |
| 止血/根治拆分 | `conclude --mitigation ... --remediation ...` | 区分短期止血与长期根治，避免"建议"混作一团 |
| 未解之谜 | `conclude --unsolved "<开放问题>"` | 显式保留无法在本次定位的疑点 |
| 同类扫描 | `conclude --pattern-scan "<相邻入口/数据/链路>"` | 根因定位后必须列出同类影响面，避免"只解一个、漏一片" |
| 关联假设 | `conclude --hypothesis H1 --hypothesis H2` | 让结论显式引用支持它的假设 |
| 结论质量提示 | conclude 输出 `quality_warnings`，report 渲染表格 | confidence=high 必须有强证据；推断链需有因果连接词；缺 mitigation/remediation/反证条件均会警告 |

## Obsidian 知识库

如果你有 Obsidian 或 Markdown 笔记，可以直接搜索：

```bash
python3 -m compass_cli kb search "入金通知" --root "/Users/you/Obsidian/工作笔记" --json
```

也可以在环境变量里配置默认路径：

```bash
export COMPASS_OBSIDIAN_ROOT="/Users/you/Obsidian/工作笔记"
python3 -m compass_cli kb search "清分单" --json
```

## 故障排查

`setup-check` 提示 `CODE_ROOT` 不存在：

- 检查 `.env` 里的 `CODE_ROOT` 是否是本机真实路径。
- 如果项目在多层目录下，补充 `config/code-repos.yaml`。

SLS 不可用：

- 检查至少存在一个完整 `SLS[index].*` profile。
- 检查 `SLS[index].PROJECT`、`SLS[index].ACCESS_KEY_ID`、`SLS[index].ACCESS_KEY_SECRET` 是否填写。
- 默认 `SLS[index].LOGSTORE=all`，换其他 logstore 前需要用户确认。

项目扫描找不到服务：

- 先确认服务目录真实存在。
- 在 `config/code-repos.yaml` 里显式配置项目名到相对路径。
- 项目名建议和排查时常用服务名保持一致，例如 `finance_server`、`omp-shop`。

报告没有结论：

- 确认是否已经有 `scene fact`、`evidence` 和 `conclude`。
- `conclude` 必须引用真实存在的 evidence id。
- 如果结论后有新信息，使用 `reopen --reason ...` 进入新 revision。

## 验证

```bash
python3 -m pytest tests/test_compass_cli.py tests/test_sls_client.py
```
