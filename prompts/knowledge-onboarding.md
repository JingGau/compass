# 知识入驻工作流（单页面/单功能）

**触发**：用户说「注册页面」/「添加知识」/「让 XX 页面加入知识库」

> 批量扫描所有服务请使用 `knowledge-batch-scan.md`，本流程适用于单个页面或功能的知识入驻。

---

## 前置检查

1. 确认 `knowledge/b-side/` 下三个 YAML 文件存在：
   - `pages.yaml`
   - `page-api-mapping.yaml`
   - `api-log-keywords.yaml`
2. 如果不存在 → 先创建空骨架（参考现有文件格式）

---

## Step 1 — 收集信息

向用户询问以下信息（能给多少给多少，缺的 AI 探索补全）：

```markdown
> 请提供以下信息（不确定的可以留空，我来帮你查）：
>
> | # | 信息 | 示例 |
> |---|------|------|
> | 1 | 页面名称或功能描述 | 「车队管理」「钱包充值页面」 |
> | 2 | 页面路由（如果知道） | `/customerManagement/vehicleFleetManagement` |
> | 3 | 关联的后端服务（如果知道） | `finance_server`、`base_server` |
```

---

## Step 2 — 探索前端代码（omp-shop）

### 2.1 定位页面路由

在 omp-shop 中搜索：
- `src/router/` 目录下查找匹配的路由配置
- 搜索用户描述的关键词（如「车队」→ 搜中文 or 拼音）
- 找到后记录：`route path`、`component path`、`meta.title`

### 2.2 提取 API 调用

读取页面 `.vue` 文件及其引用的 `.js` 文件：
- 搜索 `axios`、`request`、`this.$http`、`api.` 等调用
- 提取每个 API 的：
  - HTTP Method（GET/POST/PUT/DELETE）
  - URL 路径
  - 请求参数名（从 `params` 或 `data` 中提取）

### 2.3 整理结果

```yaml
page:
  id: "fleet-management"
  name: "车队管理"
  route: "/customerManagement/vehicleFleetManagement"
  description: "车队CRUD、司机管理"
  source_project: "omp-shop"
  component: "src/views/customerManagement/vehicleFleetManagement/index.vue"

apis:
  - method: "GET"
    path: "/base/fleet/list"
    params: ["pageNum", "pageSize", "organizationName"]
  - method: "POST"
    path: "/base/fleet/create"
    params: ["name", "orgId", "walletType"]
```

---

## Step 3 — 推断后端链路

### 3.1 定位 Controller

根据 API path，在后端项目中搜索对应的 Controller：
- 搜索 `@RequestMapping`、`@GetMapping`、`@PostMapping` 中包含 API 路径的
- 记录 Controller 类名和方法名

### 3.2 追踪 Service 层

从 Controller 方法中找到调用的 Service：
- 记录 Service 类名和方法名
- 读 Service 代码，提取：
  - 调用的 Mapper/DAO 方法 → 涉及的数据库表
  - 调用的 Redis 操作 → Redis key 模式
  - `log.info` / `log.error` 中的关键字

### 3.3 推断 SLS 容器名

- 从项目的部署配置或项目名推断容器名
- 例：`finance_server` → `finance-server`
- 不确定时标注「待确认」

### 3.4 整理结果

```yaml
backend:
  service: "base_server"
  controller: "FleetController#list"
  service_method: "FleetServiceImpl#queryFleetList"
  tables: ["t_organization", "t_fleet_driver"]
  redis_keys: []
  log_keywords: ["queryFleetList", "FleetService"]
  error_keywords: ["FleetException", "OrganizationNotFound"]
  container: "base-server"
```

---

## Step 4 — 更新知识库

### 4.1 准备变更

将 Step 2-3 的结果映射到三个 YAML 文件的条目格式：

| 文件 | 新增内容 |
|------|---------|
| `pages.yaml` | 一条 page 记录（id, name, route, description, backend_services） |
| `page-api-mapping.yaml` | 一组 API mapping（page_id → apis 列表） |
| `api-log-keywords.yaml` | 每个 API 的日志关键字（api_path, container, sls_keywords, error_keywords） |

### 4.2 检查重复

- 按 `page_id` 检查 `pages.yaml` 中是否已存在
- 已存在 → 展示 diff（旧值 vs 新值），问用户是否更新
- 不存在 → 新增

### 4.3 展示变更给用户确认

```markdown
> **知识入驻预览**
>
> **新增页面**：车队管理
>
> | 文件 | 变更 |
> |------|------|
> | `pages.yaml` | +1 条：fleet-management |
> | `page-api-mapping.yaml` | +2 个 API 映射 |
> | `api-log-keywords.yaml` | +2 组日志关键字 |
>
> 确认写入？ **[确认]** / **[修改]** / **[取消]**
```

---

## Step 5 — 写入并验证

1. 用户确认 → 追加到对应 YAML 文件
2. 每条记录添加 `generated_at` 时间戳
3. 写入完成后回读验证 YAML 格式是否正确
4. 告知用户「已入驻，下次排查涉及该页面时会自动关联」

---

## 错误处理

| 场景 | 处理 |
|------|------|
| 找不到匹配的路由 | 告知用户「未在 omp-shop 中找到该页面」，问用户是否手动提供路由 |
| 找不到后端 Controller | 记录 API path，跳过后端链路推断，仅入驻前端知识 |
| YAML 写入格式错误 | 回滚本次变更，提示错误信息 |
| 页面已存在 | 展示 diff，问用户是否覆盖更新 |
