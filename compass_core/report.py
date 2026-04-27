from __future__ import annotations

from pathlib import Path
from typing import Any

from compass_core.masking import mask_mapping, mask_text, mask_value
from compass_core.state import read_state


def load_state(path: str | Path) -> dict[str, Any]:
    return read_state(Path(path))


def render_markdown_report(state: dict[str, Any], audience: str = "technical") -> str:
    if audience == "business":
        return render_business_report(state)
    if audience == "review":
        return render_review_report(state)
    return render_technical_report(state)


def render_technical_report(state: dict[str, Any]) -> str:
    lines = ["# Compass Investigation Report", ""]
    lines.append(f"- session_id: {state.get('session_id', 'unknown')}")
    flow = state.get("flow", {})
    lines.append(f"- current_step: {flow.get('current_step', 'unknown')}")

    conclusion = state.get("conclusion") or {}
    details = conclusion.get("details") or {}
    conclusion_history = state.get("conclusion_history") or []
    if conclusion:
        lines.extend(
            [
                "",
                "## 排查结论",
                "",
                f"**根因**：{mask_text(conclusion.get('summary', ''))}",
                "",
                "| 维度 | 内容 |",
                "|------|------|",
                f"| What | {mask_text(details.get('what', ''))} |",
                f"| Where | {mask_text(details.get('where', ''))} |",
                f"| When | {mask_text(details.get('when', ''))} |",
                f"| Why - 技术根因 | {mask_text(details.get('why_technical', ''))} |",
                f"| Why - 业务触发 | {mask_text(details.get('why_business', ''))} |",
                f"| Blast Radius | {mask_text(details.get('blast_radius', ''))} |",
                f"| How | {mask_text(details.get('how', ''))} |",
            ]
        )
    if conclusion_history:
        lines.extend(["", "## 结论版本历史", "", "| Revision | 状态 | 原结论 | 重开原因 |", "|----------|------|--------|----------|"])
        for item in conclusion_history:
            lines.append(
                f"| {item.get('revision', '')} | {mask_text(item.get('status', ''))} | {mask_text(item.get('summary', ''))} | {mask_text(item.get('reopen_reason', ''))} |"
            )

    lines.extend(["", "## Entities"])
    entities = state.get("entities") or {}
    if entities:
        for key, value in entities.items():
            lines.append(f"- {key}: {mask_value(key, value)}")
    else:
        lines.append("- 暂无")

    lines.extend(["", "## 场景事实"])
    scene_facts = state.get("scene_facts") or []
    if scene_facts:
        lines.extend(["| 类别 | 名称 | 值 | 来源 | 证据 |", "|------|------|----|------|------|"])
        for fact in scene_facts:
            evidence_refs = ", ".join(str(item) for item in fact.get("evidence", []))
            lines.append(
                f"| {mask_text(fact.get('category', ''))} | {mask_text(fact.get('name', ''))} | {mask_text(fact.get('value', ''))} | {mask_text(fact.get('source', ''))} | {mask_text(evidence_refs)} |"
            )
    else:
        lines.append("暂无。当前结论若依赖假设，建议先补入口、对象、上下游、配置或差异事实。")

    lines.extend(["", "## 证据链"])
    if conclusion:
        lines.append(f"**可信度**：{_confidence_label(str(conclusion.get('confidence', 'medium')))}")
        lines.append("")
        lines.extend(["| 证据ID | 来源 | 质量 | 证据摘要 | 支持/排除 |", "|--------|------|------|----------|-----------|"])
        evidence_refs = set(conclusion.get("evidence") or [])
        for item in state.get("evidence") or []:
            if evidence_refs and item.get("id") not in evidence_refs:
                continue
            lines.append(
                f"| {item.get('id', 'E?')} | {mask_text(item.get('source', 'unknown'))} | {_evidence_quality(item)} | {mask_text(item.get('summary', ''))} | {mask_text(item.get('supports', ''))} |"
            )
    else:
        lines.append("暂无结论，无法生成证据链。")

    lines.extend(["", "## Evidence"])
    evidence = state.get("evidence") or []
    if evidence:
        for item in evidence:
            raw_ref = f" raw_ref={mask_text(item.get('raw_ref', ''))}" if item.get("raw_ref") else ""
            lines.append(
                f"- [{item.get('id', 'E?')}] {mask_text(item.get('source', 'unknown'))} 质量={_evidence_quality(item)}: {mask_text(item.get('summary', ''))}{raw_ref}"
            )
    else:
        lines.append("- 暂无")

    lines.extend(["", "## Hypotheses"])
    hypotheses = state.get("hypotheses") or []
    if hypotheses:
        for item in hypotheses:
            source_facts = ", ".join(str(value) for value in item.get("source_facts", []))
            source_evidence = ", ".join(str(value) for value in item.get("source_evidence", []))
            suffix_parts = []
            if source_facts:
                suffix_parts.append(f"facts={source_facts}")
            if source_evidence:
                suffix_parts.append(f"evidence={source_evidence}")
            suffix = f" ({'; '.join(suffix_parts)})" if suffix_parts else ""
            lines.append(f"- [{item.get('id', 'H?')}] {item.get('status', '待验证')}: {item.get('statement', '')}{suffix}")
    else:
        lines.append("- 暂无")

    lines.extend(["", "## 证据图"])
    graph = state.get("evidence_graph") or {}
    nodes = graph.get("nodes") or []
    if nodes:
        lines.extend(["| 类型 | 节点 |", "|------|------|"])
        for node in nodes:
            lines.append(f"| {mask_text(node.get('type', ''))} | {mask_text(node.get('id', node.get('value', '')))} |")
    else:
        lines.append("暂无")

    lines.extend(["", "## Action Plan"])
    action_plan = state.get("action_plan") or []
    if action_plan:
        lines.extend(["| Action | 状态 | 轨道 | 来源 | 目标 | 成功标准 |", "|--------|------|------|------|------|----------|"])
        for action in action_plan:
            lines.append(
                f"| {mask_text(action.get('action_id', ''))} | {mask_text(action.get('status', ''))} | {mask_text(action.get('track', ''))} | {mask_text(action.get('source', ''))} | {mask_text(action.get('objective', ''))} | {mask_text(action.get('success_criteria', ''))} |"
            )
    else:
        lines.append("暂无")

    lines.extend(["", "## 完整排查流程"])
    action_history = state.get("action_history") or []
    if action_history:
        for idx, action in enumerate(action_history, start=1):
            lines.extend(_render_action_flow(idx, action))
    else:
        lines.append("暂无结构化 action 记录。")

    if conclusion:
        lines.extend(["", "## 推断链", "", mask_text(details.get("inference_chain", ""))])

    lines.extend(_render_strategy_review(state))

    lines.extend(["", "## 建议"])
    next_actions = conclusion.get("next_actions") or state.get("next_actions") or []
    if next_actions:
        for item in next_actions:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无自动建议，建议继续补充同类样本验证影响范围。")
    return "\n".join(lines) + "\n"


