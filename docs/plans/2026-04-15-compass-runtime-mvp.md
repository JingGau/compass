# Compass Runtime MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the first runnable Compass runtime for the log-first investigation path, using replay-backed execution and a thin skill bridge.

**Architecture:** Add a new runtime layer that owns flow orchestration, replay-backed adapter dispatch, evidence extraction, and hypothesis generation, while keeping the existing skill assets as the user-facing shell. Implement the log-first path end to end before integrating real adapters or expanding to other tracks.

**Tech Stack:** Python 3.12, PyYAML, unittest/pytest style tests, existing Compass adapters, YAML-based memory and replay fixtures

---

### Task 1: Create runtime package skeleton

**Files:**
- Create: `runtime/__init__.py`
- Create: `runtime/core/__init__.py`
- Create: `runtime/models/__init__.py`
- Create: `runtime/tracks/__init__.py`
- Create: `runtime/adapter_runtime/__init__.py`
- Create: `runtime/diagnosis/__init__.py`
- Create: `runtime/replay/__init__.py`
- Create: `runtime/skill_bridge/__init__.py`

**Step 1: Write the failing test**

```python
def test_runtime_package_imports():
    import runtime
    import runtime.core
    import runtime.models
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_runtime_imports.py -v`
Expected: FAIL because the runtime package does not exist yet

**Step 3: Write minimal implementation**

Create the package directories and empty `__init__.py` files so the runtime namespace can be imported.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_runtime_imports.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime tests/test_runtime_imports.py
git commit -m "feat: add runtime package skeleton"
```

### Task 2: Define shared runtime models

**Files:**
- Create: `runtime/models/session.py`
- Create: `runtime/models/logs.py`
- Create: `runtime/models/diagnosis.py`
- Create: `runtime/models/replay.py`
- Modify: `runtime/models/__init__.py`
- Test: `tests/test_runtime_models.py`

**Step 1: Write the failing test**

```python
def test_investigation_session_defaults():
    from runtime.models.session import InvestigationSession

    session = InvestigationSession(session_id="sess-1", query_text="用户支付失败")

    assert session.current_phase == "Intake"
    assert session.evidence == []
    assert session.hypotheses == []
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_runtime_models.py::test_investigation_session_defaults -v`
Expected: FAIL because the model does not exist yet

**Step 3: Write minimal implementation**

Implement dataclasses for:

- `InvestigationSession`
- `LogHit`
- `TraceChain`
- `Evidence`
- `Hypothesis`
- `ReplayCase`

Use explicit defaults for mutable fields.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_runtime_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/models tests/test_runtime_models.py
git commit -m "feat: add runtime data models"
```

### Task 3: Introduce FlowEngine phases and transitions

**Files:**
- Create: `runtime/core/phases.py`
- Create: `runtime/core/flow_engine.py`
- Modify: `runtime/core/__init__.py`
- Test: `tests/test_flow_engine.py`

**Step 1: Write the failing test**

```python
def test_flow_engine_starts_at_intake():
    from runtime.core.flow_engine import FlowEngine
    from runtime.models.session import InvestigationSession

    engine = FlowEngine()
    session = InvestigationSession(session_id="sess-1", query_text="订单异常")

    assert engine.current_phase(session) == "Intake"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_flow_engine.py::test_flow_engine_starts_at_intake -v`
Expected: FAIL because the flow engine does not exist yet

**Step 3: Write minimal implementation**

Implement:

