# Tools

本目录提供 v4 phase-based runtime 仍在使用的工具层。其它 v3 step-based 模块（`session_state.py` / `context_injector.py` / `sensors.py` / `compressor.py` / `tool_protocol.md`）已停用并迁到 `legacy/`，请参考 `legacy/README.md`。

## 文件说明

- `action_cards.py`：执行前 / 门禁 / 执行后的结构化卡片协议（`InvestigationAction` / `SafetyGateResult` / `ActionResult`），由 `compass_core.runtime` 与外层 Agent 共同使用。
- `sql_gate.py`：解析 Doris/MySQL `EXPLAIN`，输出 low/medium/high 风险判定。`compass_core.runtime.plan_action(track='sql')` 在 prod 环境会强制调用本模块；Agent 不能再通过自报 `gate.status=passed` 绕过。
- `evidence_graph.py`：沉淀页面、接口、方法、表、key、traceId 等证据节点关系，被 runtime 在 `complete_action` / `record_action_result` 时自动写入。
- `python_env.py`：自动探测可用 Python（COMPASS_PYTHON / .venv / VIRTUAL_ENV / sys.executable / PATH），生成 venv 与依赖安装建议。
- `setup_check.py`：检查 `.env`、`CODE_ROOT`、各 adapter profile 是否齐全；`compass_cli setup-check` 的实现入口。
- `env_config.py`：`.env` 加载与整数环境变量读取的小工具。

## 设计原则

1. 工具返回结构化 dataclass / dict，调用方按字段判断行为，不做隐式跳过。
2. 状态读写只能经由 `compass_core/state.py` 的 `read_or_init_state` / `write_state`，禁止直接手改 `memory/session-state.yaml`。
3. 安全门禁的真值由本目录工具产出（如 `sql_gate.assess_sql_explain`），上层 runtime 必须以此为准、不允许信任 Agent 自报。
