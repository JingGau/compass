from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationAction:
    step_id: str
    title: str
    track: str
    purpose: str
    tool: str
    environment: str
    target: dict[str, Any]
    expected: str
    source: str | None = None


@dataclass
class SafetyGateResult:
    gate_type: str
    status: str
    risk_level: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    confirmation_id: str | None = None


@dataclass
class ActionResult:
    status: str
    elapsed_ms: int
    summary: str
    key_findings: list[str] = field(default_factory=list)
    leads: dict[str, list[str]] = field(default_factory=dict)
    next_actions: list[str] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)


def should_execute(gate: SafetyGateResult, confirmed: bool = False) -> bool:
    if gate.requires_confirmation and not confirmed:
        return False
    return gate.status in {"passed", "warning", "confirmed"}


def build_pending_confirmation(action: InvestigationAction, gate: SafetyGateResult) -> dict[str, Any]:
    confirmation_id = gate.confirmation_id or f"{action.step_id}:{gate.gate_type}:{gate.risk_level}"
    return {
        "id": confirmation_id,
        "action_id": action.step_id,
        "title": action.title,
        "gate_type": gate.gate_type,
        "risk_level": gate.risk_level,
        "summary": gate.summary,
        "required_reply": "确认执行",
    }


def render_before_card(action: InvestigationAction) -> str:
    lines = [
        f"▶ Step {action.step_id} — {action.title}",
        f"- 目的：{action.purpose}",
        f"- 工具：{action.tool} · 环境/Profile：{action.environment}",
    ]
    if action.source:
        lines.append(f"- 来源线索：{action.source}")

    if action.track == "sql":
        lines.extend(
            [
                "- 将执行 SQL：",
                _indent_code(str(action.target.get("sql", "未提供 SQL"))),
            ]
        )
    elif action.track == "sls":
        lines.extend(
            [
                "- 将执行 SLS 查询：",
                f"  query: {action.target.get('query', '未提供 query')}",
                f"  time_range: {action.target.get('time_range', '未提供')}",
                f"  limit: {action.target.get('limit', '未提供')}",
            ]
        )
    elif action.track == "code":
        applications = action.target.get("applications") or []
        methods = action.target.get("methods") or []
        if applications:
            lines.append(f"- 应用：{' → '.join(map(str, applications))}")
        lines.append("- 将读取：")
        for idx, method in enumerate(methods, start=1):
            lines.append(f"  {idx}. {method}")
        if not methods:
            lines.append("  1. 未提供方法名，需先根据页面/API/关键字定位")
    else:
        lines.append(f"- 查询对象：{_format_target(action.target)}")

    lines.append(f"- 成功标准：{action.expected}")
    return "\n".join(lines)


def render_safety_gate_card(action: InvestigationAction, gate: SafetyGateResult) -> str:
    icon = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(gate.risk_level, "⚪")
    lines = [
        f"🔒 Safety Gate — {gate.gate_type.upper()}",
        f"├ 步骤：{action.step_id} · {action.title}",
        f"├ 判定：{icon} {gate.risk_level} · {gate.status}",
        f"├ 摘要：{gate.summary}",
    ]
    for key, value in gate.details.items():
        lines.append(f"├ {key}：{value}")

    if gate.requires_confirmation:
        lines.extend(
            [
                "└ 状态：已暂停，等待用户确认",
                "",
                "⚠️ 请明确回复「确认执行」才会继续，其他回复均视为取消。",
                "",
                "**[确认执行]** **[我来改写 SQL]** **[跳过此步]**",
            ]
        )
    else:
        lines.append("└ 状态：通过，可继续执行")
    return "\n".join(lines)


def render_after_card(action: InvestigationAction, result: ActionResult) -> str:
    lines = [
        f"✅ Step {action.step_id} 完成 · 耗时 {_format_elapsed(result.elapsed_ms)}",
        f"- 结果摘要：{result.summary}",
    ]
    if result.key_findings:
        lines.append("- 关键发现：")
        for finding in result.key_findings:
            lines.append(f"  · {finding}")
    else:
        lines.append("- 关键发现：未发现，需换关键字/扩大时间窗/切换轨道重试")

    lines.append("- 提取线索：")
    lines.extend(_render_leads(result.leads))

    if result.next_actions:
        lines.append("- 可继续下钻：")
        for idx, next_action in enumerate(result.next_actions, start=1):
            lines.append(f"  {idx}. {next_action}")
        lines.append(f"- 下一步：→ {result.next_actions[0]}")
    else:
        lines.append("- 下一步：→ 暂无自动候选，需人工选择补充轨道")
    return "\n".join(lines)


def _render_leads(leads: dict[str, list[str]]) -> list[str]:
    label_map = {
        "trace_ids": "traceId",
        "interfaces": "接口",
        "methods": "方法",
        "tables": "表",
        "keys": "key",
        "timestamps": "时间戳",
    }
    lines: list[str] = []
    for key, label in label_map.items():
        values = [str(v) for v in leads.get(key, []) if str(v)]
        if values:
            lines.append(f"  · {label}：{', '.join(values)}")
        else:
            lines.append(f"  · {label}：未发现")
    return lines


def _indent_code(text: str) -> str:
    return "\n".join(f"  {line}" for line in text.splitlines())


def _format_target(target: dict[str, Any]) -> str:
    return "；".join(f"{key}={value}" for key, value in target.items()) or "未提供"


def _format_elapsed(elapsed_ms: int) -> str:
    if elapsed_ms >= 1000:
        return f"{elapsed_ms / 1000:.1f}s"
    return f"{elapsed_ms}ms"

