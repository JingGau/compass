from __future__ import annotations

import fnmatch
import json
import os
from pathlib import Path
import re
from typing import Any
import yaml

from compass_core.intake import intake_problem
from compass_core.state import default_state, now_iso, read_or_init_state, update_state, write_state
from tools.action_cards import SafetyGateResult
from tools.sql_gate import assess_sql_explain


class CompassRuntimeError(ValueError):
    pass


REQUIRED_CONCLUSION_FIELDS: tuple[str, ...] = (
    "what",
    "where",
    "when",
    "why_technical",
    "why_business",
    "blast_radius",
    "how",
    "inference_chain",
)

TRACK_REQUIREMENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "sls": {
        "input": ("query", "time_range", "anchor"),
        "gate": ("type", "status", "keyword_source"),
    },
    "sql": {
        "input": ("sql", "env"),
        "gate": ("type",),
    },
    "code": {
        "input": ("repo", "target"),
        "gate": ("type", "scope"),
    },
    "kb": {
        "input": ("query",),
        "gate": ("type",),
    },
    "manual": {
        "input": (),
        "gate": (),
    },
}

EVIDENCE_KINDS = {"manual", "log", "sql", "code", "kb", "user", "inference"}
EVIDENCE_STRENGTHS = {"weak", "medium", "strong"}
GENERIC_SLS_KEYWORDS = {
    "error",
    "exception",
    "fail",
    "failed",
    "失败",
    "异常",
    "错误",
    "报错",
    "问题",
    "日志",
    "支付",
    "订单",
    "余额",
    "余额不足",
    "停充",
    "充值",
    "退款",
    "回调",
}
SLS_EXTRA_KEYWORD_SOURCES = {"code", "sql", "schema", "table_field", "code_sql", "none"}
CODE_SEARCH_SKIP_DIRS = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
}
CODE_SEARCH_MAX_FILE_BYTES = 1_000_000
CODE_SHOW_MAX_LINES = 200


def start_session(path: str | Path, text: str) -> dict[str, Any]:
    intake = intake_problem(text)
    state = default_state()
    state["problem"] = {
        "raw": intake.raw_problem,
        "standard": intake.standard_problem,
        "scene": intake.scene,
        "environment": intake.environment,
        "impact": "未知",
        "detected_at": now_iso(),
    }
    state["environment"] = intake.environment
    state["mode"] = "investigation_only"
    state["write_policy"] = "no_code_or_data_mutation"
    state["entities"] = intake.entities
    state["missing"] = intake.missing
    state["hypotheses"] = []
    state["hypothesis_mode"] = "evidence_first"
    state["investigation_hints"] = intake.investigation_hints
    state["scene_facts"] = []
    state["next_actions"] = intake.next_actions
    state["applicable_knowledge"] = _recall_applicable_knowledge(intake, top_n=5)
    state["flow"].update(
        {
            "phase": "awaiting_confirmation",
            "confirmed": False,
            "allowed_commands": ["confirm", "state show"],
            "current_step": "intake",
        }
    )
    _append_event(
        state,
        "session_started",
        summary=state["problem"]["standard"],
        refs={"session_id": state["session_id"], "phase": "awaiting_confirmation"},
    )
    write_state(path, state)
    return state


def _recall_applicable_knowledge(intake: Any, *, top_n: int = 5) -> list[dict[str, Any]]:
    """根据 intake 内容自动从 KB 召回最多 top_n 条相关通用知识。

    召回失败（KB 不存在 / yaml 损坏）时返回空列表，不阻塞主流程。
    """

    try:
        from .knowledge import suggest_knowledge, increment_hits  # 延迟导入，避免循环
    except Exception:
        return []

    parts: list[str] = []
    raw = getattr(intake, "raw_problem", "") or ""
    standard = getattr(intake, "standard_problem", "") or ""
    scene = getattr(intake, "scene", "") or ""
    parts.append(str(raw))
    parts.append(str(standard))
    parts.append(str(scene))
    entities = getattr(intake, "entities", {}) or {}
    if isinstance(entities, dict):
        for key, value in entities.items():
            parts.append(str(key))
            if isinstance(value, list):
                parts.extend(str(v) for v in value)
            else:
                parts.append(str(value))
    query = " ".join(p for p in parts if p)

    try:
        matches = suggest_knowledge(query, top_n=top_n)
    except Exception:
        return []
    if not matches:
        return []
    try:
        increment_hits([m.id for m in matches])
    except Exception:
        pass
    return [m.to_dict() for m in matches]


def confirm_session(path: str | Path, mode: str = "auto") -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        phase = _phase(state)
        if phase not in {"awaiting_confirmation", "action_ready"}:
            raise CompassRuntimeError(f"当前阶段 {phase} 不需要确认。")
        state["flow"].update(
            {
                "phase": "action_ready",
                "confirmed": True,
                "execution_mode": mode,
                "allowed_commands": ["next", "scene fact", "playbook recall", "action plan", "evidence add", "state show"],
            }
        )
        _append_event(state, "session_confirmed", summary=f"mode={mode}", refs={"phase": "action_ready"})
        _touch(state)
        return state

    return _update_runtime_state(path, mutate)


def next_step(path: str | Path) -> dict[str, Any]:
    state = _load_state(path)
    state["__path__"] = str(path)
    phase = _phase(state)
    task = _build_next_task(state)
    if not state.get("flow", {}).get("confirmed"):
        return {
            "phase": phase,
            "blocked": True,
            "message": "会话尚未确认执行模式。请先运行 compass confirm。",
            "next_actions": ["confirm"],
            "health": _build_session_health(state),
            "task": task,
        }
    if phase == "action_ready":
        if not state.get("scene_facts"):
            return {
                "phase": phase,
                "blocked": False,
                "message": "请先记录场景事实，展开入口、对象、上下游、配置或差异，再基于事实推进查询和假设。",
                "next_actions": ["scene fact", "playbook recall", "action plan"],
                "health": _build_session_health(state),
                "task": task,
            }
        if not state.get("playbook_recall", {}).get("recalled"):
            return {
                "phase": phase,
                "blocked": False,
                "message": "已有场景事实，可先召回 playbook；若直接规划 action，runtime 仍会注入候选知识上下文并标记未召回。",
                "next_actions": ["playbook recall", "action plan", "hypothesis add", "scene fact"],
                "health": _build_session_health(state),
                "task": task,
            }
        return {
            "phase": phase,
            "blocked": False,
            "message": "已有场景事实和 playbook 召回，请继续记录查询证据，或从事实/证据派生新假设。",
            "next_actions": ["action plan", "hypothesis add", "scene fact"],
            "health": _build_session_health(state),
            "task": task,
        }
    if phase == "evidence_collecting":
        pending = _pending_actions(state)
        if pending:
            action_ids = ", ".join(str(item.get("action_id")) for item in pending)
            return {
                "phase": phase,
                "blocked": False,
                "message": f"存在待完成 action：{action_ids}。请先完成或明确改计划，再继续生成新结论。",
                "next_actions": [f"action complete {item.get('action_id')}" for item in pending],
                "health": _build_session_health(state),
                "task": task,
            }
        if not state.get("scene_facts"):
            return {
                "phase": phase,
                "blocked": False,
                "message": "已有证据，但还缺少场景事实。请先用 scene fact 记录入口、对象、上下游、配置或差异。",
                "next_actions": ["scene fact", "action plan"],
                "health": _build_session_health(state),
                "task": task,
            }

        payload = {
            "phase": phase,
            "blocked": False,
            "message": "已有场景事实和证据，可继续补证据、派生假设，或输出带证据引用的结论。",
            "next_actions": ["action plan", "hypothesis add", "conclude"],
            "health": _build_session_health(state),
            "task": task,
        }
        return payload
    if phase == "concluded":
        return {
            "phase": phase,
            "blocked": False,
            "message": "排查已输出结论。请先生成报告，再确认是否保留本次最终查询策略。",
            "next_actions": ["report"],
            "health": _build_session_health(state),
            "task": task,
        }
    if phase == "reported":
        review = state.get("strategy_review") or {}
        if review.get("status") == "pending":
            return {
                "phase": phase,
                "blocked": False,
                "message": "报告已生成。请确认是否保留本次最终查询策略。",
                "next_actions": ["strategy keep", "strategy discard"],
                "health": _build_session_health(state),
                "task": task,
            }
        return {
            "phase": phase,
            "blocked": False,
            "message": "排查已结束。可查看报告，或在新信息出现时 reopen。",
            "next_actions": ["report", "reopen"],
            "health": _build_session_health(state),
            "task": task,
        }
    return {"phase": phase, "blocked": False, "message": "继续推进。", "next_actions": [], "health": _build_session_health(state), "task": task}


