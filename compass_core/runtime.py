from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from compass_core.intake import intake_problem
from compass_core.state import default_state, now_iso, read_or_init_state, write_state
from tools.action_cards import ActionResult, SafetyGateResult
from tools.evidence_graph import EvidenceGraph
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


def start_session(path: str | Path, text: str) -> dict[str, Any]:
    intake = intake_problem(text)
    state = default_state()
    state["problem"] = {
        "raw": intake.raw_problem,
        "standard": intake.standard_problem,
        "scene": intake.scene,
        "environment": intake.environment,
        "impact": "未知",
    }
    state["environment"] = intake.environment
    state["mode"] = "investigation_only"
    state["write_policy"] = "no_code_or_data_mutation"
    state["entities"] = intake.entities
    state["missing"] = intake.missing
    state["hypotheses"] = intake.hypotheses
    state["hypothesis_mode"] = "initial_from_intake"
    state["scene_facts"] = []
    state["next_actions"] = intake.next_actions
    state["evidence_graph"] = {"nodes": [], "edges": []}
    state["applicable_knowledge"] = _recall_applicable_knowledge(intake, top_n=5)
    state["flow"].update(
        {
            "phase": "awaiting_confirmation",
            "confirmed": False,
            "allowed_commands": ["confirm", "state show"],
            "current_step": "intake",
        }
    )
    write_state(path, state)
    return state


def _maybe_reflection_questions(state: dict[str, Any]) -> dict[str, Any] | None:
    """当证据/假设具备一定深度时，输出"根因反思三问"。

    触发条件（满足任一即提示）：
        - 证据数 ≥ 3 且 至少 1 条 strong/medium 级别证据；
        - 至少 1 个 status=支持 的假设；
        - 已登记变更（state.changes 非空）。

    若三问已展示过（state.flow.reflection_shown），则不重复打扰。
    """

    flow = state.get("flow") or {}
    if flow.get("reflection_shown"):
        return None
    evidence = state.get("evidence") or []
    if not evidence:
        return None

    strong_count = sum(
        1
        for e in evidence
        if str(e.get("kind", "")).lower() in _STRONG_KINDS
        and str(e.get("strength", "")).lower() in _STRONG_STRENGTHS
    )
    hypotheses = state.get("hypotheses") or []
    supported = [
        h
        for h in hypotheses
        if str(h.get("status", "")).lower() in {"支持", "supported"}
    ]
    has_changes = bool(state.get("changes"))

    trigger = (len(evidence) >= 3 and strong_count >= 1) or supported or has_changes
    if not trigger:
        return None

    questions = [
        "1) 这是【现象】还是【根因】？把当前结论再问一次 'why'，能不能继续往下挖？",
        "2) 为什么【之前】没出问题、【现在】才出？把'变化点'（变更/数据/流量/上游）跟故障窗口对齐。",
        "3) 同一根因还会影响哪些【相邻入口/数据/链路】？同类是不是也已经/即将出问题？",
    ]
    state["flow"]["reflection_shown"] = True
    path = state.get("__path__")
    if path:
        snapshot = {k: v for k, v in state.items() if k != "__path__"}
        write_state(path, snapshot)
    return {
        "phase": "evidence_collecting",
        "blocked": False,
        "message": (
            "证据已具备一定深度，请先做【根因反思三问】，再决定是否输出 conclude：\n"
            + "\n".join(questions)
        ),
        "reflection": questions,
        "next_actions": [
            "scene fact (category=baseline 或 diff，把'之前/正常'与'之后/异常'对比写下来)",
            "change record (登记疑似引发本次问题的变更)",
            "hypothesis add (把反思中浮现的新猜想登记)",
            "conclude (若三问都过得去则可以输出结论)",
        ],
    }


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
    state = _load_state(path)
    phase = _phase(state)
    if phase not in {"awaiting_confirmation", "action_ready"}:
        raise CompassRuntimeError(f"当前阶段 {phase} 不需要确认。")
    state["flow"].update(
        {
            "phase": "action_ready",
            "confirmed": True,
            "execution_mode": mode,
            "allowed_commands": ["next", "action record", "evidence add", "state show"],
        }
    )
    _touch(state)
    write_state(path, state)
    return state


