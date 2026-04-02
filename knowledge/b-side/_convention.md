# B端知识库生成规范

## 生成方式

AI 扫描 omp-shop 前端代码（路由 + API 文件）自动生成，用户确认后落盘。
触发：用户说「注册页面」或「扫描 B端知识」，AI 读 `prompts/knowledge-onboarding.md` 执行。

## 目录结构

```
knowledge/b-side/
├── _convention.md           ← 本文件（生成规范）
├── pages.yaml               ← 页面目录（路由 + 后端服务）
├── page-api-mapping.yaml    ← 页面→接口映射
└── api-log-keywords.yaml    ← 接口→SLS日志关键字
```

## 文件格式

### pages.yaml — 页面目录

```yaml
pages:
  - id: "page-id"                  # 唯一标识，kebab-case
    name: "页面名称"                # 中文显示名
    route: "/xxx/yyy"              # Vue Router 路径
    description: "一句话功能"       # 页面用途
    source_project: "omp-shop"     # 来源前端项目
    backend_services: ["svc1"]     # 调用的后端服务
    generated_at: "2026-04-01"     # 生成日期
```

### page-api-mapping.yaml — 页面到接口映射

```yaml
mappings:
  - page_id: "page-id"             # 关联 pages.yaml 的 id
    apis:
      - method: "GET"              # HTTP 方法
        path: "/xxx/yyy"           # 接口路径
        service: "service_name"    # 后端服务名（与 projects/*.md 对应）
        description: "接口用途"
```

### api-log-keywords.yaml — 接口到日志关键字

```yaml
keywords:
  - api_path: "/xxx/yyy"           # 接口路径
    container: "service-container"  # SLS 容器名
    sls_keywords: ["kw1", "kw2"]   # 正常日志关键字
    error_keywords: ["err1"]       # 异常日志关键字
```

## 生成规则

1. **扫描入口**：`src/router/` 提取路由和页面组件路径
2. **API 提取**：`src/api/` 提取所有 HTTP 调用（URL + Method）
3. **服务归属**：按 URL 前缀推断后端服务（`/finance/` → finance_server）
4. **日志关键字**：扫描后端 Service 的 `log.info`/`log.error` 提取（需 projects/*.md 已注册）
5. **每条记录标明来源**：`generated_at` + `source_project`，区分扫描生成 vs 手动补充
6. **页面 id 全局唯一**：不同知识文件通过 page_id 串联

## 更新触发

- 用户说「注册页面」→ 扫描新增页面，追加到已有文件
- 用户说「扫描 B端知识」→ 全量重新扫描，覆盖生成
- 排查中发现新接口 → 手动追加到对应文件

## 与 C端的区别

| 维度 | B端 | C端 |
|------|-----|-----|
| 来源项目 | omp-shop（Vue 前端） | guan-zhong 网关 + App 行为 |
| 知识粒度 | 页面 → API → 服务 | 流程 → 接口 → 日志 |
| 核心文件 | pages + mapping + keywords | flows + keywords + journey |
| 扫描依赖 | 前端代码（路由 + API 文件） | 后端代码 + 业务文档 |
