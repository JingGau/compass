# Legacy v3 Harness（已停用）

本目录是 Compass v3 阶段的 step-based harness（`current_step` + `checkpoints` + `pending_confirmations`）。

它已经被 v4 phase-based runtime（`compass_cli` + `compass_core/runtime.py`：`awaiting_confirmation → action_ready → evidence_collecting → concluded`）取代，**不再维护、不再被主流程加载**，只为保留代码 history 与历史 demo 作存档。

## 目录构成

```text
legacy/
  tools/
    session_state.py        # step+checkpoints 状态机
    context_injector.py     # 旧 prompt 注入
    sensors.py              # 旧流程偏离/日志轨/上下文 sensor
    compressor.py           # 旧 step 内容压缩
  scripts/
    e2e_harness_demo.py     # 旧 8 步 demo
    harness_protocol_runner.py  # 旧 protocol runner
  tests/
    test_tools_session_state.py
    test_tools_sensors.py
    test_harness_protocol_runner.py
```

## 不要再引用这些模块

如果在 `compass_cli` / `compass_core` 中看到 `from tools.session_state import ...`、`from tools.sensors import ...`、`from tools.context_injector import ...`、`from tools.compressor import ...`，那是历史残留，应当替换或删除。

新的等价能力在：

| 旧 v3 模块 | 新 v4 等价物 |
|------------|--------------|
| `tools/session_state.SessionState` | `compass_core/state.py`（`read_or_init_state` / `write_state`）+ `compass_core/runtime.py` 的 phase 状态机 |
| `tools/context_injector.ContextInjector` | 直接读 `references/*.md` + `prompts/*.md`（按需读取，不再做 step 编排） |
| `tools/sensors.sense_*` | runtime 内部的 `_require_phase` / `_require_existing_evidence` / `_validate_*` |
| `tools/compressor.compress` | 不再需要——v4 通过最小命令链控制上下文 |

## 状态文件冲突处理

v3 写 `memory/session-state.yaml`（YAML），v4 写同名文件但用 JSON。两者已互不兼容。如果你看到本机 `memory/session-state.yaml` 既有 `current_step` / `checkpoints` 又有 `flow.phase` / `scene_facts`，是 v3 v4 互写过同一文件造成的污染，应直接删除该文件后由 v4 重新生成。
