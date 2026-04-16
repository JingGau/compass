# Compass Runtime + Skill Dual-Layer Design

**Date:** 2026-04-15

**Status:** Approved for implementation planning

## Goal

Refactor `compass` from a prompt-first troubleshooting skill into a runnable investigation framework with two clear layers:

- a `runtime` layer that executes investigation flow, collects evidence, and produces structured hypotheses
- a `skill` layer that handles user interaction, confirmations, and narrative output

## Approved Decisions

### Product Direction

- Primary target: a runnable troubleshooting framework
- Entry shape: dual entrypoints, `CLI/runner + skill/Agent`
- First MVP path: log-first investigation
- Delivery rhythm: replay first, then real adapter integration
- Skill compatibility: preserve current Compass principles, but allow step boundary and output refactoring

### Runtime Responsibility Boundary

The runtime owns:

- flow orchestration
- session state
- adapter dispatch
- replay execution
- structured evidence extraction
- hypothesis generation and ranking

The skill layer owns:

- first-turn framing
- mode confirmation and user-facing pauses
- result presentation
- process narration
- final recommendation cards

## Architecture

### 1. Runtime Layer

The runtime becomes the execution kernel. It should not depend on the prompt text structure in `SKILL.md`.

Core modules:

- `runtime/core/`: session, phases, flow engine
- `runtime/models/`: structured data objects such as `InvestigationSession`, `LogHit`, `TraceChain`, `Evidence`, `Hypothesis`, `ReplayCase`
- `runtime/tracks/`: track executors, starting with `LogTrackExecutor`
- `runtime/adapter_runtime/`: unified adapter interface for real and replay backends
- `runtime/diagnosis/`: evidence extraction, hypothesis generation, ranking
- `runtime/replay/`: replay case loading and adapter response playback
- `runtime/cli.py`: independent runner entrypoint

### 2. Skill Layer

The skill layer becomes a bridge between human conversation and the runtime.

Core responsibilities:

- convert user problem description into runtime intake input
- expose manual or automatic mode controls
- translate runtime artifacts into Compass-formatted cards and summaries
- preserve safety and masking requirements already defined by Compass

### 3. Existing Assets

The current repository already contains valuable assets that should be retained:

- `adapters/`: concrete data-source clients
- `knowledge/` and `projects/`: investigation knowledge base
- `memory/strategies.yaml` and `memory/categories.yaml`: strategy and taxonomy memory
- `guards/`: safety constraints

The new runtime should consume these assets instead of replacing them immediately.

## MVP Investigation Flow

The first runnable path is log-first investigation.

Recommended runtime phases:

1. `Intake`
2. `Plan`
3. `LogSearch`
4. `TraceResolve`
5. `TraceExpand`
6. `EvidenceHypothesis`
7. `EscalateOrConclude`

This runtime flow can later be projected back into the current Compass user-facing 8-step protocol, but the engine should not be forced to mirror the prompt structure internally.

## Replay-First Strategy

To avoid blocking on credentials and environment readiness, the first implementation phase should use replayable investigation cases.

Recommended replay model:

- cases are organized by scenario
- each case contains adapter-level responses
- the runtime executes the same path whether the backend is replay or real

This gives the project a safe way to validate flow, evidence extraction, and hypothesis generation before talking to live systems.

## Data Model Principles

### Evidence and Hypotheses Stay Separate

- `Evidence` represents observed facts from logs, traces, or query results
- `Hypothesis` represents possible root causes inferred from evidence

This separation is required for explainability and later ranking.

### TraceChain is a Diagnostic Object

`TraceChain` should not be a raw log dump. It should be the structured, investigation-ready view of an execution path:

- service order
- breakpoints
- latency anomalies
- error events
- missing downstream continuation

### Session State Must Grow Beyond Step Tracking

The current state model is useful but too narrow. The runtime session should also carry:

- entities
- missing entities
- chosen tracks
- artifacts
- evidence list
- hypothesis list
- timeline events
- pending confirmations

## Proposed Repository Shape

```text
compass/
├── SKILL.md
├── skill/
│   ├── prompts/
│   ├── guards/
│   └── bridge/
├── runtime/
│   ├── core/
│   ├── tracks/
│   ├── adapter_runtime/
│   ├── diagnosis/
│   ├── replay/
│   ├── models/
│   └── cli.py
├── adapters/
├── knowledge/
├── projects/
├── memory/
│   ├── strategy/
│   └── taxonomy/
├── state/
├── scripts/
└── tests/
```

Migration should be gradual. The first phase should add `runtime/` without deleting existing `tools/` or prompt assets.

## Phase 1 Scope

Phase 1 should produce:

- a new runtime skeleton
- shared runtime models
- a real flow engine abstraction
- a replay adapter runtime
- a log track executor
- evidence and hypothesis generation for the log-first path
- a skill bridge contract for turning runtime output into Compass responses

It should explicitly avoid:

- rewriting all prompts up front
- refactoring every adapter
- implementing all three tracks in parallel
- building a heavy rule DSL before the log path is proven

## Success Criteria

Phase 1 is successful when:

- a replay case can drive the runtime through the full log-first investigation path
- the runtime produces structured evidence and ranked hypotheses
- the skill layer can render those runtime outputs into Compass-style user responses
- the architecture cleanly supports later replacement of replay backends with real adapters
