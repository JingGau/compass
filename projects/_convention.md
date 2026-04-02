# 项目注册约定

本文档是 AI 自主注册项目的唯一规范。每个项目一个 `.md` 文件，作为 **代码导航地图**，告诉 AI 排查时去哪读活代码。

所有代码路径基于 `config/code-repos.yaml` 解析：
- **code_root**：从 `.env` 的 `CODE_ROOT` 读取，每个开发者设置自己的代码仓库根目录
- **路径解析**：AI 读 `config/code-repos.yaml` 的 `projects` 映射 → 拼接 `code_root` + 相对路径得到绝对路径
- **自动发现**：项目不在 `projects` 映射中 → AI 在 `code_root` 下递归扫描同名子目录
- **`代码根路径` 字段**：写相对于 `code_root` 的路径，按你实际的目录结构来：
  - 有分组目录：`FINANCE/finance_server` 或 `TRADE/order-server`
  - 无分组平铺：`finance_server` 或 `order-server`

## 插件化规则

- 加一个 `projects/<name>.md` = 注册一个项目，不修改任何其他文件
- 删一个 `.md` = 注销，不影响其他项目
- 文件名用项目实际目录名（如 `finance_server.md`、`omp-shop.md`）

## 后端项目格式（Java / Python 等）

```markdown
# {项目名称}

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | {Java 后端 / Python 服务 / ...} |
| 代码根路径 | {相对路径（相对于 config/code-repos.yaml 的 code_root），如 FINANCE/finance_server} |
| SLS 容器名 | {如 finance-server} |
| 关联数据库 | {如 yunkc_finance（MySQL）} |
| 所属端 | {B端 / C端 / B端+C端} |
| 一句话职责 | {如：财务核心服务：钱包、支付、发票、对账} |

## 代码导航

### Controller 层（接口入口）
| 功能域 | 文件路径（相对代码根路径） | 核心接口 |
|--------|--------------------------|---------|
| {功能} | {src/main/.../XxxController.java} | {POST /xxx, GET /yyy} |

### Service 层（业务逻辑）
| 功能域 | 文件路径（相对代码根路径） | 职责 |
|--------|--------------------------|------|
| {功能} | {src/main/.../impl/XxxServiceImpl.java} | {一句话说明} |

### 数据层
| 表 / 缓存 | 用途 | Mapper/配置路径 |
|-----------|------|----------------|
| {t_xxx} | {说明} | {src/main/resources/mapper/XxxMapper.xml} |
| {redis:key:pattern} | {说明} | {所在 Service 类} |

## 排查路径

### 常见问题 → 从这里开始读代码
| 问题描述 | 入口代码（类#方法） | 关联 adapter |
|---------|-------------------|-------------|
| {问题} | {XxxServiceImpl#method} | {sls + mysql + ...} |

### SLS 日志关键字
| 场景 | 关键字 |
|------|--------|
| {场景} | {keyword1, keyword2} |

## 元信息
- generated_at: {日期}
- generated_by: {AI auto-scan / manual}
- last_verified: {日期}
- source: {batch-scan / single-register / manual}
```

## 前端项目格式（Vue / React 等）

前端项目的代码导航重点是 **页面 → API → 后端服务** 的映射链：

```markdown
# {项目名称}

## 基本信息

| 属性 | 值 |
|------|----|
| 服务类型 | {前端 Vue / React / ...} |
| 代码根路径 | {相对路径（相对于 config/code-repos.yaml 的 code_root），如 Front/omp-shop} |
| 所属端 | B端 |
| 一句话职责 | {如：商户管理后台前端} |
| 技术栈 | {Vue 2 + Element UI / ...} |

## 代码导航

### 页面目录
| 页面名称 | 路由 | 文件路径（相对代码根路径） | 功能 |
|---------|------|--------------------------|------|
| {页面} | {/xxx/yyy} | {src/views/xxx/index.vue} | {功能说明} |

### API 调用（页面 → 后端接口）
| 页面 | API 文件路径 | 接口列表 | 后端服务 |
|------|------------|---------|---------|
| {页面} | {src/api/xxx.js} | {POST /finance/xxx, GET /base/yyy} | {finance_server, base_server} |

## 排查路径

### B端问题 → 前端到后端追溯
| 问题描述 | 先看前端 | 再看后端 |
|---------|---------|---------|
| {问题} | {src/api/xxx.js} | → {service_name} (projects/{service_name}.md) |

## 元信息
- generated_at: {日期}
- generated_by: {AI auto-scan / manual}
- last_verified: {日期}
- source: {batch-scan / single-register / manual}
```

## AI 生成流程

### 后端项目扫描策略

1. 读目录结构，识别项目类型（Maven/Gradle → Java，requirements.txt → Python）
2. **Controller 层**：扫描 `**/controller/**/*.java`，提取 `@RequestMapping`/`@PostMapping`/`@GetMapping` 注解
3. **Service 层**：扫描 `**/service/**/impl/*.java`，按 Controller 中注入的 Service 关联
4. **数据层**：扫描 `**/mapper/*.xml` 或 `**/repository/**/*.java`，提取表名
5. **日志关键字**：扫描 Service 中的 `log.info`/`log.error` 提取标识符
6. **排查路径**：根据 Controller → Service 的调用关系，为每个核心功能推断"问题 → 入口"映射

### 前端项目扫描策略

1. 读 `src/router/` 提取路由定义和页面组件路径
2. 读 `src/api/` 提取所有 API 调用（URL、HTTP 方法）
3. 读 `src/views/` 中的组件文件，关联使用了哪些 API
4. 按 API URL 前缀推断后端服务归属（`/finance/` → finance_server）
5. 生成页面 → API → 后端服务的三层映射

## 无损引入保障

- 新项目文件是独立 `.md`，不修改任何已有文件
- 删除文件即回滚，零副作用
- 排查流程中 `projects/` 为空时正常降级（跳过代码理解步骤，直接查询）