- runtime phase names
- allowed phase ordering for the log-first path
- `current_phase(session)`
- `advance(session, result)` with guardrails against invalid transitions

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_flow_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/core tests/test_flow_engine.py
git commit -m "feat: add runtime flow engine"
```

### Task 4: Build unified adapter runtime with replay backend

**Files:**
- Create: `runtime/adapter_runtime/base.py`
- Create: `runtime/adapter_runtime/replay_backend.py`
- Create: `runtime/adapter_runtime/runtime.py`
- Modify: `runtime/adapter_runtime/__init__.py`
- Test: `tests/test_replay_adapter_runtime.py`

**Step 1: Write the failing test**

```python
def test_replay_backend_returns_registered_response():
    from runtime.adapter_runtime.runtime import AdapterRuntime
    from runtime.adapter_runtime.replay_backend import ReplayBackend

    runtime = AdapterRuntime(backend=ReplayBackend({"sls.search_logs": [{"message": "timeout"}]}))
    result = runtime.invoke("sls", "search_logs", {"keyword": "timeout"})

    assert result[0]["message"] == "timeout"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_replay_adapter_runtime.py::test_replay_backend_returns_registered_response -v`
Expected: FAIL because the replay backend does not exist yet

**Step 3: Write minimal implementation**

Implement a unified adapter runtime that:

- accepts a backend object
- invokes adapter operations by `adapter + operation`
- supports a replay backend keyed by scenario response identifiers

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_replay_adapter_runtime.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/adapter_runtime tests/test_replay_adapter_runtime.py
git commit -m "feat: add replay-backed adapter runtime"
```

### Task 5: Add replay case schema and loader

**Files:**
- Create: `runtime/replay/schema.py`
- Create: `runtime/replay/loader.py`
- Create: `runtime/replay/cases/log_timeout_case.yaml`
- Modify: `runtime/replay/__init__.py`
- Test: `tests/test_replay_loader.py`

**Step 1: Write the failing test**

```python
def test_replay_case_loader_reads_case_file():
    from runtime.replay.loader import load_case

    case = load_case("runtime/replay/cases/log_timeout_case.yaml")

    assert case.case_id == "log-timeout-case"
    assert case.expected_track == "log"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_replay_loader.py::test_replay_case_loader_reads_case_file -v`
Expected: FAIL because the replay loader and case schema do not exist yet

**Step 3: Write minimal implementation**

Implement:

- replay case dataclass parsing
- YAML loader
- one representative replay case for the log-first path

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_replay_loader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/replay tests/test_replay_loader.py
git commit -m "feat: add replay case loading"
```

### Task 6: Implement LogTrackExecutor search and trace resolution

**Files:**
- Create: `runtime/tracks/log_track.py`
- Modify: `runtime/tracks/__init__.py`
- Test: `tests/test_log_track_executor.py`

**Step 1: Write the failing test**

```python
def test_log_track_executor_extracts_trace_key_from_hits():
    from runtime.tracks.log_track import LogTrackExecutor
    from runtime.adapter_runtime.runtime import AdapterRuntime
    from runtime.adapter_runtime.replay_backend import ReplayBackend
    from runtime.models.session import InvestigationSession

    backend = ReplayBackend({
        "sls.search_logs": [{"message": "timeout traceId=abc-123", "service": "trade-server"}],
    })
    runtime = AdapterRuntime(backend=backend)
    executor = LogTrackExecutor(runtime)
    session = InvestigationSession(session_id="sess-1", query_text="支付失败")

    updated = executor.search_and_resolve(session)

    assert updated.artifacts["trace_key"] == "abc-123"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_log_track_executor.py::test_log_track_executor_extracts_trace_key_from_hits -v`
Expected: FAIL because the executor does not exist yet

**Step 3: Write minimal implementation**

Implement the first two log-track actions:

- log search through adapter runtime
- trace key extraction from candidate hits

Store intermediate artifacts on the session.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_log_track_executor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/tracks tests/test_log_track_executor.py
git commit -m "feat: add log search and trace resolution"
```

### Task 7: Implement trace expansion and timeline building

**Files:**
- Modify: `runtime/tracks/log_track.py`
- Create: `runtime/diagnosis/timeline.py`
- Test: `tests/test_trace_expand.py`

**Step 1: Write the failing test**

```python
def test_trace_expand_builds_service_timeline():
    from runtime.tracks.log_track import LogTrackExecutor
    from runtime.adapter_runtime.runtime import AdapterRuntime
    from runtime.adapter_runtime.replay_backend import ReplayBackend
    from runtime.models.session import InvestigationSession

    backend = ReplayBackend({
        "sls.expand_trace": [
            {"service": "gateway", "message": "request in"},
            {"service": "trade-server", "message": "downstream timeout"},
        ],
    })
    runtime = AdapterRuntime(backend=backend)
    executor = LogTrackExecutor(runtime)
    session = InvestigationSession(session_id="sess-1", query_text="支付失败")
    session.artifacts["trace_key"] = "abc-123"

    updated = executor.expand_trace(session)

    assert updated.timeline_events[0]["service"] == "gateway"
    assert updated.timeline_events[1]["service"] == "trade-server"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_trace_expand.py::test_trace_expand_builds_service_timeline -v`