def next_step(path: str | Path) -> dict[str, Any]:
    state = _load_state(path)
    state["__path__"] = str(path)
    phase = _phase(state)
    if not state.get("flow", {}).get("confirmed"):
        return {
            "phase": phase,
            "blocked": True,
            "message": "会话尚未确认执行模式。请先运行 compass confirm。",
            "next_actions": ["confirm"],
        }
    if phase == "action_ready":
        if not state.get("scene_facts"):
            return {
                "phase": phase,
                "blocked": False,
                "message": "请先记录场景事实，展开入口、对象、上下游、配置或差异，再基于事实推进查询和假设。",
                "next_actions": ["scene fact", "action record"],
            }
        return {
            "phase": phase,
            "blocked": False,
            "message": "已有场景事实，请继续记录查询证据，或从事实/证据派生新假设。",
            "next_actions": ["action record", "hypothesis add", "scene fact"],
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
            }
        if not state.get("scene_facts"):
            return {
                "phase": phase,
                "blocked": False,
                "message": "已有证据，但还缺少场景事实。请先用 scene fact 记录入口、对象、上下游、配置或差异。",
                "next_actions": ["scene fact", "action record"],
            }
        reflection = _maybe_reflection_questions(state)
        if reflection is not None:
            return reflection
        return {
            "phase": phase,
            "blocked": False,
            "message": "已有场景事实和证据，可继续补证据、派生假设，或输出带证据引用的结论。",
            "next_actions": ["action record", "hypothesis add", "conclude"],
        }
    if phase == "concluded":
        review = state.get("strategy_review") or {}
        if review.get("status") == "pending":
            return {
                "phase": phase,
                "blocked": False,
                "message": "排查已输出结论。请先生成报告，并确认是否保留本次最终查询策略。",
                "next_actions": ["report", "strategy keep", "strategy discard"],
            }
        return {
            "phase": phase,
            "blocked": False,
            "message": "排查已输出结论。",
            "next_actions": ["report"],
        }
    return {"phase": phase, "blocked": False, "message": "继续推进。", "next_actions": []}


def record_action_result(
    path: str | Path,
    *,
    action_id: str,
    source: str,
    summary: str,
    track: str = "manual",
    action_input: dict[str, str] | None = None,
    gate: dict[str, str] | None = None,
    elapsed_ms: int = 0,
    findings: list[str] | None = None,
    leads: dict[str, list[str]] | None = None,
    supports: str | None = None,
    kind: str | None = None,
    strength: str = "medium",
    raw_ref: str | None = None,
    event_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _load_state(path)
    _require_confirmed(state)
    _require_phase(state, {"action_ready", "evidence_collecting"}, "记录 action")
    _require_unique_action_id(state, action_id)
    if track.lower() != "manual" or action_input or gate:
        _validate_action_plan_fields(track, action_input or {}, gate or {})
    evidence = _build_evidence(
        state,
        source=source,
        summary=summary,
        findings=findings or [],
        supports=supports,
        action_id=action_id,
        kind=kind or _kind_from_track(track),
        strength=strength,
        raw_ref=raw_ref,
        event_at=event_at,
    )
    state.setdefault("evidence", []).append(evidence)
    state.setdefault("action_history", []).append(
        _build_action_history_item(
            action_id=action_id,
            track=track,
            source=source,
            action_input=action_input or {},
            gate=gate or {},
            summary=summary,
            findings=findings or [],
            leads=leads or {},
            elapsed_ms=elapsed_ms,
            evidence_id=evidence["id"],
        )
    )
    _mark_hypothesis(state, supports, evidence["id"])
    _add_action_leads(state, action_id, summary, findings or [], leads or {})
    state["flow"].update(
        {
            "phase": "evidence_collecting",
            "current_step": "evidence",
            "allowed_commands": ["next", "action record", "evidence add", "conclude", "state show"],
        }
    )
    _touch(state)
    write_state(path, state)
    return state, evidence


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
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _load_state(path)
    _require_confirmed(state)
    _require_phase(state, {"action_ready", "evidence_collecting"}, "规划 action")
    _require_unique_action_id(state, action_id)
    inputs = action_input or {}
    if track.lower() == "sql" and not inputs.get("env"):
        inputs["env"] = str(state.get("environment") or state.get("problem", {}).get("environment") or "prod")
    gates = gate or {}
    _validate_action_plan_fields(track, inputs, gates)
    sql_gate_result: SafetyGateResult | None = None
    if track.lower() == "sql":
        sql_gate_result = _enforce_sql_explain_gate(inputs, gates)
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
    }
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
    _touch(state)
    write_state(path, state)
    return state, action


