# Adapter 开发约定

本文档是 AI 自主创建新 adapter 的唯一规范。严格遵循以下约定，确保新 adapter 与系统无缝集成。

## 目录结构（必须完整）

```
adapters/<name>/
├── README.md          # 必须。给 AI 看的使用指引（接口文档、语法、注意事项）
├── client.py          # 必须。Python 客户端实现
├── config.yaml        # 必须。连接参数（含 enabled 开关）
└── requirements.txt   # 必须。Python 依赖
```

## client.py 规范

**必须实现的方法：**

```python
def __init__(self, config_path: Optional[str] = None):
    # 从 config.yaml 加载配置，config_path 默认为同目录下的 config.yaml

def health_check(self) -> dict:
    # 验证连通性，返回标准结构，不抛出异常
    # {"adapter": "...", "status": "ok|error|disabled", "latency_ms": 12, "environment": "prod", "error": None}
```

**返回格式统一：**

```python
# 所有业务方法必须返回 dict，不得抛出未捕获的异常
{"success": True,  "data": any,  "error": None}
{"success": False, "data": None, "error": "错误说明"}
```

**其他约定：**
- 从 `Path(__file__).parent / "config.yaml"` 加载配置（支持相对路径）
- 敏感操作（如写入）不提供方法，排查场景只读
- 支持 `if __name__ == "__main__":` 独立测试块

## config.yaml 规范

```yaml
enabled: true   # 第一行必须是 enabled 开关

# 敏感值用 YOUR_XXX 占位（本系统中直接填真实值）
# 必须有 default_profile 或 default_env 指定默认连接
```

## README.md 规范

必须包含：
1. **能力概述**：这个 adapter 做什么
2. **使用方法**：每个方法的说明、参数、返回格式
3. **注意事项**：限制、坑、必须知道的背景知识
4. **常用示例**：AI 在排查时最可能用到的调用方式

## 注册步骤

创建完文件后：
1. 在 `SKILL.md` 的能力注册表中加一行，状态标记 `⏳ 待验证`
2. 运行 `python adapters/<name>/client.py` 验证 health_check
3. 通过后将状态改为 `✅ 可用`

## 无损引入保证

- 新 adapter 是独立目录，不修改任何已有文件（除 SKILL.md 注册表加一行）
- config.yaml 中 `enabled: false` 可随时禁用
- 删除目录 + 删除注册表对应行即可完全回滚