Expected: FAIL because trace expansion does not exist yet

**Step 3: Write minimal implementation**

Implement:

- trace expansion call through adapter runtime
- timeline normalization
- initial `TraceChain` creation

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_trace_expand.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/tracks runtime/diagnosis tests/test_trace_expand.py
git commit -m "feat: add trace expansion timeline"
```

### Task 8: Add evidence extraction and hypothesis generation

**Files:**
- Create: `runtime/diagnosis/evidence.py`
- Create: `runtime/diagnosis/hypothesis.py`
- Modify: `runtime/diagnosis/__init__.py`
- Test: `tests/test_diagnosis_engine.py`

**Step 1: Write the failing test**

```python
def test_timeout_trace_produces_timeout_hypothesis():
    from runtime.diagnosis.evidence import extract_evidence
    from runtime.diagnosis.hypothesis import generate_hypotheses
    from runtime.models.logs import TraceChain

    chain = TraceChain(
        trace_key="abc-123",
        services_in_order=["gateway", "trade-server"],
        error_events=[{"service": "trade-server", "message": "timeout"}],
    )

    evidence = extract_evidence(chain)
    hypotheses = generate_hypotheses(evidence)

    assert any(item.type == "downstream_timeout" for item in evidence)
    assert hypotheses[0].label == "downstream_service_timeout"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_diagnosis_engine.py::test_timeout_trace_produces_timeout_hypothesis -v`
Expected: FAIL because diagnosis helpers do not exist yet

**Step 3: Write minimal implementation**

Implement rule-first diagnosis helpers that:

- derive evidence from trace artifacts
- generate ranked hypotheses from evidence
- attach supporting evidence ids

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_diagnosis_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/diagnosis tests/test_diagnosis_engine.py
git commit -m "feat: add evidence and hypothesis generation"
```

### Task 9: Wire a runnable log-first investigation flow

**Files:**
- Create: `runtime/core/investigation_runner.py`
- Modify: `runtime/core/flow_engine.py`
- Modify: `runtime/core/__init__.py`
- Test: `tests/test_investigation_runner.py`

**Step 1: Write the failing test**

```python
def test_investigation_runner_completes_replay_case():
    from runtime.core.investigation_runner import InvestigationRunner
    from runtime.replay.loader import load_case

    case = load_case("runtime/replay/cases/log_timeout_case.yaml")
    runner = InvestigationRunner.from_replay_case(case)

    session = runner.run()

    assert session.current_phase == "EscalateOrConclude"
    assert session.hypotheses
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_investigation_runner.py::test_investigation_runner_completes_replay_case -v`
Expected: FAIL because the runner does not exist yet

**Step 3: Write minimal implementation**

Implement a runner that coordinates:

- session creation
- phase progression
- log track execution
- diagnosis stage execution

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_investigation_runner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/core tests/test_investigation_runner.py
git commit -m "feat: add runnable investigation flow"
```

### Task 10: Add a skill bridge contract for Compass responses

**Files:**
- Create: `runtime/skill_bridge/contracts.py`
- Create: `runtime/skill_bridge/render.py`
- Modify: `runtime/skill_bridge/__init__.py`
- Test: `tests/test_skill_bridge.py`

**Step 1: Write the failing test**

```python
def test_skill_bridge_renders_conclusion_summary():
    from runtime.skill_bridge.render import render_conclusion_card
    from runtime.models.session import InvestigationSession
    from runtime.models.diagnosis import Hypothesis

    session = InvestigationSession(session_id="sess-1", query_text="支付失败")
    session.hypotheses = [
        Hypothesis(id="h1", label="downstream_service_timeout", summary="trade-server 调用下游超时")
    ]

    card = render_conclusion_card(session)

    assert "downstream_service_timeout" in card["title"]
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_skill_bridge.py::test_skill_bridge_renders_conclusion_summary -v`
Expected: FAIL because the skill bridge does not exist yet

**Step 3: Write minimal implementation**

Implement render helpers that transform runtime state into user-facing structures for:

- conclusion card
- process summary
- next-step recommendation

Keep formatting data-oriented so the existing `SKILL.md` can consume it.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_skill_bridge.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/skill_bridge tests/test_skill_bridge.py
git commit -m "feat: add skill bridge rendering"
```