def render_business_report(state: dict[str, Any]) -> str:
    conclusion = state.get("conclusion") or {}
    details = conclusion.get("details") or {}
    lines = ["# Compass Investigation Report", "", "## 结论", ""]
    if conclusion:
        lines.extend(
            [
                f"**问题**：{mask_text(details.get('what', conclusion.get('summary', '')))}",
                "",
                "| | |",
                "|--|--|",
                f"| 发生时间 | {mask_text(details.get('when', ''))} |",
                f"| 影响范围 | {mask_text(details.get('blast_radius', ''))} |",
                f"| 原因 | {mask_text(details.get('why_business', ''))} |",
                "| 状态 | 已定位，等待按修复建议处理 |",
            ]
        )
    else:
        lines.append("当前还没有可输出的结论。")

    lines.extend(["", "## 证据摘要"])
    evidence = state.get("evidence") or []
    if evidence:
        for item in evidence:
            lines.append(f"- {mask_text(item.get('summary', ''))}")
    else:
        lines.append("- 暂无")

    lines.extend(["", "## 建议"])
    next_actions = conclusion.get("next_actions") or state.get("next_actions") or []
    if next_actions:
        for item in next_actions:
            lines.append(f"- {item}")
    else:
        lines.append("- 建议由对应研发确认修复排期，并用同类场景回归验证。")
    lines.extend(_render_strategy_review(state))
    return "\n".join(lines) + "\n"


