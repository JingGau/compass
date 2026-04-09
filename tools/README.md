# Harness Tools

本目录提供 Compass v3 的 Harness 工具层，实现流程编排与运行时门禁。

## 文件说明

- `session_state.py`：会话状态机，负责读写状态、检查点、步骤推进。
- `context_injector.py`：按步骤注入最小上下文包。
- `sensors.py`：流程偏离、查询质量、上下文体积、日志轨完成度检测。
- `compressor.py`：步骤级摘要压缩。
- `tool_protocol.md`：工具调用协议（必须遵守）。

## 设计原则

1. 工具返回结构化 JSON 信号，调用方按信号执行，不做隐式跳过。
2. 任意步骤推进前必须通过 `assert_step_complete`。
3. 只有通过 `session_state` 更新 `memory/session-state.yaml`，禁止直接手改。
