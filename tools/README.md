# Harness Tools

本目录提供 Compass v3 的 Harness 工具层，实现流程编排与运行时门禁。

## 文件说明

- `session_state.py`：会话状态机，负责读写状态、检查点、步骤推进。
- `context_injector.py`：按步骤注入最小上下文包。
- `sensors.py`：流程偏离、查询质量、上下文体积、日志轨完成度检测。
- `compressor.py`：步骤级摘要压缩。
- `action_cards.py`：执行前、门禁、执行后的结构化卡片协议。
- `sql_gate.py`：解析 SQL EXPLAIN 并输出结构化风险判定。
- `evidence_graph.py`：沉淀页面、接口、方法、表、日志等证据关系。
- `setup_check.py`：安装后检查 `.env`、`CODE_ROOT` 和 adapter 凭证配置状态。
- `tool_protocol.md`：工具调用协议（必须遵守）。

## 设计原则

1. 工具返回结构化 JSON 信号，调用方按信号执行，不做隐式跳过。
2. 任意步骤推进前必须通过 `assert_step_complete`。
3. 只有通过 `session_state` 更新 `memory/session-state.yaml`，禁止直接手改。