def confirm_action(
    path: str | Path,
    *,
    action_id: str,
    note: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _load_state(path)
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
    _touch(state)
    write_state(path, state)
    return state, action


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
    state = _load_state(path)
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
    _add_action_leads(state, action_id, summary, findings or [], leads or {})
    state["flow"].update(
        {
            "phase": "evidence_collecting",
            "current_step": "evidence",
            "allowed_commands": ["next", "action plan", "action complete", "evidence add", "hypothesis add", "conclude", "state show"],
        }
    )
    _touch(state)
    write_state(path, state)
    return state, evidence


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
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _load_state(path)
    _require_confirmed(state)
    _require_phase(state, {"action_ready", "evidence_collecting"}, "新增证据")
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
    _touch(state)
    write_state(path, state)
    return state, evidence


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

    state = _load_state(path)
    _require_confirmed(state)
    _require_phase(state, {"action_ready", "evidence_collecting"}, "登记变更")
    _require_existing_evidence(state, evidence_ids or [])
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
    _touch(state)
    write_state(path, state)
    return state, record


def reopen_session(path: str | Path, *, reason: str) -> dict[str, Any]:
    state = _load_state(path)
    _require_confirmed(state)
    _require_phase(state, {"concluded"}, "重开排查")
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
            "allowed_commands": ["next", "action plan", "action complete", "evidence add", "scene fact", "hypothesis add", "conclude", "state show"],
        }
    )
    _touch(state)
    write_state(path, state)
    return state


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
    state = _load_state(path)
    _require_confirmed(state)
    _require_phase(state, {"action_ready", "evidence_collecting"}, "记录场景事实")
    _require_existing_evidence(state, evidence_ids or [])
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
            "allowed_commands": ["next", "scene fact", "hypothesis add", "action record", "evidence add", "conclude", "state show"],
        }
    )
    _touch(state)
    write_state(path, state)
    return state


