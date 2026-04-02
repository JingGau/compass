# 项目注册工作流

**触发**：用户说「注册项目」/「添加项目」/「注册 XX 服务」/「让 XX 加入排查」

## 核心目标

为指定项目生成 `projects/<name>.md` **代码导航地图**，让排查时 AI 能按路径读活代码。

## 流程

### Step 1：收集基础信息

```
AI: 要注册哪个项目？
    - 项目名称 / 服务名？
    - 代码路径？（提供后可深度扫描，不提供则手动录入）
    - 这个服务主要做什么？（一句话）
```

如果用户只说了服务名（如"finance_server"），AI 应：
1. 先在 `config/code-repos.yaml` 的 `projects` 映射中查找对应路径，拼接 `code_root` + 相对路径
2. 找到 → 自动使用，不再追问
3. 找不到 → 请用户提供路径

### Step 2：识别项目类型

根据代码目录判断：
- 有 `pom.xml` / `build.gradle` → **Java 后端**
- 有 `package.json` + `src/views/` → **前端 Vue**
- 有 `package.json` + `src/pages/` → **前端 React**
- 有 `requirements.txt` / `pyproject.toml` → **Python 服务**

### Step 3：按类型深度扫描代码

#### Java 后端项目

**3.1 Controller 层**
- 扫描 `**/controller/**/*.java`
- 提取 `@RequestMapping`/`@PostMapping`/`@GetMapping`/`@DeleteMapping` 注解
- 记录：功能域、文件路径（相对代码根路径）、接口列表

**3.2 Service 层**
- 扫描 `**/service/**/impl/*.java`
- 按 Controller 中 `@Autowired` / `@Resource` 注入的 Service 关联
- 记录：功能域、文件路径、一句话职责

**3.3 数据层**
- 扫描 `**/mapper/*.xml` 或 `**/resources/mapper/**/*.xml`，提取 namespace 和涉及的表名
- 扫描 `**/entity/**/*.java` 或 `**/model/**/*.java`，识别 `@TableName` 注解
- 扫描 Service 中的 Redis 操作（`redisTemplate`/`StringRedisTemplate`），提取 key 模式
- 记录：表名/缓存key → 用途 → Mapper 路径

**3.4 排查线索提取**
- 扫描 Service 中的 `log.info`/`log.error`/`log.warn`，提取日志标识符
- 从 k8s 部署配置或 application.yml 推断 SLS 容器名
- 从 pom.xml / application.yml 识别数据库连接名（推断关联数据库）
- 为每个核心功能域推断「问题 → 入口代码」映射

#### 前端项目

执行 `prompts/knowledge-batch-scan.md` 中 Step 2 的前端扫描策略（路由 → API → 页面关联 → 服务分组）。

#### Python 服务

- 读入口文件（`main.py`/`app.py`/`server.py`）
- 读路由定义（FastAPI/Flask 的路由装饰器）
- 读 `requirements.txt` 了解依赖
- 扫描 handler/service 目录，提取业务逻辑文件

### Step 4：生成项目文件

按 `projects/_convention.md` 定义的格式，生成完整的 `projects/<name>.md`。

**必须包含的四个部分**：
1. 基本信息（服务类型、代码路径、容器名、数据库、职责）
2. 代码导航（Controller → Service → 数据层，含文件路径）
3. 排查路径（常见问题 → 入口代码 → 关联 adapter）+ SLS 关键字
4. 元信息（生成时间、来源）

### Step 5：展示给用户确认

```
AI: 我根据代码扫描生成了 projects/finance_server.md，包含：
    - Controller: 15 个功能域
    - Service: 23 个业务类
    - 数据表: 18 张
    - 排查路径: 8 个常见问题入口

    [展示完整内容]

    确认写入？
```

用户确认 → 写入文件。
用户修改 → 调整后重新展示。

### Step 6：检查关联（可选）

如果注册的是后端服务，检查 `projects/omp-shop.md`（如果存在）：
- 是否有页面调用了这个服务的接口
- 如果有，建议更新 omp-shop.md 的排查路径部分

## 注意事项

- 代码路径一律使用**相对路径**（相对代码根路径），基本信息中的代码根路径用绝对路径
- 如果已有同名 `projects/<name>.md`，先展示 diff 再确认覆盖
- 扫描大型项目时分步展示进度
- 每个生成的文件必须带元信息