def render_review_report(state: dict[str, Any]) -> str:
    conclusion = state.get("conclusion") or {}
    details = conclusion.get("details") or {}
    lines = ["# 排查结果", ""]

    if not conclusion:
        lines.extend(["## 一句话结论", "", "当前还没有可输出的排查结论。"])
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "## 一句话结论",
            "",
            mask_text(conclusion.get("summary", "")),
            "",
            "## 关键过程",
            "",
            "| 时间 | 角色/系统 | 位置 | 动作 | 结果 |",
            "|------|-----------|------|------|------|",
        ]
    )
    for item in _review_timeline_rows(state, details):
        lines.append(
            "| "
            + " | ".join(
                (
                    mask_text(item.get("time", "")),
                    _review_table_cell(item.get("actor", "")),
                    _review_table_cell(item.get("where", "")),
                    _review_table_cell(item.get("action", "")),
                    _review_table_cell(item.get("result", "")),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 链路说明",
            "",
            mask_text(details.get("how", "")),
            "",
            "## 原因分析",
            "",
            "| 类型 | 内容 |",
            "|------|------|",
            f"| 技术原因 | {_review_table_cell(details.get('why_technical', ''))} |",
            f"| 业务触发 | {_review_table_cell(details.get('why_business', ''))} |",
            f"| 涉及位置 | {_review_table_cell(details.get('where', ''))} |",
            "",
            "## 影响范围",
            "",
            mask_text(details.get("blast_radius", "")),
            "",
            "## 后续建议",
            "",
        ]
    )
    next_actions = conclusion.get("next_actions") or []
    if next_actions:
        for item in next_actions:
            lines.append(f"- {mask_text(item)}")
    else:
        lines.extend(_default_review_repair_suggestions())

    lines.extend(["", "## 证据参考"])
    evidence_refs = set(conclusion.get("evidence") or [])
    evidence = [item for item in state.get("evidence") or [] if not evidence_refs or item.get("id") in evidence_refs]
    if evidence:
        for item in evidence:
            raw_ref = f"（{mask_text(item.get('raw_ref', ''))}）" if item.get("raw_ref") else ""
            lines.append(f"- [{item.get('id', 'E?')}] {mask_text(item.get('source', 'unknown'))}：{mask_text(item.get('summary', ''))}{raw_ref}")
    else:
        lines.append("- 暂无")
    lines.extend(_render_strategy_review(state))
    return "\n".join(lines) + "\n"


def _render_strategy_review(state: dict[str, Any]) -> list[str]:
    review = state.get("strategy_review") or {}
    if not review:
        return []
    candidate = review.get("candidate") or {}
    lines = ["", "## 策略沉淀确认", ""]
    lines.append(f"**状态**：{_strategy_status_label(str(review.get('status', 'pending')))}")
    lines.append(f"**候选策略**：{mask_text(candidate.get('title', ''))}")
    if candidate.get("scenario"):
        lines.append(f"**适用场景**：{mask_text(candidate.get('scenario', ''))}")
    if candidate.get("summary"):
        lines.append(f"**本次结论**：{mask_text(candidate.get('summary', ''))}")
    evidence = ", ".join(str(item) for item in candidate.get("evidence", []))
    if evidence:
        lines.append(f"**来源证据**：{mask_text(evidence)}")
    if review.get("status") == "pending":
        lines.extend(
            [
                "",
                "请确认：是否将本次最终查询策略保留为同类问题的可复用策略？",
                "",
                "- 保留：`python3 -m compass_cli strategy keep --note \"<为什么值得保留>\"`",
                "- 不保留：`python3 -m compass_cli strategy discard --note \"<不保留原因>\"`",
            ]
        )
    elif review.get("note"):
        lines.append(f"**备注**：{mask_text(review.get('note', ''))}")
    return lines


def _strategy_status_label(status: str) -> str:
    return {"pending": "待确认", "kept": "已保留", "discarded": "不保留"}.get(status, status)


def _confidence_label(value: str) -> str:
    return {"high": "高", "medium": "中", "low": "低"}.get(value, value)


def _evidence_quality(item: dict[str, Any]) -> str:
    return f"{mask_text(item.get('kind', 'manual'))}/{mask_text(item.get('strength', 'medium'))}"


def _review_timeline_rows(state: dict[str, Any], details: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = [
        {
            "time": str(details.get("when", "")),
            "actor": _infer_actor(str(details.get("why_business", ""))) or "用户/业务",
            "where": str(details.get("where", "")),
            "action": str(details.get("what", "")),
            "result": str(details.get("why_business", "")),
        }
    ]
    for action in state.get("action_history") or []:
        output = action.get("output") or {}
        rows.append(
            {
                "time": _extract_time(str(output.get("summary", ""))) or "排查过程中",
                "actor": _actor_from_source(str(action.get("source", "")), str(action.get("track", ""))),
                "where": str(action.get("source", "")),
                "action": str(action.get("input", {}).get("query") or action.get("objective") or action.get("track") or "查询/阅读"),
                "result": str(output.get("summary", "")),
            }
        )
    return rows


def _review_table_cell(value: Any) -> str:
    return mask_text(value).replace("|", r"\|").replace("\n", "<br>")


def _actor_from_source(source: str, track: str) -> str:
    source_lower = source.lower()
    if "finance" in source_lower:
        return "finance-server"
    if "charge" in source_lower:
        return "charge-server"
    if "order" in source_lower:
        return "order-server"
    if "guan" in source_lower:
        return "guan-zhong"
    if track == "code":
        return "代码链路"
    if track == "sls" or "sls" in source_lower:
        return "线上日志"
    if track == "sql":
        return "数据表"
    return source or "系统"


def _infer_actor(text: str) -> str:
    if "用户" in text:
        return "用户"
    if "财务" in text or "finance" in text.lower():
        return "finance-server"
    if "充电" in text or "charge" in text.lower():
        return "charge-server"
    return ""


def _extract_time(text: str) -> str:
    import re

    matches = re.findall(r"(?:\d{4}-\d{2}-\d{2}\s+)?\d{1,2}:\d{2}(?::\d{2})?", text)
    return "；".join(matches[:3])


def _default_review_repair_suggestions() -> list[str]:
    return [
        "- 短期：在已定位入口补充保护，先降低同类场景再次出现的概率。",
        "- 中期：补充对应链路的回归用例，覆盖本次业务触发条件。",
        "- 长期：按资金/状态/入口类型梳理边界，让通用链路和特殊业务状态更清晰。",
    ]


def _render_action_flow(index: int, action: dict[str, Any]) -> list[str]:
    lines = [
        "",
        f"### 查询 #{index} · {mask_text(action.get('track', 'manual'))} · {mask_text(action.get('source', 'unknown'))}",
        "",
        "- 操作输入：",
    ]
    action_input = mask_mapping(action.get("input") or {})
    if action_input:
        for key, value in action_input.items():
            lines.append(f"  - {key}: {value}")
    else:
        lines.append("  - 暂无")

    lines.append("- 安全门控：")
    gate = mask_mapping(action.get("gate") or {})
    if gate:
        for key, value in gate.items():
            lines.append(f"  - {key}: {value}")
    else:
        lines.append("  - 未记录")

    output = action.get("output") or {}
    lines.extend(["- 操作输出：", f"  - summary: {mask_text(output.get('summary', ''))}"])
    if output.get("elapsed_ms") is not None:
        lines.append(f"  - elapsed_ms: {output.get('elapsed_ms')}")
    findings = output.get("findings") or []
    if findings:
        lines.append("  - findings:")
        for finding in findings:
            lines.append(f"    - {mask_text(finding)}")
    leads = output.get("leads") or {}
    if leads:
        lines.append("  - leads:")
        for key, values in leads.items():
            rendered_values = ", ".join(mask_text(value) for value in values)
            lines.append(f"    - {key}: {rendered_values}")
    if output.get("evidence_id"):
        lines.append(f"  - evidence_id: {output.get('evidence_id')}")
    return lines
