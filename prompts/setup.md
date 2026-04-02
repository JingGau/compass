# 首次配置引导

当用户触发「配置」「setup」「初始化」或检测到 `.env` 不存在时，执行此引导流程。

## 触发条件

- 用户说「配置」「初始化」「setup」
- 或首次运行 Compass 时检测到 `.env` 不存在

## 配置流程

### Step 1 — 检测 MCP 连接信息

1. 读取 `~/.claude.json` 的 `mcpServers` 字段
2. 从中提取各服务的连接参数：

| MCP Server | 提取的信息 | 对应 .env 变量 |
|-----------|-----------|---------------|
| `mysql-client` | host, port, user, password, database | `MYSQL_POLARDB_TEST_*` |
| `redis-client` | host, port, password, db | `REDIS_FINANCE_TEST_*` |
| `elasticsearch-client` | url, username, password | `ES_TEST_FINANCE_*` |
| `sls-client` | access_key_id, access_key_secret, endpoint, project | `SLS_ACCESS_KEY_*` |
| `query-platform-client` | headers 中的 X-User-Name, X-Password | `PLATFORM_*` |

3. 如果用户没有配置某个 MCP → 告知用户该 adapter 将不可用，可后续补充
4. 将提取的参数写入 `.env`（从 `.env.example` 复制后填写）

### Step 2 — 配置代码仓库路径

**必须问用户**：

```
请提供你的代码仓库根目录（可以给多个，用逗号分隔）：
例如：/Users/xxx/workspace/projects
```

- 用户给出的路径 → 写入 `.env` 的 `CODE_ROOT`
- 如果用户给了多个路径，以第一个为 `CODE_ROOT`，其余的记录到 `config/code-repos.yaml` 中用绝对路径

### Step 3 — 扫描并生成项目文件

**3.1 扫描代码目录**：

1. 遍历 `CODE_ROOT` 下所有子目录（含一级和二级子目录）
2. 识别项目类型：
   - 存在 `pom.xml` 或 `build.gradle` → Java 后端
   - 存在 `package.json` + `vue.config.js` → Vue 前端
   - 存在 `requirements.txt` 或 `setup.py` → Python
   - 其他 → 记录但跳过深度扫描
3. 输出发现的项目清单，让用户确认

**3.2 生成项目导航文件**：

对每个识别到的项目，按 `projects/_convention.md` 格式生成 `projects/<name>.md`：
- Java 后端：扫描 Controller → Service → Mapper 层
- Vue 前端：扫描 router → api → views
- 记录日志关键字、涉及的数据表

**3.3 生成 config/code-repos.yaml**：

根据扫描结果，生成 `config/code-repos.yaml`：
```yaml
code_root: ${CODE_ROOT:-<用户给的默认值>}

projects:
  <name>:
    path: <相对路径或绝对路径>
    description: "<AI 从代码中提取的一句话描述>"
```

### Step 4 — 关键项目深度扫描（可选）

询问用户：

```
以下项目对排查很重要，是否要深度扫描？
  1. B端后台前端（如 omp-shop）— 路径？
  2. C端网关入口（如 guan-zhong）— 路径？
  输入编号 + 路径，或回车跳过
```

如果用户提供路径：
- 深度扫描 API 映射、页面路由、后端调用关系
- 生成更详细的导航文件

### Step 5 — 验证连接

直接用 MCP 工具测试连通性：

| 工具 | MCP 工具 | 测试命令 |
|------|---------|---------|
| Platform | `mcp__mysql-client__*` | `list_connections` |
| SLS | `mcp__sls-client__*` | `list_logstores` |
| MySQL | `mcp__mysql-client__*` | `list_connections` |
| Redis | `mcp__redis-client__*` | `list_connections` |
| ES | `mcp__elasticsearch-client__*` | `list_connections` |

输出配置报告：

| Adapter | 连接状态 | 可用环境 |
|---------|---------|---------|
| SLS | ✅ | prod, test, uat |
| MySQL | ✅ | test |
| Redis | ✅ | test |
| ES | ✅ | test |
| Platform | ✅ | prod |

### Step 6 — 完成

告知用户：
- 配置文件位置：`.env`、`config/code-repos.yaml`
- 项目导航文件数量
- 可用的 adapter 和环境
- 后续可直接使用 Compass 排查问题

## 更新已有配置

用户说「更新配置」「重新配置」时：
1. 读取现有 `.env` 和 `config/code-repos.yaml`
2. 问用户要更新哪部分（凭证 / 代码路径 / 项目列表）
3. 只更新指定部分，不影响其他配置
