# Action Card Protocol Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make every Compass investigation step visible, gated, and reusable by rendering a structured action card before execution and a structured result card after execution.

**Architecture:** Add a small runtime protocol around existing adapters instead of changing adapter behavior. Each step becomes an `InvestigationAction`, passes through safety gate rendering, then produces an `ActionResult` that extracts leads and can feed an evidence graph.

**Tech Stack:** Python dataclasses, existing `tools/` harness modules, unittest, Markdown prompt updates.

---

### Task 1: Action Card Models and Rendering

**Files:**
- Create: `tools/action_cards.py`
- Test: `tests/test_action_cards.py`

**Step 1: Write failing tests**

Cover:
- SQL Before Card shows the exact SQL.
- Code Before Card shows application and method names.
- SLS After Card shows hit count, trace IDs, code/database/log next-step candidates.
- A safety gate that requires confirmation renders explicit confirmation choices.

**Step 2: Run tests and verify they fail**

Run: `.venv/bin/python -m unittest tests.test_action_cards -v`

**Step 3: Implement minimal dataclasses and renderers**

Create:
- `InvestigationAction`
- `SafetyGateResult`
- `ActionResult`
- `render_before_card`
- `render_safety_gate_card`
- `render_after_card`
- `build_pending_confirmation`

**Step 4: Run tests and verify they pass**

Run: `.venv/bin/python -m unittest tests.test_action_cards -v`

### Task 2: SQL Gate Parsing

**Files:**
- Create: `tools/sql_gate.py`
- Test: `tests/test_sql_gate.py`

**Step 1: Write failing tests**

Cover:
- Doris EXPLAIN with `cardinality=2470577` is high risk and requires confirmation.
- Doris EXPLAIN with `cardinality=50000` is low risk.
- High risk gate creates a pending confirmation and blocks execution until confirmed.

**Step 2: Run tests and verify they fail**

Run: `.venv/bin/python -m unittest tests.test_sql_gate -v`

**Step 3: Implement parser and risk evaluator**

Parse `cardinality`, `partitions`, `tablets`, `VOlapScanNode`, and predicates from the textual EXPLAIN result.

**Step 4: Run tests and verify they pass**

Run: `.venv/bin/python -m unittest tests.test_sql_gate -v`

### Task 3: Evidence Graph

**Files:**
- Create: `tools/evidence_graph.py`
- Test: `tests/test_evidence_graph.py`

**Step 1: Write failing tests**

Cover:
- Page → API → method → table links can be recorded.
- Extracted leads from action results become graph nodes.

**Step 2: Run tests and verify they fail**

Run: `.venv/bin/python -m unittest tests.test_evidence_graph -v`

**Step 3: Implement minimal graph**

Create an in-memory graph with node de-duplication, edge de-duplication, and export to dict.

**Step 4: Run tests and verify they pass**

Run: `.venv/bin/python -m unittest tests.test_evidence_graph -v`

### Task 4: Prompt and Protocol Wiring

**Files:**
- Modify: `SKILL.md`
- Modify: `prompts/query-planning.md`
- Modify: `prompts/result-analysis.md`
- Modify: `tools/tool_protocol.md`

**Step 1: Update protocol docs**

Make Action Card Protocol mandatory:
- No direct adapter call without `InvestigationAction`.
- Execution order is Before Card → Safety Gate Card → execute or pause → After Card.
- Risk gates that require confirmation must add `pending_confirmation`.

**Step 2: Run focused tests**

Run: `.venv/bin/python -m unittest tests.test_action_cards tests.test_sql_gate tests.test_evidence_graph -v`

**Step 3: Run existing harness tests**

Run: `.venv/bin/python -m unittest tests.test_harness_protocol_runner tests.test_tools_sensors tests.test_tools_session_state -v`