def add_hypothesis(
    path: str | Path,
    *,
    hypothesis_id: str,
    statement: str,
    source_facts: list[str] | None = None,
    source_evidence: list[str] | None = None,
    falsifiable: str | None = None,
) -> dict[str, Any]:
    state = _load_state(path)
    _require_confirmed(state)
    _require_phase(state, {"action_ready", "evidence_collecting"}, "新增假设")
    facts = source_facts or []
    evidence = source_evidence or []
    if not facts and not evidence:
        raise CompassRuntimeError("假设必须引用至少一个 scene fact 或 evidence。")
    _require_existing_scene_facts(state, facts)
    _require_existing_evidence(state, evidence)
    existing = {item.get("id") for item in state.get("hypotheses", [])}
    hypothesis: dict[str, Any] = {
        "id": hypothesis_id,
        "statement": statement,
        "status": "待验证",
        "source_facts": facts,
        "source_evidence": evidence,
    }
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
    _touch(state)
    write_state(path, state)
    return state


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
) -> dict[str, Any]:
    state = _load_state(path)
    _require_confirmed(state)
    if not state.get("scene_facts"):
        raise CompassRuntimeError("缺少场景事实，禁止直接结论。请先通过 scene fact 记录入口、对象、上下游、配置或差异事实。")
    if not evidence_ids:
        raise CompassRuntimeError("结论必须引用至少一个 evidence id。")
    _require_existing_evidence(state, evidence_ids)
    if not state.get("evidence"):
        raise CompassRuntimeError("没有证据，禁止输出结论。")
    clean_details = _validate_conclusion_details(details or {})
    quality_warnings = _assess_conclusion_quality(
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
    if related_hypotheses:
        existing_hids = {str(h.get("id")) for h in state.get("hypotheses") or []}
        invalid = [hid for hid in related_hypotheses if str(hid) not in existing_hids]
        if invalid:
            raise CompassRuntimeError(f"--hypothesis 引用了不存在的假设：{', '.join(invalid)}")
    state["conclusion"] = {
        "summary": conclusion,
        "confidence": confidence,
        "evidence": evidence_ids,
        "details": clean_details,
        "next_actions": next_actions or [],
        "mitigation": list(mitigation or []),
        "remediation": list(remediation or []),
        "unsolved": list(unsolved or []),
        "pattern_scan": list(pattern_scan or []),
        "related_hypotheses": list(related_hypotheses or []),
        "quality_warnings": quality_warnings,
    }
    state["strategy_review"] = _build_strategy_review(state, conclusion, evidence_ids, clean_details)
    state["flow"].update(
        {
            "phase": "concluded",
            "current_step": "conclusion",
            "allowed_commands": ["report", "strategy keep", "strategy discard", "state show"],
        }
    )
    _touch(state)
    write_state(path, state)
    return state


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

    if not mitigation:
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
    if not remediation:
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

    return warnings


def decide_strategy_review(
    path: str | Path,
    *,
    keep: bool,
    note: str = "",
    title: str | None = None,
    memory_path: str | Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _load_state(path)
    _require_phase(state, {"concluded"}, "确认策略沉淀")
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

    _touch(state)
    write_state(path, state)
    return state, review


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
    missing_input = [field for field in requirements["input"] if not action_input.get(field)]
    if missing_input:
        raise CompassRuntimeError(f"track {normalized_track} 缺少 input 字段：{', '.join(missing_input)}。")
    missing_gate = [field for field in requirements["gate"] if not gate.get(field)]
    if missing_gate:
        raise CompassRuntimeError(f"track {normalized_track} 缺少 gate 字段：{', '.join(missing_gate)}。")
    if normalized_track == "sls":
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
    if source not in SLS_EXTRA_KEYWORD_SOURCES:
        raise CompassRuntimeError(
            "SLS gate.keyword_source 必须是 code/sql/schema/table_field/code_sql/none，"
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
    return normalized in GENERIC_SLS_KEYWORDS


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
    state.setdefault("flow", {})
    state["flow"].setdefault("phase", "new")
    state["flow"].setdefault("confirmed", False)
    return state


def _phase(state: dict[str, Any]) -> str:
    return str(state.get("flow", {}).get("phase", "new"))


def _require_confirmed(state: dict[str, Any]) -> None:
    if not state.get("flow", {}).get("confirmed"):
        raise CompassRuntimeError("会话尚未确认，禁止执行或记录查询动作。请先运行 compass confirm。")


def _require_phase(state: dict[str, Any], allowed: set[str], action_name: str) -> None:
    phase = _phase(state)
    if phase not in allowed:
        raise CompassRuntimeError(f"当前阶段 {phase} 不允许{action_name}。")


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


def _find_action_plan(state: dict[str, Any], action_id: str) -> dict[str, Any]:
    for action in state.get("action_plan", []):
        if action.get("action_id") == action_id:
            return action
    raise CompassRuntimeError(f"action plan 不存在：{action_id}。")


def _pending_actions(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in state.get("action_plan", []) if item.get("status") == "planned"]


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
    return evidence


def _kind_from_track(track: str) -> str:
    normalized = track.lower()
    return normalized if normalized in {"log", "sql", "code", "kb", "manual"} else {"sls": "log"}.get(normalized, "manual")


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


def _add_action_leads(
    state: dict[str, Any],
    action_id: str,
    summary: str,
    findings: list[str],
    leads: dict[str, list[str]],
) -> None:
    graph = EvidenceGraph()
    for node in state.get("evidence_graph", {}).get("nodes", []):
        graph.add_node(str(node.get("type", "unknown")), str(node.get("value", "")))
    for edge in state.get("evidence_graph", {}).get("edges", []):
        from_type, from_value = _split_node_id(str(edge.get("from", "")))
        to_type, to_value = _split_node_id(str(edge.get("to", "")))
        graph.link(from_type, from_value, to_type, to_value, str(edge.get("relation", "links")))
    result = ActionResult(
        status="success",
        elapsed_ms=0,
        summary=summary,
        key_findings=findings,
        leads=leads,
        next_actions=[],
    )
    graph.add_result_leads(action_id, result)
    state["evidence_graph"] = graph.to_dict()


def _split_node_id(node_id: str) -> tuple[str, str]:
    node_type, separator, value = node_id.partition(":")
    if not separator:
        return "unknown", node_id
    return node_type, value


def _touch(state: dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
