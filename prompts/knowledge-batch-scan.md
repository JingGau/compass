# 批量扫描建库

**触发**：用户说「扫描前端整理知识」/「批量注册项目」/「整理 B 端服务」/「批量建库」

## 流程

### Step 1：确认扫描范围

```
AI: 要扫描哪个前端项目？
    默认：omp-shop（路径：${CODE_ROOT}/omp/omp-shop）

    扫描完前端后，是否也扫描关联的后端服务？
    A. 只扫前端（生成 omp-shop.md + 后端服务清单）
    B. 前端 + 后端 Controller 层（生成所有关联服务的 projects/*.md）
    C. 全链路深度扫描（前端 → Controller → Service → Mapper，最完整但耗时）
```

### Step 2：扫描前端代码

按以下顺序扫描，每一步提取关键信息：

**2.1 路由扫描**
- 读 `src/router/` 下所有路由文件
- 提取：路由路径、页面组件路径、页面名称/标题
- 输出：路由 → 页面文件 映射表

**2.2 API 调用扫描**
- 读 `src/api/` 下所有 API 定义文件
- 提取：每个函数的 HTTP 方法、URL 路径、参数
- 输出：API 函数 → 后端接口 映射表

**2.3 页面-API 关联**
- 读 `src/views/` 下的页面组件文件
- 查找组件中引用了哪些 API 函数（import 语句 + 调用点）
- 输出：页面 → API 调用 列表

**2.4 后端服务分组**
- 按 API URL 前缀推断后端服务：
  - `/finance/` → finance_server
  - `/order/` → order_server
  - `/base/` → base_server
  - `/charge/` → charge_server
  - 等等（参考 `config/code-repos.yaml` 中的 `projects` 映射）
- 输出：后端服务清单 + 每个服务对应的接口列表

### Step 3：生成前端项目文件

按 `projects/_convention.md` 前端格式，生成 `projects/omp-shop.md`，包含：
- 页面目录（路由 + 文件路径 + 功能）
- API 调用映射（页面 → API 文件 → 接口列表 → 后端服务）
- 排查路径（问题描述 → 先看前端 → 再看后端）

### Step 4：扫描后端服务（如用户选择 B 或 C）

对 Step 2.4 识别出的每个后端服务：

**4.1 定位代码路径**
- 参考 `config/code-repos.yaml` 的 `projects` 映射，拼接 `code_root` + 相对路径得到绝对路径
- 如果找不到，问用户确认路径

**4.2 扫描 Controller 层**（选项 B 和 C 都执行）
- 扫描 `**/controller/**/*.java`
- 提取 `@RequestMapping`、`@PostMapping`、`@GetMapping` 注解
- 建立：功能域 → Controller 文件 → 接口列表

**4.3 扫描 Service + 数据层**（仅选项 C 执行）
- 扫描 `**/service/**/impl/*.java`，按 Controller 注入关系关联
- 扫描 `**/mapper/*.xml` 或 `**/resources/mapper/**`，提取表名
- 扫描 Service 中的 `log.info`/`log.error`，提取日志关键字
- 扫描 Redis 操作（redisTemplate/StringRedisTemplate），提取 key 模式

**4.4 生成后端项目文件**
- 按 `projects/_convention.md` 后端格式，生成 `projects/<service>.md`
- 每个服务一个文件

### Step 5：展示全量结果，等待用户确认

```
AI: 扫描完成，生成了以下文件：

  1. projects/omp-shop.md — 前端项目
     - 页面: 42 个
     - API 调用: 128 个
     - 关联后端服务: 8 个

  2. projects/finance_server.md — 财务服务
     - Controller: 15 个
     - Service: 23 个
     - 数据表: 18 个

  ... (其他服务)

  要查看具体内容吗？确认后写入。
```

用户确认 → 写入所有文件。
用户要求修改 → 调整后重新展示。

### Step 6：更新 knowledge/b-side/（可选）

如果扫描结果中有 B 端页面信息，同步更新：
- `knowledge/b-side/pages.yaml` — 页面目录
- `knowledge/b-side/page-api-mapping.yaml` — 页面-API 映射
- `knowledge/b-side/api-log-keywords.yaml` — 接口-日志关键字

## 注意事项

- 扫描过程中逐步展示进度，不要静默运行太久
- 如果某个文件解析失败（如路由定义方式不标准），跳过并记录，最后告知用户
- 生成的代码路径使用**相对路径**（相对代码根路径），不用绝对路径
- 每个生成的文件都带元信息（generated_at、source: batch-scan）
- 如果 `projects/` 下已有同名文件，展示 diff 而非直接覆盖