### Task 11: Add CLI entrypoint for replay execution

**Files:**
- Create: `runtime/cli.py`
- Modify: `scripts/harness_protocol_runner.py`
- Test: `tests/test_runtime_cli.py`

**Step 1: Write the failing test**

```python
def test_runtime_cli_runs_replay_case():
    from runtime.cli import main

    code = main(["--replay-case", "runtime/replay/cases/log_timeout_case.yaml"])

    assert code == 0
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_runtime_cli.py::test_runtime_cli_runs_replay_case -v`
Expected: FAIL because the runtime CLI does not exist yet

**Step 3: Write minimal implementation**

Implement a CLI entrypoint that:

- loads a replay case
- runs the investigation
- prints a compact summary
- returns a zero exit code on success

Update the existing harness runner to delegate to the new runtime entrypoint where appropriate.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_runtime_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add runtime/cli.py scripts/harness_protocol_runner.py tests/test_runtime_cli.py
git commit -m "feat: add runtime cli entrypoint"
```

### Task 12: Document runtime-to-skill integration points

**Files:**
- Modify: `SKILL.md`
- Create: `docs/runtime-skill-integration.md`
- Test: `tests/test_runtime_contracts_smoke.py`

**Step 1: Write the failing test**

```python
def test_skill_bridge_contract_smoke():
    from runtime.skill_bridge.contracts import ConclusionCard

    card = ConclusionCard(title="结论", summary="下游超时")

    assert card.title == "结论"
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_runtime_contracts_smoke.py::test_skill_bridge_contract_smoke -v`
Expected: FAIL because the contract or integration doc references do not exist yet

**Step 3: Write minimal implementation**

Document and wire:

- which runtime outputs are consumed by the skill layer
- where manual confirmation interrupts occur
- how the existing Compass first-turn and conclusion templates should read runtime results

Only make the minimal `SKILL.md` changes required to point future work at the runtime layer.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_runtime_contracts_smoke.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add SKILL.md docs/runtime-skill-integration.md tests/test_runtime_contracts_smoke.py
git commit -m "docs: describe runtime skill integration"
```

### Task 13: Final verification pass

**Files:**
- Test: `tests/test_runtime_imports.py`
- Test: `tests/test_runtime_models.py`
- Test: `tests/test_flow_engine.py`
- Test: `tests/test_replay_adapter_runtime.py`
- Test: `tests/test_replay_loader.py`
- Test: `tests/test_log_track_executor.py`
- Test: `tests/test_trace_expand.py`
- Test: `tests/test_diagnosis_engine.py`
- Test: `tests/test_investigation_runner.py`
- Test: `tests/test_skill_bridge.py`
- Test: `tests/test_runtime_cli.py`
- Test: `tests/test_runtime_contracts_smoke.py`

**Step 1: Run focused runtime test suite**

Run: `python3 -m pytest tests/test_runtime_imports.py tests/test_runtime_models.py tests/test_flow_engine.py tests/test_replay_adapter_runtime.py tests/test_replay_loader.py tests/test_log_track_executor.py tests/test_trace_expand.py tests/test_diagnosis_engine.py tests/test_investigation_runner.py tests/test_skill_bridge.py tests/test_runtime_cli.py tests/test_runtime_contracts_smoke.py -v`
Expected: PASS across the new runtime scope

**Step 2: Run existing harness compatibility checks**

Run: `python3 scripts/check_harness_ready.py`
Expected: PASS, unless the skill integration step intentionally changes required files

**Step 3: Record residual gaps**

Document any remaining blockers before integrating real adapters, especially:

- live SLS contract differences
- missing entity prompts
- skill bridge formatting gaps

**Step 4: Commit**

```bash
git add runtime tests docs SKILL.md scripts
git commit -m "feat: deliver compass runtime mvp"
```

Plan complete and saved to `docs/plans/2026-04-15-compass-runtime-mvp.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