def plan_action(
    path: str | Path,
    *,
    action_id: str,
    track: str,
    source: str,
    objective: str,
    success_criteria: str,
    action_input: dict[str, str] | None = None,
    gate: dict[str, str] | None = None,
    applied_playbooks: list[str] | None = None,
    applied_knowledge: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output: dict[str, Any] = {}

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _require_phase(state, {"action_ready", "evidence_collecting"}, "规划 action")
        _require_scene_facts(state, "规划 action")
        _require_unique_action_id(state, action_id)
        inputs = dict(action_input or {})
        normalized_track = track.lower()
        if normalized_track == "sql" and not inputs.get("env"):
            inputs["env"] = str(state.get("environment") or state.get("problem", {}).get("environment") or "prod")
        if normalized_track == "sls" and not inputs.get("time_range"):
            inputs["time_range"] = "-7d"
        gates = dict(gate or {})
        _validate_action_plan_fields(track, inputs, gates)
        sql_gate_result: SafetyGateResult | None = None
        if normalized_track == "sql":
            sql_gate_result = _enforce_sql_explain_gate(inputs, gates)
        playbooks = _clean_list(applied_playbooks)
        knowledge = _clean_list(applied_knowledge)
        action = {
            "action_id": action_id,
            "track": track,
            "source": source,
            "objective": objective,
            "success_criteria": success_criteria,
            "input": inputs,
            "gate": gates,
            "status": "planned",
            "created_at": now_iso(),
            "context": _build_action_context(state, track=normalized_track, applied_playbooks=playbooks),
        }
        if playbooks:
            action["applied_playbooks"] = playbooks
        if knowledge:
            action["applied_knowledge"] = knowledge
        if sql_gate_result and sql_gate_result.requires_confirmation:
            action["status"] = "requires_confirmation"
            action["pending_confirmation"] = {
                "gate_type": sql_gate_result.gate_type,
                "risk_level": sql_gate_result.risk_level,
                "summary": sql_gate_result.summary,
                "details": dict(sql_gate_result.details),
            }
            state.setdefault("pending_confirmations", []).append(
                {
                    "id": f"{action_id}:sql:{sql_gate_result.risk_level}",
                    "action_id": action_id,
                    "gate_type": sql_gate_result.gate_type,
                    "risk_level": sql_gate_result.risk_level,
                    "summary": sql_gate_result.summary,
                    "required_reply": "compass action confirm",
                    "created_at": now_iso(),
                }
            )
        state.setdefault("action_plan", []).append(action)
        allowed = ["next", "action complete", "action plan", "scene fact", "hypothesis add", "evidence add", "state show"]
        if action["status"] == "requires_confirmation":
            allowed.append("action confirm")
        state["flow"].update(
            {
                "phase": "evidence_collecting",
                "current_step": "action_planning",
                "allowed_commands": allowed,
            }
        )
        _append_event(
            state,
            "action_planned",
            summary=objective,
            refs={
                "action_id": action_id,
                "track": normalized_track,
                "status": action["status"],
                "phase": "evidence_collecting",
            },
        )
        _touch(state)
        output["action"] = action
        return state

    state = _update_runtime_state(path, mutate)
    return state, output["action"]


def confirm_action(
    path: str | Path,
    *,
    action_id: str,
    note: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    output: dict[str, Any] = {}

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _require_phase(state, {"action_ready", "evidence_collecting"}, "确认 action 风险")
        action = _find_action_plan(state, action_id)
        if action.get("status") != "requires_confirmation":
            raise CompassRuntimeError(
                f"action {action_id} 状态为 {action.get('status')}，没有待确认的风险门禁。"
            )
        action["status"] = "planned"
        action["confirmed_at"] = now_iso()
        if note:
            action["confirmation_note"] = note
        pending = state.get("pending_confirmations") or []
        state["pending_confirmations"] = [
            item for item in pending if str(item.get("action_id")) != action_id
        ]
        _append_event(
            state,
            "action_confirmed",
            summary=note or f"action {action_id} risk confirmed",
            refs={"action_id": action_id, "phase": _phase(state)},
        )
        _touch(state)
        output["action"] = action
        return state

    state = _update_runtime_state(path, mutate)
    return state, output["action"]


def adapter_runtime_env(path: str | Path, *, action_id: str) -> tuple[dict[str, Any], dict[str, str]]:
    output: dict[str, Any] = {}

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        action = _find_action_plan(state, action_id)
        if action.get("status") != "planned":
            raise CompassRuntimeError(
                f"action {action_id} 状态为 {action.get('status')}，不能生成 adapter 自动执行环境。"
            )
        env = {
            "COMPASS_ADAPTER_MODE": "agent_auto",
            "COMPASS_AGENT_AUTO": "1",
            "COMPASS_RUNTIME_STATE_FILE": str(Path(path).resolve()),
            "COMPASS_RUNTIME_ACTION_ID": action_id,
        }
        _append_event(
            state,
            "adapter_env_generated",
            summary=f"action {action_id} adapter env generated",
            refs={
                "action_id": action_id,
                "track": str(action.get("track", "")),
                "source": str(action.get("source", "")),
            },
        )
        _touch(state)
        output["action"] = action
        output["env"] = env
        return state

    _update_runtime_state(path, mutate)
    return output["action"], output["env"]


def code_search(
    path: str | Path,
    *,
    action_id: str,
    query: str,
    root: str | Path | None = None,
    glob: str | None = None,
    limit: int = 20,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output: dict[str, Any] = {}

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _, repo_path = _require_planned_code_action(state, action_id)
        search_root = _resolve_code_path(repo_path, root or repo_path)
        if not search_root.exists() or not search_root.is_dir():
            raise CompassRuntimeError(f"code search root 不存在或不是目录：{search_root}。")
        matches, truncated = _search_code_files(search_root, repo_path, query=query, glob=glob, limit=limit)
        result = {
            "action_id": action_id,
            "repo": str(repo_path),
            "root": str(search_root),
            "query": query,
            "glob": glob or "",
            "limit": max(1, int(limit)),
            "truncated": truncated,
            "matches": matches,
        }
        _append_event(
            state,
            "code_search_executed",
            summary=f"action {action_id} code search: {query}",
            refs={
                "action_id": action_id,
                "repo": str(repo_path),
                "root": str(search_root),
                "query": query,
                "matches": len(matches),
                "truncated": truncated,
            },
        )
        _touch(state)
        output["result"] = result
        return state

    state = _update_runtime_state(path, mutate)
    return state, output["result"]


def code_show(
    path: str | Path,
    *,
    action_id: str,
    file_path: str | Path,
    start: int = 1,
    end: int = 120,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output: dict[str, Any] = {}

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _, repo_path = _require_planned_code_action(state, action_id)
        target = _resolve_code_path(repo_path, file_path)
        if not target.exists() or not target.is_file():
            raise CompassRuntimeError(f"code show 文件不存在或不是普通文件：{target}。")
        start_line = max(1, int(start))
        end_line = max(start_line, int(end))
        end_line = min(end_line, start_line + CODE_SHOW_MAX_LINES - 1)
        lines = _read_code_lines(target, start=start_line, end=end_line)
        result = {
            "action_id": action_id,
            "repo": str(repo_path),
            "path": target.relative_to(repo_path).as_posix(),
            "start": start_line,
            "end": start_line + len(lines) - 1 if lines else start_line,
            "lines": lines,
        }
        _append_event(
            state,
            "code_show_executed",
            summary=f"action {action_id} code show: {result['path']}",
            refs={
                "action_id": action_id,
                "repo": str(repo_path),
                "path": result["path"],
                "start": result["start"],
                "end": result["end"],
            },
        )
        _touch(state)
        output["result"] = result
        return state

    state = _update_runtime_state(path, mutate)
    return state, output["result"]


def complete_action(
    path: str | Path,
    *,
    action_id: str,
    summary: str,
    elapsed_ms: int = 0,
    findings: list[str] | None = None,
    leads: dict[str, list[str]] | None = None,
    supports: str | None = None,
    kind: str | None = None,
    strength: str = "medium",
    raw_ref: str | None = None,
    event_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output: dict[str, Any] = {}

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _require_phase(state, {"action_ready", "evidence_collecting"}, "完成 action")
        action = _find_action_plan(state, action_id)
        if action.get("status") == "completed":
            raise CompassRuntimeError(f"action 已完成：{action_id}。")
        if action.get("status") == "requires_confirmation":
            raise CompassRuntimeError(
                f"action {action_id} 仍处于风险待确认状态，无法完成。请先执行 "
                f"`compass action confirm --action-id {action_id} --note ...` 解锁。"
            )
        evidence = _build_evidence(
            state,
            source=str(action.get("source", "unknown")),
            summary=summary,
            findings=findings or [],
            supports=supports,
            action_id=action_id,
            kind=kind or _kind_from_track(str(action.get("track", "manual"))),
            strength=strength,
            raw_ref=raw_ref,
            event_at=event_at,
        )
        state.setdefault("evidence", []).append(evidence)
        state.setdefault("action_history", []).append(
            _build_action_history_item(
                action_id=action_id,
                track=str(action.get("track", "manual")),
                source=str(action.get("source", "unknown")),
                objective=str(action.get("objective", "")),
                success_criteria=str(action.get("success_criteria", "")),
                action_input=action.get("input") or {},
                gate=action.get("gate") or {},
                summary=summary,
                findings=findings or [],
                leads=leads or {},
                elapsed_ms=elapsed_ms,
                evidence_id=evidence["id"],
            )
        )
        action["status"] = "completed"
        action["completed_at"] = now_iso()
        action["evidence_id"] = evidence["id"]
        _mark_hypothesis(state, supports, evidence["id"])
        state["flow"].update(
            {
                "phase": "evidence_collecting",
                "current_step": "evidence",
                "allowed_commands": ["next", "action plan", "action complete", "evidence add", "hypothesis add", "conclude", "state show"],
            }
        )
        _append_event(
            state,
            "action_completed",
            summary=summary,
            refs={"action_id": action_id, "evidence_id": evidence["id"], "phase": "evidence_collecting"},
        )
        _touch(state)
        output["evidence"] = evidence
        return state

    state = _update_runtime_state(path, mutate)
    return state, output["evidence"]


def add_evidence(
    path: str | Path,
    *,
    source: str,
    summary: str,
    supports: str | None = None,
    kind: str = "manual",
    strength: str = "medium",
    raw_ref: str | None = None,
    event_at: str | None = None,
    change_ids: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output: dict[str, Any] = {}

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _require_phase(state, {"action_ready", "evidence_collecting"}, "新增证据")
        _require_existing_changes(state, change_ids or [])
        evidence = _build_evidence(
            state,
            source=source,
            summary=summary,
            findings=[],
            supports=supports,
            action_id=None,
            kind=kind,
            strength=strength,
            raw_ref=raw_ref,
            event_at=event_at,
            change_ids=change_ids,
        )
        state.setdefault("evidence", []).append(evidence)
        state.setdefault("action_history", []).append(
            _build_action_history_item(
                action_id=f"manual-{evidence['id']}",
                track="manual",
                source=source,
                action_input={},
                gate={"type": "manual", "status": "passed"},
                summary=summary,
                findings=[],
                leads={},
                elapsed_ms=0,
                evidence_id=evidence["id"],
            )
        )
        _mark_hypothesis(state, supports, evidence["id"])
        state["flow"]["phase"] = "evidence_collecting"
        _append_event(
            state,
            "evidence_recorded",
            summary=summary,
            refs={"evidence_id": evidence["id"], "phase": "evidence_collecting"},
        )
        _touch(state)
        output["evidence"] = evidence
        return state

    state = _update_runtime_state(path, mutate)
    return state, output["evidence"]


CHANGE_TYPES = {"deploy", "config", "data", "permission", "feature_flag", "rollback", "infra", "other"}


def record_change(
    path: str | Path,
    *,
    change_type: str,
    target: str,
    description: str,
    event_at: str,
    before: str = "",
    after: str = "",
    source: str = "",
    evidence_ids: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """登记一笔与排查相关的变更（发布、配置、数据、权限、灰度等）。

    变更窗口是根因分析的核心线索之一：把"什么时间、对什么、做了什么改动"
    结构化进 state.changes，后续 timeline 可与故障窗口对齐。
    """

    normalized_type = (change_type or "").strip().lower()
    if normalized_type not in CHANGE_TYPES:
        raise CompassRuntimeError(
            f"未知 change_type：{change_type}。可选：{', '.join(sorted(CHANGE_TYPES))}。"
        )
    if not (target or "").strip():
        raise CompassRuntimeError("change.target 不能为空（变更对象，例如 'order-server@v1.2.3' / 'config:rate-limit'）。")
    if not (description or "").strip():
        raise CompassRuntimeError("change.description 不能为空（变更内容简述，例如 '上线 v1.2.3' / '把 rate_limit 从 100 调到 50'）。")
    if not (event_at or "").strip():
        raise CompassRuntimeError("change.event_at 不能为空（变更真实发生时间，用于 timeline 对齐）。")

    output: dict[str, Any] = {}

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _require_phase(state, {"action_ready", "evidence_collecting"}, "登记变更")
        _require_existing_evidence(state, evidence_ids or [])
        changes = state.setdefault("changes", [])
        change_id = f"C{len(changes) + 1}"
        record: dict[str, Any] = {
            "id": change_id,
            "change_type": normalized_type,
            "target": target.strip(),
            "description": description.strip(),
            "event_at": event_at.strip(),
            "before": (before or "").strip(),
            "after": (after or "").strip(),
            "source": (source or "").strip(),
            "evidence": list(evidence_ids or []),
            "created_at": now_iso(),
        }
        changes.append(record)
        state["flow"].update(
            {
                "phase": "evidence_collecting",
                "current_step": "change_logging",
            }
        )
        _append_event(
            state,
            "change_recorded",
            summary=record["description"],
            refs={"change_id": change_id, "change_type": normalized_type, "phase": "evidence_collecting"},
        )
        _touch(state)
        output["record"] = record
        return state

    state = _update_runtime_state(path, mutate)
    return state, output["record"]


def reopen_session(path: str | Path, *, reason: str) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _require_phase(state, {"concluded", "reported"}, "重开排查")
        conclusion = state.get("conclusion")
        if not conclusion:
            raise CompassRuntimeError("当前会话没有可重开的结论。")
        archived = dict(conclusion)
        archived["status"] = "superseded"
        archived["superseded_at"] = now_iso()
        archived["reopen_reason"] = reason
        archived["revision"] = state.get("revision", 1)
        if state.get("strategy_review"):
            archived["strategy_review"] = state.get("strategy_review")
        state.setdefault("conclusion_history", []).append(archived)
        state.pop("conclusion", None)
        state.pop("strategy_review", None)
        state["revision"] = int(state.get("revision", 1)) + 1
        state["flow"].update(
            {
                "phase": "evidence_collecting",
                "current_step": "reopened",
                "report_generated": False,
                "allowed_commands": ["next", "action plan", "action complete", "evidence add", "scene fact", "hypothesis add", "conclude", "state show"],
            }
        )
        _append_event(
            state,
            "session_reopened",
            summary=reason,
            refs={"revision": state["revision"], "phase": "evidence_collecting"},
        )
        _touch(state)
        return state

    return _update_runtime_state(path, mutate)


SCENE_FACT_CATEGORIES = {
    "entrypoint",
    "object",
    "upstream",
    "downstream",
    "config",
    "variant",
    "diff",
    "baseline",
    "repro",
}

DIFF_KEYWORDS = (
    "差异",
    "对比",
    "vs",
    "VS",
    "相比",
    "不同于",
    "不一样",
    "之前",
    "之后",
    "原本",
    "正常",
    "异常",
    "变更",
)


def add_scene_fact(
    path: str | Path,
    *,
    category: str,
    name: str,
    value: str,
    source: str,
    evidence_ids: list[str] | None = None,
    event_at: str | None = None,
) -> dict[str, Any]:
    normalized_category = (category or "").strip().lower()
    if normalized_category not in SCENE_FACT_CATEGORIES:
        raise CompassRuntimeError(
            f"未知 scene fact category：{category}。可选：{', '.join(sorted(SCENE_FACT_CATEGORIES))}。"
        )
    if normalized_category == "diff" and not any(kw in value for kw in DIFF_KEYWORDS):
        raise CompassRuntimeError(
            "category=diff 的 scene fact 必须在 value 中体现对比性，至少包含一个对比词："
            "差异 / 对比 / vs / 相比 / 不同于 / 之前 / 之后 / 原本 / 正常 / 异常 / 变更。"
            "建议格式：'故障 X 正常为 Y，差异点 Z'。"
        )

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _require_phase(state, {"action_ready", "evidence_collecting"}, "记录场景事实")
        _require_existing_evidence(state, evidence_ids or [])
        fact = {
            "category": normalized_category,
            "name": name,
            "value": value,
            "source": source,
            "evidence": evidence_ids or [],
            "created_at": now_iso(),
        }
        if event_at:
            fact["event_at"] = event_at
        state.setdefault("scene_facts", []).append(fact)
        state["flow"].update(
            {
                "phase": "evidence_collecting",
                "current_step": "scene_discovery",
                "allowed_commands": ["next", "scene fact", "hypothesis add", "action plan", "evidence add", "conclude", "state show"],
            }
        )
        _append_event(
            state,
            "scene_fact_recorded",
            summary=f"{normalized_category}.{name}={value}",
            refs={"fact": name, "category": normalized_category, "phase": "evidence_collecting"},
        )
        _touch(state)
        return state

    return _update_runtime_state(path, mutate)


def add_hypothesis(
    path: str | Path,
    *,
    hypothesis_id: str,
    statement: str,
    source_facts: list[str] | None = None,
    source_evidence: list[str] | None = None,
    falsifiable: str | None = None,
    change_ids: list[str] | None = None,
) -> dict[str, Any]:
    facts = source_facts or []
    evidence = source_evidence or []
    changes_ref = [str(c).strip() for c in (change_ids or []) if str(c).strip()]
    if not facts and not evidence and not changes_ref:
        raise CompassRuntimeError("假设必须引用至少一个 scene fact / evidence / change。")

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _require_phase(state, {"action_ready", "evidence_collecting"}, "新增假设")
        _require_existing_scene_facts(state, facts)
        _require_existing_evidence(state, evidence)
        _require_existing_changes(state, changes_ref)
        existing = {item.get("id") for item in state.get("hypotheses", [])}
        hypothesis: dict[str, Any] = {
            "id": hypothesis_id,
            "statement": statement,
            "status": "待验证",
            "source_facts": facts,
            "source_evidence": evidence,
        }
        if changes_ref:
            hypothesis["source_changes"] = changes_ref
        if falsifiable is not None:
            text = str(falsifiable).strip()
            if text:
                hypothesis["falsifiable"] = text
        if hypothesis_id in existing:
            for idx, item in enumerate(state.get("hypotheses", [])):
                if item.get("id") == hypothesis_id:
                    merged = {**item, **hypothesis}
                    if falsifiable is not None and not str(falsifiable).strip():
                        merged.pop("falsifiable", None)
                    state["hypotheses"][idx] = merged
                    break
        else:
            state.setdefault("hypotheses", []).append(hypothesis)
        state["hypothesis_mode"] = "evidence_first"
        _append_event(
            state,
            "hypothesis_recorded",
            summary=statement,
            refs={"hypothesis_id": hypothesis_id, "phase": _phase(state)},
        )
        _touch(state)
        return state

    return _update_runtime_state(path, mutate)


SEVERITY_LEVELS = ("sev1", "sev2", "sev3", "sev4")

_INFERENCE_SPLIT_REGEX = re.compile(r"\s*(?:→|->|=>|\u21d2)\s*")


def _split_inference_steps(text: str) -> list[str]:
    """把推断链拆成有序步骤；保留原文用于 details.inference_chain。"""

    if not text:
        return []
    parts = _INFERENCE_SPLIT_REGEX.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _diff_minutes(start: str, end: str | None) -> int | None:
    """计算两个时间字符串之间的分钟数，无法解析则返回 None。"""

    if not start or not end:
        return None
    from .timeline import _parse_ts  # 复用 timeline 的宽容解析

    s = _parse_ts(start)
    e = _parse_ts(end)
    if s is None or e is None:
        return None
    diff = (e - s) / 60.0
    if diff < 0:
        return None
    return int(round(diff))


def _normalize_action_items(items: list | None) -> list[dict[str, str]]:
    """把 mitigation/remediation 统一为 action item dict 列表。

    支持的输入：
        - "字符串"  →  {"description": "字符串"}
        - "owner=..., due=..., url=..., desc=..." 形式
        - 已是 dict 直接保留必要字段
    """

    if not items:
        return []
    out: list[dict[str, str]] = []
    for raw in items:
        if isinstance(raw, dict):
            item = {
                "description": str(raw.get("description") or raw.get("desc") or "").strip(),
                "owner": str(raw.get("owner") or "").strip(),
                "due": str(raw.get("due") or "").strip(),
                "url": str(raw.get("url") or "").strip(),
                "status": str(raw.get("status") or "open").strip(),
            }
        else:
            text = str(raw).strip()
            if "=" in text and any(
                key in text for key in ("owner=", "due=", "url=", "status=", "desc=", "description=")
            ):
                kv: dict[str, str] = {}
                for chunk in re.split(r",\s*", text):
                    if "=" in chunk:
                        k, v = chunk.split("=", 1)
                        kv[k.strip().lower()] = v.strip()
                item = {
                    "description": kv.get("description") or kv.get("desc") or "",
                    "owner": kv.get("owner", ""),
                    "due": kv.get("due", ""),
                    "url": kv.get("url", ""),
                    "status": kv.get("status", "open"),
                }
            else:
                item = {
                    "description": text,
                    "owner": "",
                    "due": "",
                    "url": "",
                    "status": "open",
                }
        if not item["description"]:
            continue
        out.append({k: v for k, v in item.items() if v or k in ("description", "status")})
    return out


def _suggest_severity(blast_radius: str) -> str:
    """根据 blast_radius 文本启发式推荐 severity；不命中则给 sev3 中等。

    规则：
        - 含"全部/所有用户/全站/系统不可用/资金损失" → sev1
        - 含"批量/大面积/N% 用户/超过 N00" → sev2
        - 含"个别/单个用户/单点/单笔" → sev4
        - 其余 → sev3
    """

    text = (blast_radius or "").lower()
    if any(token in text for token in ("全部", "所有用户", "全站", "系统不可用", "资金损失", "重大资损")):
        return "sev1"
    if any(token in text for token in ("批量", "大面积", "%", "千", "万", "百名", "数百", "数千")):
        return "sev2"
    if any(token in text for token in ("单个用户", "个别", "单点", "单笔", "1 人", "1人")):
        return "sev4"
    return "sev3"


def conclude_session(
    path: str | Path,
    *,
    conclusion: str,
    evidence_ids: list[str],
    confidence: str = "medium",
    details: dict[str, str] | None = None,
    next_actions: list[str] | None = None,
    mitigation: list[str] | None = None,
    remediation: list[str] | None = None,
    unsolved: list[str] | None = None,
    pattern_scan: list[str] | None = None,
    related_hypotheses: list[str] | None = None,
    tldr: str | None = None,
    severity: str | None = None,
    detected_at: str | None = None,
    acknowledged_at: str | None = None,
    mitigated_at: str | None = None,
    resolved_at: str | None = None,
) -> dict[str, Any]:
    if not evidence_ids:
        raise CompassRuntimeError("结论必须引用至少一个 evidence id。")
    quality_warnings: list[dict[str, Any]] = []

    tldr_text = (tldr or "").strip()
    if tldr_text:
        sentences = [s for s in re.split(r"[。！？\.!?\n]", tldr_text) if s.strip()]
        if len(sentences) > 3:
            quality_warnings.append(
                {
                    "code": "TLDR_TOO_LONG",
                    "level": "warn",
                    "message": (
                        f"TL;DR 检测到 {len(sentences)} 个句子（建议 ≤3 句）；"
                        "TL;DR 是给非技术决策者一眼看完的摘要，过长会失去价值。"
                    ),
                }
            )

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        if not state.get("scene_facts"):
            raise CompassRuntimeError("缺少场景事实，禁止直接结论。请先通过 scene fact 记录入口、对象、上下游、配置或差异事实。")
        _require_existing_evidence(state, evidence_ids)
        if not state.get("evidence"):
            raise CompassRuntimeError("没有证据，禁止输出结论。")

        # 先做 evidence 存在性校验，再做结论字段校验，
        # 保证错误优先级更符合用户预期与现有测试断言。
        clean_details = _validate_conclusion_details(details or {})
        if severity is not None and severity:
            sev = severity.strip().lower()
            if sev not in SEVERITY_LEVELS:
                raise CompassRuntimeError(
                    f"未知 severity 等级：{severity}。可选：{', '.join(SEVERITY_LEVELS)}。"
                )
        else:
            sev = _suggest_severity(clean_details.get("blast_radius", ""))

        quality_warnings.extend(
            _assess_conclusion_quality(
            state=state,
            summary=conclusion,
            evidence_ids=evidence_ids,
            confidence=confidence,
            details=clean_details,
            mitigation=mitigation or [],
            remediation=remediation or [],
            unsolved=unsolved or [],
            related_hypotheses=related_hypotheses or [],
        )
        )
        if related_hypotheses:
            existing_hids = {str(h.get("id")) for h in state.get("hypotheses") or []}
            invalid = [hid for hid in related_hypotheses if str(hid) not in existing_hids]
            if invalid:
                raise CompassRuntimeError(f"--hypothesis 引用了不存在的假设：{', '.join(invalid)}")

        timing = {}
        detected = (detected_at or state.get("problem", {}).get("detected_at") or "").strip()
        if detected:
            timing["detected_at"] = detected
        if acknowledged_at:
            timing["acknowledged_at"] = acknowledged_at.strip()
        if mitigated_at:
            timing["mitigated_at"] = mitigated_at.strip()
        timing["resolved_at"] = (resolved_at or now_iso()).strip()
        timing["mttd_minutes"] = _diff_minutes(detected, timing.get("acknowledged_at"))
        timing["mttm_minutes"] = _diff_minutes(timing.get("acknowledged_at"), timing.get("mitigated_at"))
        timing["mttr_minutes"] = _diff_minutes(detected, timing.get("resolved_at"))

        state["conclusion"] = {
            "summary": conclusion,
            "tldr": tldr_text,
            "severity": sev,
            "confidence": confidence,
            "evidence": evidence_ids,
            "details": clean_details,
            "inference_steps": _split_inference_steps(clean_details.get("inference_chain", "")),
            "next_actions": next_actions or [],
            "mitigation": _normalize_action_items(mitigation),
            "remediation": _normalize_action_items(remediation),
            "unsolved": list(unsolved or []),
            "pattern_scan": list(pattern_scan or []),
            "related_hypotheses": list(related_hypotheses or []),
            "timing": timing,
            "quality_warnings": quality_warnings,
        }
        state["strategy_review"] = _build_strategy_review(state, conclusion, evidence_ids, clean_details)
        state["flow"].update(
            {
                "phase": "concluded",
                "current_step": "conclusion",
                "report_generated": False,
                "allowed_commands": ["report", "reopen", "state show"],
            }
        )
        _append_event(
            state,
            "conclusion_recorded",
            summary=conclusion,
            refs={"phase": "concluded", "evidence": list(evidence_ids)},
        )
        _touch(state)
        return state

    return _update_runtime_state(path, mutate)


def mark_report_generated(path: str | Path, *, audience: str) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_phase(state, {"concluded", "reported"}, "标记报告已生成")
        if not state.get("conclusion"):
            raise CompassRuntimeError("当前会话没有结论，不能标记报告已生成。")
        state["flow"].update(
            {
                "phase": "reported",
                "current_step": "report",
                "report_generated": True,
                "report_audience": audience,
                "report_generated_at": now_iso(),
                "allowed_commands": ["strategy keep", "strategy discard", "reopen", "state show"],
            }
        )
        _append_event(
            state,
            "report_generated",
            summary=f"audience={audience}",
            refs={"phase": "reported", "audience": audience},
        )
        _touch(state)
        return state

    return _update_runtime_state(path, mutate)


_STRONG_KINDS = {"log", "sql", "code"}
_STRONG_STRENGTHS = {"medium", "strong"}
_CAUSAL_CONNECTORS = (
    "因为",
    "所以",
    "由于",
    "导致",
    "触发",
    "造成",
    "致使",
    "推断",
    "因此",
    "故",
    "→",
    "->",
)

_DIRECT_FAILURE_TERMS = (
    "连不上",
    "不可达",
    "连接失败",
    "连接不上",
    "超时",
    "无响应",
    "离线",
    "心跳中断",
    "校验失败",
    "timeout",
    "unreachable",
    "connection refused",
    "connection failed",
)


def _assess_conclusion_quality(
    *,
    state: dict[str, Any],
    summary: str,
    evidence_ids: list[str],
    confidence: str,
    details: dict[str, str],
    mitigation: list[str],
    remediation: list[str],
    unsolved: list[str],
    related_hypotheses: list[str],
) -> list[dict[str, str]]:
    """对 conclude 输出的结论做软质量检查（不阻塞，只警告）。

    检查项：
        - confidence=high 但缺乏 ≥1 条 strong/medium 强证据 → CONF_GATE
        - inference_chain 缺少因果连接词 → INF_CHAIN_WEAK
        - mitigation 为空 → NO_MITIGATION
        - remediation 为空 → NO_REMEDIATION
        - 推断链与 summary 高度雷同 → INF_CHAIN_DUP
        - 当前会话有"支持"状态假设但 conclude 未引用 → HYP_NOT_REFED
        - 存在"相关"或"待验证"假设但既未排除也未引用 → OPEN_HYP
    """

    warnings: list[dict[str, str]] = []
    evidence_pool = state.get("evidence") or []
    refed_evidence = [e for e in evidence_pool if str(e.get("id")) in set(evidence_ids)]

    has_strong_evidence = any(
        str(e.get("kind", "")).lower() in _STRONG_KINDS
        and str(e.get("strength", "")).lower() in _STRONG_STRENGTHS
        for e in refed_evidence
    )
    if str(confidence).lower() == "high" and not has_strong_evidence:
        warnings.append(
            {
                "code": "CONF_GATE",
                "level": "block",
                "message": (
                    "confidence=high 需要至少 1 条 kind∈{log,sql,code} 且 strength∈{medium,strong} 的强证据；"
                    "当前所引用证据均为弱证据，请补强证据或将 confidence 降至 medium。"
                ),
            }
        )

    inference_chain = (details or {}).get("inference_chain", "") or ""
    inference_text = inference_chain.strip()
    if inference_text:
        if not any(token in inference_text for token in _CAUSAL_CONNECTORS):
            warnings.append(
                {
                    "code": "INF_CHAIN_WEAK",
                    "level": "warn",
                    "message": (
                        "推断链未出现明显因果连接词（因为/所以/由于/导致/→ 等）；"
                        "建议改写为 '观察 X → 因 Y → 触发 Z' 的形式，让因果关系外显。"
                    ),
                }
            )
        if summary and inference_text.replace(" ", "").startswith(summary.replace(" ", "")[:30]):
            warnings.append(
                {
                    "code": "INF_CHAIN_DUP",
                    "level": "warn",
                    "message": (
                        "推断链开头与 summary 高度雷同，疑似只是 summary 的复述；"
                        "推断链应展示证据→中间事实→结论的链路，而不是结论本身。"
                    ),
                }
            )

    mitigation_norm = _normalize_action_items(mitigation)
    remediation_norm = _normalize_action_items(remediation)
    if not mitigation_norm:
        warnings.append(
            {
                "code": "NO_MITIGATION",
                "level": "warn",
                "message": (
                    "未提供 --mitigation（止血动作）。专业排查建议先给出短期止血措施，"
                    "即使本次问题已自愈，也建议明确说明 '无需止血' 的理由。"
                ),
            }
        )
    if not remediation_norm:
        warnings.append(
            {
                "code": "NO_REMEDIATION",
                "level": "warn",
                "message": (
                    "未提供 --remediation（根治动作）。建议把根治措施与负责人/排期写明，"
                    "和 mitigation 区分开。"
                ),
            }
        )
    remediation_no_owner = [r for r in remediation_norm if not r.get("owner")]
    if remediation_norm and remediation_no_owner:
        ids = ", ".join(r.get("description", "") for r in remediation_no_owner[:2])
        warnings.append(
            {
                "code": "REMEDIATION_NO_OWNER",
                "level": "info",
                "message": (
                    f"根治动作未指定 owner（如：{ids}…）。建议用 "
                    "'owner=张三, due=2026-05-10, url=工单链接, desc=...' 形式"
                    "明确责任人/截止时间/工单。"
                ),
            }
        )

    hypotheses = state.get("hypotheses") or []
    refed_hids = set(related_hypotheses)
    supported = [h for h in hypotheses if str(h.get("status", "")).lower() in {"支持", "supported"}]
    supported_no_falsifiable = [
        h for h in supported if not str(h.get("falsifiable", "")).strip()
    ]
    open_hypos = [
        h
        for h in hypotheses
        if str(h.get("status", "")).lower() in {"待验证", "相关", "pending", "related"}
    ]
    if supported and not refed_hids:
        warnings.append(
            {
                "code": "HYP_NOT_REFED",
                "level": "warn",
                "message": (
                    "会话中存在 status=支持 的假设，但 conclude 未通过 --hypothesis 引用任意一个；"
                    "建议显式引用，使结论与假设链路对齐。"
                ),
            }
        )
    if supported_no_falsifiable:
        ids = ", ".join(str(h.get("id", "")) for h in supported_no_falsifiable)
        warnings.append(
            {
                "code": "HYP_NO_FALSIFIABLE",
                "level": "warn",
                "message": (
                    f"已被证据支持的假设（{ids}）未填 falsifiable（反证条件）；"
                    "可证伪是科学结论的最低门槛——请用 `compass hypothesis add --id ... --falsifiable ...` "
                    "补充 '如果 X 不成立则结论不成立' 的反证陈述。"
                ),
            }
        )
    if open_hypos and not unsolved:
        open_ids = ", ".join(str(h.get("id", "")) for h in open_hypos)
        warnings.append(
            {
                "code": "OPEN_HYP",
                "level": "info",
                "message": (
                    f"存在未结论的假设（{open_ids}），但 --unsolved 为空；"
                    "若它们与本次结论无关请显式声明 'unrelated' 或转入 --unsolved 暂列。"
                ),
            }
        )

    conclusion_text = " ".join(
        [
            str(summary or ""),
            str((details or {}).get("why_technical", "")),
            str((details or {}).get("inference_chain", "")),
        ]
    ).lower()
    if _looks_like_direct_failure(conclusion_text) and not _has_change_evidence(state, evidence_ids):
        warnings.append(
            {
                "code": "HALF_ROOT_CAUSE",
                "level": "warn",
                "message": (
                    "当前结论像是只定位到连接失败、不可达、超时、离线或校验失败等直接断点；"
                    "建议继续登记最近发布、配置、网关地址、证书、白名单、DNS、路由、绑定或迁移变更，"
                    "并用时间线、影响面和反证判断它是否是真正根因。"
                ),
            }
        )

    return warnings


def decide_strategy_review(
    path: str | Path,
    *,
    keep: bool,
    note: str = "",
    title: str | None = None,
    memory_path: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output: dict[str, Any] = {}

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        if _phase(state) == "concluded" and not state.get("flow", {}).get("report_generated"):
            raise CompassRuntimeError("请先生成报告，再确认是否保留本次最终查询策略。")
        _require_phase(state, {"reported"}, "确认策略沉淀")
        review = state.get("strategy_review") or {}
        if not review:
            raise CompassRuntimeError("当前会话没有待确认的策略沉淀项。请先通过 conclude 输出结论。")
        if review.get("status") not in {"pending", "kept", "discarded"}:
            raise CompassRuntimeError(f"未知策略沉淀状态：{review.get('status')}。")
        if review.get("status") != "pending":
            raise CompassRuntimeError(f"策略沉淀已确认：{review.get('status')}。如需重新沉淀，请 reopen 后输出新结论。")

        decision = {
            "status": "kept" if keep else "discarded",
            "decided_at": now_iso(),
            "note": note,
        }
        if title:
            review.setdefault("candidate", {})["title"] = title
        review.update(decision)
        state["strategy_review"] = review

        if keep and memory_path:
            _append_strategy_memory(memory_path, review)

        state["flow"].update(
            {
                "current_step": "strategy_review",
                "allowed_commands": ["report", "reopen", "state show"],
            }
        )
        _append_event(
            state,
            "strategy_decided",
            summary=note or decision["status"],
            refs={"status": decision["status"], "phase": _phase(state)},
        )
        _touch(state)
        output["review"] = review
        return state

    state = _update_runtime_state(path, mutate)
    return state, output["review"]


def _build_strategy_review(
    state: dict[str, Any],
    conclusion: str,
    evidence_ids: list[str],
    details: dict[str, str],
) -> dict[str, Any]:
    action_history = state.get("action_history") or []
    completed_actions = [
        {
            "action_id": item.get("action_id"),
            "track": item.get("track"),
            "source": item.get("source"),
            "objective": item.get("objective") or (item.get("input") or {}).get("query") or (item.get("output") or {}).get("summary", ""),
            "success_criteria": item.get("success_criteria", ""),
            "input": item.get("input") or {},
            "gate": item.get("gate") or {},
        }
        for item in action_history
    ]
    scenario = (state.get("problem") or {}).get("standard") or (state.get("problem") or {}).get("raw") or ""
    entity_types = [key for key, value in (state.get("entities") or {}).items() if value not in (None, "", [])]
    services = _strategy_services(completed_actions)
    return {
        "status": "pending",
        "created_at": now_iso(),
        "prompt": "请确认是否将本次最终查询策略保留为同类问题的可复用策略。",
        "candidate": {
            "title": _strategy_title(state, details),
            "scenario": scenario,
            "scene": (state.get("problem") or {}).get("scene", ""),
            "entity_types": entity_types,
            "services": services,
            "source_session_id": state.get("session_id", ""),
            "source_revision": state.get("revision", 1),
            "summary": conclusion,
            "reusable_steps": completed_actions,
            "evidence": evidence_ids,
            "inference_chain": details.get("inference_chain", ""),
            "guardrails": [
                "继续遵循 start/confirm/scene/action/evidence/conclude/report 流程。",
                "SLS/SQL 查询仍必须使用高区分度实体和已验证字段，禁止猜关键词。",
                "该策略只用于问题查询和定位，不代表允许修改业务代码或数据。",
            ],
        },
    }


def _strategy_title(state: dict[str, Any], details: dict[str, str]) -> str:
    scene = (state.get("problem") or {}).get("scene") or "unknown"
    where = details.get("where", "").strip()
    what = details.get("what", "").strip()
    if where and what:
        return f"{scene}：{what} @ {where}"
    if what:
        return f"{scene}：{what}"
    return f"{scene}：线上问题排查策略"


def _strategy_services(actions: list[dict[str, Any]]) -> list[str]:
    services: list[str] = []
    for action in actions:
        source = str(action.get("source") or "").strip()
        if source and source not in services:
            services.append(source)
    return services


def _append_strategy_memory(path: str | Path, review: dict[str, Any]) -> None:
    memory_path = Path(path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _read_strategy_memory(memory_path)
    strategies = payload.setdefault("strategies", [])
    if not isinstance(strategies, list):
        raise CompassRuntimeError(f"策略库 strategies 字段必须是列表：{memory_path}")
    candidate = review.get("candidate") or {}
    strategy = _build_strategy_memory_entry(candidate, review, sequence=len(strategies) + 1)
    strategies.append(strategy)
    _write_strategy_memory(memory_path, payload)


def _build_strategy_memory_entry(candidate: dict[str, Any], review: dict[str, Any], *, sequence: int) -> dict[str, Any]:
    created_at = str(review.get("decided_at") or now_iso())
    title = str(candidate.get("title") or "线上问题排查策略")
    return {
        "id": _strategy_memory_id(title, created_at, sequence),
        "pattern": {
            "category": candidate.get("scene") or "unknown",
            "keywords": _strategy_keywords(candidate),
            "entity_types": candidate.get("entity_types") or [],
            "services": candidate.get("services") or [],
            "scene": candidate.get("scene") or "unknown",
        },
        "plan": _strategy_plan(candidate.get("reusable_steps") or []),
        "score": {
            "effectiveness": 0.0,
            "usage_count": 0,
            "last_used": None,
            "avg_rounds": None,
            "user_ratings": [],
            "modification_count": 0,
        },
        "meta": {
            "created_at": created_at,
            "created_from": "first_use",
            "last_updated": created_at,
            "related_projects": [],
            "pinned": False,
            "source_session_id": candidate.get("source_session_id", ""),
            "source_revision": candidate.get("source_revision", 1),
            "source_summary": candidate.get("summary", ""),
            "source_evidence": candidate.get("evidence") or [],
            "note": review.get("note", ""),
        },
    }


def _strategy_plan(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for index, action in enumerate(actions, start=1):
        gate = action.get("gate") or {}
        action_input = action.get("input") or {}
        objective = str(action.get("objective") or "").strip()
        plan.append(
            {
                "step": index,
                "adapter": str(action.get("track") or action.get("source") or "manual"),
                "action": objective or "按本次证据链继续查询",
                "template": _strategy_action_template(action_input, objective),
                "env_profile": action_input.get("env") or gate.get("env") or gate.get("environment") or "prod",
                "source": str(action.get("source") or ""),
                "success_criteria": str(action.get("success_criteria") or ""),
            }
        )
    return plan


def _strategy_action_template(action_input: dict[str, Any], fallback: str) -> str:
    for key in ("query", "sql", "target"):
        value = str(action_input.get(key) or "").strip()
        if value:
            return value
    return fallback


def _strategy_keywords(candidate: dict[str, Any]) -> list[str]:
    text = " ".join(
        str(candidate.get(key) or "")
        for key in ("title", "scenario", "summary", "inference_chain")
    )
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", text)
    keywords: list[str] = []
    for word in words:
        if word not in keywords:
            keywords.append(word)
        if len(keywords) >= 8:
            break
    return keywords


def _strategy_memory_id(title: str, created_at: str, sequence: int) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_").lower()[:32] or "online_issue"
    day = created_at[:10].replace("-", "") if len(created_at) >= 10 else "unknown"
    return f"strategy_{slug}_{day}_{sequence}"


def _read_strategy_memory(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.read_text(encoding="utf-8").strip():
        return {"strategies": []}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {"strategies": []}
    except ModuleNotFoundError:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise CompassRuntimeError(f"策略库不是合法 YAML/JSON：{path}") from exc


def _write_strategy_memory(path: Path, payload: dict[str, Any]) -> None:
    try:
        import yaml  # type: ignore

        text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    except ModuleNotFoundError:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")


def _validate_conclusion_details(details: dict[str, str]) -> dict[str, str]:
    clean = {key: str(value).strip() for key, value in details.items() if str(value).strip()}
    missing = [field for field in REQUIRED_CONCLUSION_FIELDS if not clean.get(field)]
    if missing:
        raise CompassRuntimeError(f"缺少结论字段：{', '.join(missing)}。")
    quality_errors = _conclusion_quality_errors(clean)
    if quality_errors:
        raise CompassRuntimeError(f"结论字段质量不足：{', '.join(quality_errors)}。")
    return {field: clean[field] for field in REQUIRED_CONCLUSION_FIELDS}


def _validate_action_plan_fields(track: str, action_input: dict[str, str], gate: dict[str, str]) -> None:
    normalized_track = track.lower()
    requirements = TRACK_REQUIREMENTS.get(normalized_track)
    if requirements is None:
        raise CompassRuntimeError(f"未知 action track：{track}。可选：{', '.join(sorted(TRACK_REQUIREMENTS))}。")
    required_input = requirements["input"]
    required_gate = requirements["gate"]
    relaxed_non_prod = normalized_track in {"sls"} and _non_prod_gate_relax_enabled(action_input, gate)
    if relaxed_non_prod:
        required_input = ("query", "time_range")
        required_gate = ("type",)
        env = _action_environment(action_input, gate)
        gate["env"] = env
        gate.setdefault("status", "passed")
        gate.setdefault("risk", "low")
        gate["policy"] = "relaxed_non_prod"
        gate["assessor"] = "compass.runtime.non_prod_gate_relax"

    missing_input = [field for field in required_input if not action_input.get(field)]
    if missing_input:
        raise CompassRuntimeError(f"track {normalized_track} 缺少 input 字段：{', '.join(missing_input)}。")
    missing_gate = [field for field in required_gate if not gate.get(field)]
    if missing_gate:
        raise CompassRuntimeError(f"track {normalized_track} 缺少 gate 字段：{', '.join(missing_gate)}。")
    if normalized_track == "sls" and not relaxed_non_prod:
        _validate_sls_query_policy(action_input, gate)


def _enforce_sql_explain_gate(
    action_input: dict[str, str],
    gate: dict[str, str],
) -> SafetyGateResult:
    """对 SQL 计划做真实门禁评估。

    prod 环境强制要求 input.explain_text，由 runtime 调 ``assess_sql_explain``
    解析风险等级，结果直接覆盖 Agent 自报的 gate 字段，避免"声明就行"的纸老虎。
    test/uat 环境跳过强卡，但仍写入 status=passed/risk=low 的标准 gate 字段。
    """
    sql = str(action_input.get("sql", "")).strip()
    if not sql:
        raise CompassRuntimeError("track sql 缺少 input 字段：sql。")
    env = str(action_input.get("env", "prod")).strip().lower() or "prod"
    explain_text = str(action_input.get("explain_text", "")).strip()
    if env == "prod" and not explain_text:
        raise CompassRuntimeError(
            "track sql 在 prod 环境必须提供 input.explain_text（EXPLAIN 原文）；"
            "runtime 会解析后判定风险，禁止 Agent 自报 gate.status。"
            "如需绕过强卡，请显式声明 env=test 或 env=uat。"
        )
    result = assess_sql_explain(sql, explain_text, env)
    gate["type"] = "sql"
    gate["explain"] = "passed" if result.status == "passed" else result.status
    gate["risk"] = result.risk_level
    gate["status"] = result.status
    gate["env"] = env
    gate["assessor"] = "compass.sql_gate.assess_sql_explain"
    rows = result.details.get("rows")
    if rows is not None:
        gate["rows"] = str(rows)
    if result.details.get("partitions"):
        gate["partitions"] = str(result.details["partitions"])
    if result.details.get("scan"):
        gate["scan"] = str(result.details["scan"])
    if explain_text:
        gate["explain_text"] = explain_text
    return result


def _validate_sls_query_policy(action_input: dict[str, str], gate: dict[str, str]) -> None:
    query = str(action_input.get("query", "")).strip()
    anchor = str(action_input.get("anchor", "")).strip()
    source = str(gate.get("keyword_source", "")).strip().lower()

    if not anchor:
        raise CompassRuntimeError("SLS 查询必须提供 input.anchor，且 anchor 必须是订单号/手机号/userId/traceId/站点名等高区分度实体。")
    if anchor not in query:
        raise CompassRuntimeError("SLS 查询的 input.anchor 必须原样出现在 query 中，禁止没有实体锚点的日志搜索。")
    if not _is_distinctive_sls_anchor(anchor):
        raise CompassRuntimeError(f"SLS 查询 anchor 区分度不足：{anchor}。请使用订单号、支付单号、用户ID、手机号、traceId、枪编码、站点名等实体。")
    keyword_sources = _sls_keyword_sources()
    if source not in keyword_sources:
        raise CompassRuntimeError(
            "SLS gate.keyword_source 必须是 "
            + "/".join(sorted(keyword_sources))
            + "，"
            "额外关键词只能来自代码常量、日志模板、SQL 表字段或表结构。"
        )

    extras = _sls_extra_terms(query, anchor)
    if not extras:
        if source != "none":
            raise CompassRuntimeError("SLS 查询没有额外关键词时，gate.keyword_source 应为 none。")
        return
    generic = sorted(term for term in extras if _is_generic_sls_keyword(term))
    if generic:
        raise CompassRuntimeError(
            "SLS 查询包含低区分度/猜测性关键词："
            + ", ".join(generic)
            + "。请改用实体 id/name，或使用代码/SQL 字段名作为精确关键词。"
        )
    if source == "none":
        raise CompassRuntimeError("SLS 查询包含除 anchor 外的额外关键词，必须声明 gate.keyword_source=code/sql/schema/table_field/code_sql。")


def _is_distinctive_sls_anchor(anchor: str) -> bool:
    lowered = anchor.strip().lower()
    if _is_generic_sls_keyword(lowered):
        return False
    digit_count = sum(ch.isdigit() for ch in anchor)
    if digit_count >= 6:
        return True
    if re.fullmatch(r"[a-f0-9]{16,}", lowered):
        return True
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", anchor))
    if chinese_count >= 6:
        return True
    return len(anchor) >= 8 and any(ch.isalnum() for ch in anchor)


def _sls_extra_terms(query: str, anchor: str) -> list[str]:
    cleaned = query.replace(anchor, " ")
    cleaned = re.sub(r"__tag__:[\w:.-]+", " ", cleaned)
    cleaned = re.sub(r"\b(?:AND|OR|NOT)\b", " ", cleaned, flags=re.IGNORECASE)
    raw_terms = re.split(r"[\s()\"'，,]+", cleaned)
    terms: list[str] = []
    for term in raw_terms:
        item = term.strip()
        if not item or item in {"*", "|"}:
            continue
        if ":" in item:
            item = item.rsplit(":", 1)[-1].strip()
        if item and item not in terms:
            terms.append(item)
    return terms


def _is_generic_sls_keyword(term: str) -> bool:
    normalized = term.strip().lower()
    if not normalized:
        return True
    return normalized in _generic_sls_keywords()


def _generic_sls_keywords() -> set[str]:
    return GENERIC_SLS_KEYWORDS | _csv_env_set("COMPASS_SLS_GENERIC_KEYWORDS")


def _sls_keyword_sources() -> set[str]:
    return _csv_env_set("COMPASS_SLS_KEYWORD_SOURCES") or SLS_EXTRA_KEYWORD_SOURCES


def _csv_env_set(name: str) -> set[str]:
    raw = os.environ.get(name, "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _non_prod_gate_relax_enabled(action_input: dict[str, str], gate: dict[str, str]) -> bool:
    return _truthy_env("COMPASS_NON_PROD_RELAX_GATES") and _action_environment(action_input, gate) != "prod"


def _action_environment(action_input: dict[str, str], gate: dict[str, str]) -> str:
    raw = action_input.get("env") or gate.get("env") or gate.get("environment") or "prod"
    return str(raw).strip().lower() or "prod"


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _validate_evidence_quality(kind: str, strength: str) -> None:
    if kind not in EVIDENCE_KINDS:
        raise CompassRuntimeError(f"未知 evidence kind：{kind}。可选：{', '.join(sorted(EVIDENCE_KINDS))}。")
    if strength not in EVIDENCE_STRENGTHS:
        raise CompassRuntimeError(f"未知 evidence strength：{strength}。可选：{', '.join(sorted(EVIDENCE_STRENGTHS))}。")


def _conclusion_quality_errors(details: dict[str, str]) -> list[str]:
    errors: list[str] = []
    where = details.get("where", "")
    when = details.get("when", "")
    blast_radius = details.get("blast_radius", "")
    why_technical = details.get("why_technical", "")
    how = details.get("how", "")

    if where in {"后端", "系统", "服务端", "客户端"} or not any(marker in where for marker in ("/", "#", ".", "·", "-")):
        errors.append("where 需要包含服务/API/类方法等可定位位置")
    if when in {"今天", "昨天", "最近", "刚刚"} or not re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}", when):
        errors.append("when 需要包含具体日期、时间点或时间窗")
    if any(word in blast_radius for word in ("部分用户", "一些用户", "可能", "未知")):
        errors.append("blast_radius 需要量化或明确写单用户/单站点/待批量确认")
    if why_technical in {"有问题", "异常", "代码问题", "配置问题"} or len(why_technical) < 12:
        errors.append("why_technical 需要说明具体技术原因")
    if how in {"用户操作后出现问题", "触发后异常"} or len(how) < 12:
        errors.append("how 需要说明传播链路")
    return errors


def _load_state(path: str | Path) -> dict[str, Any]:
    state = read_or_init_state(path)
    return _prepare_runtime_state(state)


def _prepare_runtime_state(state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("flow", {})
    state["flow"].setdefault("phase", "new")
    state["flow"].setdefault("confirmed", False)
    state.setdefault("events", [])
    return state


def _update_runtime_state(path: str | Path, mutator) -> dict[str, Any]:
    def wrapped(state: dict[str, Any]):
        return mutator(_prepare_runtime_state(state))

    return update_state(path, wrapped)


def _phase(state: dict[str, Any]) -> str:
    return str(state.get("flow", {}).get("phase", "new"))


def _require_confirmed(state: dict[str, Any]) -> None:
    if not state.get("flow", {}).get("confirmed"):
        raise CompassRuntimeError("会话尚未确认，禁止执行或记录查询动作。请先运行 compass confirm。")


def _require_phase(state: dict[str, Any], allowed: set[str], action_name: str) -> None:
    phase = _phase(state)
    if phase not in allowed:
        raise CompassRuntimeError(f"当前阶段 {phase} 不允许{action_name}。")


def _require_scene_facts(state: dict[str, Any], action_name: str) -> None:
    if not state.get("scene_facts"):
        raise CompassRuntimeError(f"缺少场景事实，禁止{action_name}。请先通过 scene fact 记录入口、对象、上下游、配置或差异事实。")


def _require_existing_evidence(state: dict[str, Any], evidence_ids: list[str]) -> None:
    existing_ids = {item.get("id") for item in state.get("evidence", [])}
    missing = [item for item in evidence_ids if item not in existing_ids]
    if missing:
        raise CompassRuntimeError(f"引用的 evidence 不存在：{', '.join(missing)}。")


def _require_existing_scene_facts(state: dict[str, Any], fact_names: list[str]) -> None:
    existing_names = {item.get("name") for item in state.get("scene_facts", [])}
    missing = [item for item in fact_names if item not in existing_names]
    if missing:
        raise CompassRuntimeError(f"引用的 scene fact 不存在：{', '.join(missing)}。")


def _require_unique_action_id(state: dict[str, Any], action_id: str) -> None:
    existing = {str(item.get("action_id")) for item in state.get("action_history", [])}
    existing.update(str(item.get("action_id")) for item in state.get("action_plan", []))
    if action_id in existing:
        raise CompassRuntimeError(f"action_id 已存在：{action_id}。")


def recall_playbook(
    path: str | Path,
    *,
    all: bool = False,
    matched_playbooks: list[str] | None = None,
    scene_context: str | None = None,
) -> dict[str, Any]:
    if all and matched_playbooks is None:
        playbook_dir = Path(__file__).parent.parent / "knowledge" / "playbooks"
        try:
            all_playbooks = [
                p.stem for p in playbook_dir.glob("*.md")
                if p.name != "_index.md"
            ]
        except Exception:
            all_playbooks = []
        matched = all_playbooks
        scene_context = scene_context or f"全量召回 {len(all_playbooks)} 个 playbook"
    else:
        matched = matched_playbooks or []

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        _require_confirmed(state)
        _require_phase(state, {"action_ready", "evidence_collecting"}, "召回 playbook")
        state["playbook_recall"] = {
            "recalled": True,
            "matched": matched,
            "scene_context": scene_context or "",
            "recalled_at": now_iso(),
        }
        _append_event(state, "playbook_recalled", summary=f"matched: {', '.join(matched)}")
        _touch(state)
        return state

    return _update_runtime_state(path, mutate)


def load_playbook_rules(path: str | Path | None = None) -> list[dict[str, Any]]:
    rules_path = Path(path) if path is not None else Path(__file__).parent.parent / "knowledge" / "playbooks" / "rules.yaml"
    if not rules_path.exists():
        return []
    data = yaml.safe_load(rules_path.read_text(encoding="utf-8")) or {}
    rules = data.get("rules") or []
    if not isinstance(rules, list):
        return []
    return [rule for rule in rules if isinstance(rule, dict) and rule.get("id")]


def _find_action_plan(state: dict[str, Any], action_id: str) -> dict[str, Any]:
    for action in state.get("action_plan", []):
        if action.get("action_id") == action_id:
            return action
    raise CompassRuntimeError(f"action plan 不存在：{action_id}。")


def _require_planned_code_action(state: dict[str, Any], action_id: str) -> tuple[dict[str, Any], Path]:
    action = _find_action_plan(state, action_id)
    if str(action.get("track", "")).lower() != "code":
        raise CompassRuntimeError(f"action {action_id} track 不是 code，禁止通过 code gateway 读取代码。")
    if action.get("status") != "planned":
        raise CompassRuntimeError(f"action {action_id} 状态为 {action.get('status')}，不能读取代码。")
    gate = action.get("gate") or {}
    if str(gate.get("type", "")).lower() != "code":
        raise CompassRuntimeError(f"action {action_id} gate.type 不是 code，不能读取代码。")
    scope = str(gate.get("scope", "")).lower()
    if scope not in {"read-only", "readonly", "repo-read-only"}:
        raise CompassRuntimeError(f"action {action_id} gate.scope 不是 read-only，禁止通过 code gateway 读取代码。")
    repo = str((action.get("input") or {}).get("repo") or "").strip()
    if not repo:
        raise CompassRuntimeError(f"action {action_id} 缺少 input.repo，不能读取代码。")
    repo_path = Path(repo).expanduser().resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise CompassRuntimeError(f"action {action_id} repo 不存在或不是目录：{repo_path}。")
    return action, repo_path


def _resolve_code_path(repo_path: Path, requested: str | Path) -> Path:
    raw = Path(requested).expanduser()
    target = raw.resolve() if raw.is_absolute() else (repo_path / raw).resolve()
    try:
        target.relative_to(repo_path)
    except ValueError as exc:
        raise CompassRuntimeError(f"路径不在 action repo 范围内：{target}。") from exc
    return target


def _search_code_files(
    search_root: Path,
    repo_path: Path,
    *,
    query: str,
    glob: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], bool]:
    keyword = str(query)
    if not keyword:
        raise CompassRuntimeError("code search query 不能为空。")
    max_matches = max(1, int(limit))
    matches: list[dict[str, Any]] = []
    truncated = False
    for file_path in _iter_code_files(search_root, repo_path, glob=glob):
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            for line_number, line in enumerate(text.splitlines(), 1):
                if keyword not in line:
                    continue
                matches.append(
                    {
                        "path": file_path.relative_to(repo_path).as_posix(),
                        "line": line_number,
                        "text": line[:500],
                    }
                )
                if len(matches) >= max_matches:
                    truncated = True
                    return matches, truncated
        except OSError:
            continue
    return matches, truncated


def _iter_code_files(search_root: Path, repo_path: Path, *, glob: str | None) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(search_root):
        dirs[:] = sorted(dirname for dirname in dirs if dirname not in CODE_SEARCH_SKIP_DIRS)
        current_path = Path(current)
        if any(part in CODE_SEARCH_SKIP_DIRS for part in current_path.relative_to(repo_path).parts):
            dirs[:] = []
            continue
        for name in sorted(names):
            path = current_path / name
            if not path.is_file():
                continue
            if glob:
                relative = path.relative_to(repo_path).as_posix()
                if not (fnmatch.fnmatch(relative, glob) or fnmatch.fnmatch(path.name, glob)):
                    continue
            try:
                if path.stat().st_size > CODE_SEARCH_MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            files.append(path)
    return files


def _read_code_lines(path: Path, *, start: int, end: int) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [
        {"line": line_number, "text": lines[line_number - 1]}
        for line_number in range(start, min(end, len(lines)) + 1)
    ]


def _pending_actions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in state.get("action_plan", []) if item.get("status") == "planned"]


def _build_next_task(state: dict[str, Any]) -> dict[str, Any]:
    phase = _phase(state)
    if not state.get("flow", {}).get("confirmed"):
        return _task_card(
            task_type="confirm",
            rationale="首轮人工确认后才能进入自动排查。",
            suggested_commands=["compass confirm --mode auto"],
        )
    pending = _pending_actions(state)
    if pending:
        action = pending[0]
        action_id = str(action.get("action_id", ""))
        track = str(action.get("track", "")).lower()
        suggested = []
        if track in {"sls", "sql"}:
            suggested.append(f"compass action env --action-id {action_id}")
        if track == "code":
            suggested.append(f"compass code search --action-id {action_id} --query <关键字>")
            suggested.append(f"compass code show --action-id {action_id} --path <相对路径> --start <起始行> --end <结束行>")
        suggested.append(f"compass action complete --action-id {action_id} --summary <结果摘要>")
        return _task_card(
            task_type="action_complete",
            rationale="存在 planned action，必须先完成或调整计划。",
            required_inputs=["summary", "finding"],
            suggested_commands=suggested,
        )
    if not state.get("scene_facts"):
        return _task_card(
            task_type="scene_fact",
            rationale="先记录入口、对象、上下游、配置或差异事实，再规划查询动作。",
            required_inputs=["category", "name", "value", "source"],
            suggested_commands=["compass scene fact --category entrypoint --name <入口> --value <事实> --source <来源>"],
        )

    rule = _match_playbook_rule(state)
    if rule:
        task = dict(rule.get("recommended_task") or {})
        task.setdefault("task_type", "action_plan")
        task.setdefault("required_inputs", [])
        task.setdefault("suggested_commands", [])
        task.setdefault("quality_flags", [])
        task["playbook"] = str(rule.get("id", ""))
        return task

    if phase == "evidence_collecting" and state.get("evidence"):
        return _task_card(
            task_type="conclusion_ready",
            rationale="已有场景事实和证据，可继续补证或输出引用证据的结论。",
            required_inputs=["evidence", "what", "where", "when", "why_technical", "inference_chain"],
            suggested_commands=["compass conclude --evidence E1 ..."],
        )
    return _task_card(
        task_type="action_plan",
        rationale="已有场景事实，下一步应规划最小证据动作。",
        required_inputs=["objective", "success_criteria", "track"],
        suggested_commands=["compass action plan --track <sls|code|sql|manual> ..."],
    )


def _task_card(
    *,
    task_type: str,
    rationale: str,
    required_inputs: list[str] | None = None,
    suggested_commands: list[str] | None = None,
    quality_flags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "task_type": task_type,
        "rationale": rationale,
        "required_inputs": list(required_inputs or []),
        "suggested_commands": list(suggested_commands or []),
        "quality_flags": list(quality_flags or []),
    }


def _match_playbook_rule(state: dict[str, Any]) -> dict[str, Any] | None:
    text = _state_search_text(state)
    if not text:
        return None
    rules = load_playbook_rules()
    matched: list[tuple[int, dict[str, Any]]] = []
    for index, rule in enumerate(rules):
        keywords = [str(keyword).lower() for keyword in (rule.get("trigger_keywords") or [])]
        if any(keyword and keyword in text for keyword in keywords):
            matched.append((index, rule))
    if not matched:
        return None
    if state.get("evidence") and not state.get("changes"):
        for _, rule in matched:
            if str(rule.get("id")) == "direct-failure-to-change-root-cause":
                return rule
    return matched[0][1]


def _state_search_text(state: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("problem", "entities"):
        value = state.get(key)
        if isinstance(value, dict):
            parts.extend(str(v) for v in value.values())
        else:
            parts.append(str(value or ""))
    for collection in ("scene_facts", "evidence", "investigation_hints"):
        for item in state.get(collection) or []:
            if isinstance(item, dict):
                parts.extend(str(v) for v in item.values())
    return " ".join(parts).lower()


def _build_session_health(state: dict[str, Any]) -> dict[str, Any]:
    pending_count = len(_pending_actions(state))
    scene_count = len(state.get("scene_facts") or [])
    evidence_count = len(state.get("evidence") or [])
    change_count = len(state.get("changes") or [])
    open_hypotheses = [
        h
        for h in state.get("hypotheses") or []
        if str(h.get("status", "")).lower() in {"待验证", "相关", "pending", "related"}
    ]
    conclusion_warnings = (state.get("conclusion") or {}).get("quality_warnings") or []
    flags: list[str] = []
    if pending_count:
        flags.append("pending_actions")
    if evidence_count and not change_count:
        flags.append("no_changes_recorded")
    if open_hypotheses:
        flags.append("open_hypotheses")
    if any(str(w.get("code")) == "HALF_ROOT_CAUSE" for w in conclusion_warnings):
        flags.append("possible_half_root_cause")
    return {
        "phase": _phase(state),
        "scene_facts": scene_count,
        "evidence": evidence_count,
        "changes": change_count,
        "pending_actions": pending_count,
        "open_hypotheses": len(open_hypotheses),
        "events": len(state.get("events") or []),
        "quality_flags": flags,
    }


def _build_action_context(
    state: dict[str, Any],
    *,
    track: str,
    applied_playbooks: list[str],
) -> dict[str, Any]:
    recall = state.get("playbook_recall") or {}
    matched = _clean_list(recall.get("matched") if isinstance(recall.get("matched"), list) else [])
    quality_flags: list[str] = []
    if not recall.get("recalled"):
        quality_flags.append("PLAYBOOK_RECALL_MISSING")
    if not applied_playbooks:
        quality_flags.append("PLAYBOOK_NOT_APPLIED")
    return {
        "playbook_index": "knowledge/playbooks/_index.md",
        "playbook_recall": {
            "recalled": bool(recall.get("recalled")),
            "matched": matched,
            "scene_context": str(recall.get("scene_context") or ""),
            "recalled_at": str(recall.get("recalled_at") or ""),
        },
        "knowledge_candidates": _action_knowledge_candidates(state),
        "investigation_hints": [
            {
                "id": str(item.get("id", "")),
                "type": str(item.get("type", "")),
                "statement": str(item.get("statement", "")),
                "status": str(item.get("status", "")),
            }
            for item in (state.get("investigation_hints") or [])
            if isinstance(item, dict)
        ],
        "track": track,
        "quality_flags": quality_flags,
    }


def _action_knowledge_candidates(state: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for item in state.get("applicable_knowledge") or []:
        if not isinstance(item, dict):
            continue
        candidates.append(
            {
                "id": str(item.get("id", "")),
                "tags": [str(tag) for tag in (item.get("tags") or [])],
                "statement": str(item.get("statement", "")),
            }
        )
    return candidates


def _build_action_history_item(
    *,
    action_id: str,
    track: str,
    source: str,
    action_input: dict[str, str],
    gate: dict[str, str],
    objective: str = "",
    success_criteria: str = "",
    summary: str,
    findings: list[str],
    leads: dict[str, list[str]],
    elapsed_ms: int,
    evidence_id: str,
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "track": track,
        "source": source,
        "objective": objective,
        "success_criteria": success_criteria,
        "input": action_input,
        "gate": gate,
        "output": {
            "summary": summary,
            "findings": findings,
            "leads": leads,
            "elapsed_ms": elapsed_ms,
            "evidence_id": evidence_id,
        },
    }


def _clean_list(values: list[str] | None) -> list[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()]


def _append_event(
    state: dict[str, Any],
    event_type: str,
    *,
    summary: str = "",
    refs: dict[str, Any] | None = None,
) -> None:
    events = state.setdefault("events", [])
    event = {
        "type": event_type,
        "created_at": now_iso(),
        "phase": _phase(state),
        "summary": str(summary or "").strip(),
        "refs": refs or {},
    }
    events.append(event)
    if len(events) > 200:
        del events[:-200]


def _build_evidence(
    state: dict[str, Any],
    *,
    source: str,
    summary: str,
    findings: list[str],
    supports: str | None,
    action_id: str | None,
    kind: str,
    strength: str,
    raw_ref: str | None,
    event_at: str | None = None,
    change_ids: list[str] | None = None,
) -> dict[str, Any]:
    _validate_evidence_quality(kind, strength)
    evidence_id = f"E{len(state.get('evidence', [])) + 1}"
    evidence: dict[str, Any] = {
        "id": evidence_id,
        "source": source,
        "summary": summary,
        "kind": kind,
        "strength": strength,
        "created_at": now_iso(),
    }
    if findings:
        evidence["findings"] = findings
    if supports:
        evidence["supports"] = supports
    if action_id:
        evidence["action_id"] = action_id
    if raw_ref:
        evidence["raw_ref"] = raw_ref
    if event_at:
        evidence["event_at"] = event_at
    if change_ids:
        normalized = [str(cid).strip() for cid in change_ids if str(cid).strip()]
        if normalized:
            evidence["change_ids"] = normalized
    return evidence


def _require_existing_changes(state: dict[str, Any], change_ids: list[str]) -> None:
    """校验引用的 change_id 必须已经登记，否则抛出。"""

    if not change_ids:
        return
    existing = {str(c.get("id", "")).strip() for c in (state.get("changes") or [])}
    missing = [cid for cid in change_ids if cid and cid not in existing]
    if missing:
        raise CompassRuntimeError(
            "引用的变更不存在：" + ", ".join(missing) + "。请先通过 `compass change record ...` 登记变更。"
        )


def _kind_from_track(track: str) -> str:
    normalized = track.lower()
    return normalized if normalized in {"log", "sql", "code", "kb", "manual"} else {"sls": "log"}.get(normalized, "manual")


def _looks_like_direct_failure(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(term.lower() in lowered for term in _DIRECT_FAILURE_TERMS)


def _has_change_evidence(state: dict[str, Any], evidence_ids: list[str]) -> bool:
    if state.get("changes"):
        return True
    referenced = {str(eid) for eid in evidence_ids}
    for evidence in state.get("evidence") or []:
        if str(evidence.get("id")) in referenced and evidence.get("change_ids"):
            return True
    for hypothesis in state.get("hypotheses") or []:
        if hypothesis.get("source_changes"):
            return True
    return False


def _mark_hypothesis(state: dict[str, Any], hypothesis_id: str | None, evidence_id: str) -> None:
    if not hypothesis_id:
        return
    found = False
    for hypothesis in state.get("hypotheses", []):
        if hypothesis.get("id") == hypothesis_id:
            hypothesis["status"] = "支持"
            hypothesis.setdefault("evidence", []).append(evidence_id)
            found = True
            break
    if not found:
        state.setdefault("hypotheses", []).append(
            {"id": hypothesis_id, "statement": "用户补充的临时假设", "status": "支持", "evidence": [evidence_id]}
        )


def _touch(state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
