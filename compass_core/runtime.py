from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from compass_core.intake import intake_problem
from compass_core.state import default_state, now_iso, read_or_init_state, write_state
from tools.action_cards import ActionResult
from tools.evidence_graph import EvidenceGraph


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
        "gate": ("type", "explain", "risk"),
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
    state.setdefault("action_plan", []).append(action)
    state["flow"].update(
        {
            "phase": "evidence_collecting",
            "current_step": "action_planning",
            "allowed_commands": ["next", "action complete", "action plan", "scene fact", "hypothesis add", "evidence add", "state show"],
        }
    )
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
) -> tuple[dict[str, Any], dict[str, Any]]:
    state = _load_state(path)
    _require_confirmed(state)
    _require_phase(state, {"action_ready", "evidence_collecting"}, "完成 action")
    action = _find_action_plan(state, action_id)
    if action.get("status") == "completed":
        raise CompassRuntimeError(f"action 已完成：{action_id}。")
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
    )
    state.setdefault("evidence", []).append(evidence)
    state.setdefault("action_history", []).append(
        _build_action_history_item(
            action_id=action_id,
            track=str(action.get("track", "manual")),
            source=str(action.get("source", "unknown")),
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
    state.setdefault("conclusion_history", []).append(archived)
    state.pop("conclusion", None)
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


def add_scene_fact(
    path: str | Path,
    *,
    category: str,
    name: str,
    value: str,
    source: str,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    state = _load_state(path)
    _require_confirmed(state)
    _require_phase(state, {"action_ready", "evidence_collecting"}, "记录场景事实")
    _require_existing_evidence(state, evidence_ids or [])
    fact = {
        "category": category,
        "name": name,
        "value": value,
        "source": source,
        "evidence": evidence_ids or [],
        "created_at": now_iso(),
    }
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
    hypothesis = {
        "id": hypothesis_id,
        "statement": statement,
        "status": "待验证",
        "source_facts": facts,
        "source_evidence": evidence,
    }
    if hypothesis_id in existing:
        for idx, item in enumerate(state.get("hypotheses", [])):
            if item.get("id") == hypothesis_id:
                state["hypotheses"][idx] = {**item, **hypothesis}
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
    state["conclusion"] = {
        "summary": conclusion,
        "confidence": confidence,
        "evidence": evidence_ids,
        "details": clean_details,
        "next_actions": next_actions or [],
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
        _append_strategy_playbook(memory_path, review)

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
            "objective": (item.get("input") or {}).get("query") or (item.get("output") or {}).get("summary", ""),
            "gate": item.get("gate") or {},
        }
        for item in action_history
    ]
    scenario = (state.get("problem") or {}).get("standard") or (state.get("problem") or {}).get("raw") or ""
    return {
        "status": "pending",
        "created_at": now_iso(),
        "prompt": "请确认是否将本次最终查询策略保留为同类问题的可复用策略。",
        "candidate": {
            "title": _strategy_title(state, details),
            "scenario": scenario,
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


def _append_strategy_playbook(path: str | Path, review: dict[str, Any]) -> None:
    playbook_path = Path(path)
    playbook_path.parent.mkdir(parents=True, exist_ok=True)
    if playbook_path.exists() and playbook_path.read_text(encoding="utf-8").strip():
        try:
            payload = json.loads(playbook_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CompassRuntimeError(f"策略库不是合法 JSON：{playbook_path}") from exc
    else:
        payload = {"strategies": []}
    payload.setdefault("strategies", []).append(
        {
            "kept_at": review.get("decided_at"),
            "note": review.get("note", ""),
            **(review.get("candidate") or {}),
        }
    )
    playbook_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
