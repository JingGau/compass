# Harness 发版前检查清单

## 1. 结构完整性

- `python3 scripts/check_harness_ready.py` 通过
- `tools/` 四件套和 `tool_protocol.md` 均存在
- `guards/flow-checkpoints.md` 存在且与流程步骤一致

## 2. 代码与静态检查

- `python3 -m py_compile tools/*.py adapters/*/client.py adapters/base.py` 通过
- `python3 -m unittest discover -s tests -p 'test_tools_*.py'` 通过
- IDE lint 无新增错误

## 3. 流程功能检查

- `python3 scripts/e2e_harness_demo.py` 全流程跑通（Step1 -> Step8）
- `assert_step_complete` 可阻断缺失检查点
- `sense_log_track_progress` 未完成时返回阻断信号

## 4. 安全与门禁

- `guards/context-limits.yaml` 为 token 阈值模型
- `guards/query-limits.yaml` 含 `context_sensor` 阈值
- `prompts/query-planning.md` 和 `SKILL.md` 均声明工具协议门禁

## 5. Adapter 标准化

- 5 个 adapter 的 `health_check()` 返回结构统一：
  - `adapter`
  - `status`
  - `latency_ms`
  - `environment`
  - `error`

## 6. 文档与配置

- `docs/compass-harness-v3.md` 已包含实现状态同步段落
- `.env.example` 包含 Harness 相关可选阈值项

