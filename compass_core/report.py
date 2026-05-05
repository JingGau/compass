from __future__ import annotations

from pathlib import Path
from typing import Any

from compass_core.masking import mask_mapping, mask_text, mask_value
from compass_core.state import read_state
from compass_core.timeline import build_timeline


def load_state(path: str | Path) -> dict[str, Any]:
    return read_state(Path(path))


def render_markdown_report(state: dict[str, Any], audience: str = "technical") -> str:
    if audience == "business":
        return render_business_report(state)
    if audience == "review":
        return render_review_report(state)
    if audience == "postmortem":
        return render_postmortem_report(state)
    return render_technical_report(state)


def render_postmortem_report(state: dict[str, Any]) -> str:
    """事后复盘（postmortem）十段式结构，适合事故评审与组织级留档。"""

    conclusion = state.get("conclusion") or {}
    details = conclusion.get("details") or {}
    probl = state.get("problem") or {}
    timing = conclusion.get("timing") or {}

    lines: list[str] = [
        "# Postmortem · 事故复盘报告",
        "",
        f"- **session_id**：`{mask_text(state.get('session_id', 'unknown'))}`",
    ]
    if probl.get("standard"):
        lines.append(f"- **标准化问题**：{mask_text(str(probl.get('standard', '')))}")

    lines.extend(["", "## 一、Executive Summary（概述）", ""])
    if conclusion.get("tldr"):
        lines.append(f"> **TL;DR**：{mask_text(str(conclusion.get('tldr', '')))}")
        lines.append("")
    sev = str(conclusion.get("severity") or "").strip()
    if sev:
        sev_icon = {"sev1": "🔴", "sev2": "🟠", "sev3": "🟡", "sev4": "🟢"}.get(sev.lower(), "")
        lines.append(f"**严重等级**：{sev_icon} {mask_text(sev.upper())}")
        lines.append("")
    if conclusion.get("summary"):
        lines.append(f"**根因结论**：{mask_text(conclusion.get('summary', ''))}")
    else:
        lines.append("*尚未输出结构化 conclude，建议补全后再做复盘评审。*")

    lines.extend(["", "## 二、Impact（影响面）", "", mask_text(str(details.get("blast_radius") or "（未量化）")), ""])

    lines.extend(["## 三、Detection（发现与侦测）", ""])
    det_lines: list[str] = []
    if timing.get("detected_at"):
        det_lines.append(f"- **发现时间（timing.detected_at）**：{mask_text(str(timing['detected_at']))}")
    elif probl.get("detected_at"):
        det_lines.append(f"- **发现时间（problem.detected_at）**：{mask_text(str(probl.get('detected_at')))}")
    det_lines.append(f"- **When / What**：{mask_text(str(details.get('when', '')))} · {mask_text(str(details.get('what', '')))}")
    lines.extend(det_lines)
    lines.extend(_render_applicable_knowledge_section(state))

    lines.extend(["## 四、Response（响应与接手）", ""])
    ack_at = timing.get("acknowledged_at")
    lines.append(f"- **开始响应时间**：{mask_text(str(ack_at)) if ack_at else '（未记录）'}")
    if timing.get("mttd_minutes") is not None:
        lines.append(f"- **MTTD（发现→响应）**：约 {mask_text(str(timing['mttd_minutes']))} 分钟")
    mitig = conclusion.get("mitigation") or []
    if mitig:
        lines.extend(["", "### 止血动作（Mitigation）", ""])
        lines.extend(_render_action_items_table(mitig))
    else:
        lines.extend(["", "*未记录 mitigation*", ""])

    lines.extend(["## 五、Recovery（恢复与根治）", ""])
    mit_at = timing.get("mitigated_at")
    res_at = timing.get("resolved_at")
    lines.append(f"- **止血见效时间**：{mask_text(str(mit_at)) if mit_at else '（未记录）'}")
    lines.append(f"- **完全恢复时间**：{mask_text(str(res_at)) if res_at else '（未记录）'}")
    if timing.get("mttm_minutes") is not None:
        lines.append(f"- **MTTM（响应→止血）**：约 {mask_text(str(timing['mttm_minutes']))} 分钟")
    if timing.get("mttr_minutes") is not None:
        lines.append(f"- **MTTR（发现→解决）**：约 {mask_text(str(timing['mttr_minutes']))} 分钟")
    rem = conclusion.get("remediation") or []
    if rem:
        lines.extend(["", "### 根治动作（Remediation）", ""])
        lines.extend(_render_action_items_table(rem))
    lines.append("")

    lines.extend(["## 六、Root Cause（根因）", ""])
    lines.extend(
        [
            "| 维度 | 内容 |",
            "|------|------|",
            f"| Why — 技术 | {mask_text(str(details.get('why_technical', '')))} |",
            f"| Why — 业务触发 | {mask_text(str(details.get('why_business', '')))} |",
            f"| Where | {mask_text(str(details.get('where', '')))} |",
            f"| How（传播链） | {mask_text(str(details.get('how', '')))} |",
            "",
        ]
    )
    lines.extend(_render_inference_chain(conclusion, details))

    lines.extend(["## 七、Action Items（行动项汇总）", ""])
    lines.extend(_render_mitigation_remediation(conclusion))
    lines.extend(_render_unsolved_pattern(conclusion))

    lines.extend(["## 八、Lessons Learned（经验与反思）", ""])
    lines.append("- 结合根因与行动项补充本次复盘教训。")
    lines.extend(_render_quality_warnings(conclusion))

    lines.extend(["## 九、References（引用与证据）", ""])
    ev_ref = conclusion.get("evidence") or []
    if ev_ref:
        lines.append("结论引用：`" + "`, `".join(mask_text(str(x)) for x in ev_ref) + "`")
        lines.append("")
    evidence_rows = state.get("evidence") or []
    if evidence_rows:
        lines.extend(["| ID | 来源 | 摘要 | kind/strength |", "|----|------|------|---------------|"])
        for item in evidence_rows:
            lines.append(
                f"| {mask_text(str(item.get('id', '')))} | {mask_text(str(item.get('source', '')))} | "
                f"{mask_text(str(item.get('summary', '')))} | {_evidence_quality(item)} |"
            )
        lines.append("")

    tl = _render_timeline_section(state, heading="## 十、Timeline（时间线）")
    if tl:
        lines.extend(tl)
    else:
        lines.extend(["", "## 十、Timeline（时间线）", "", "*暂无带 event_at 的事件；建议为 change / evidence 补 event_at*", ""])

    lines.extend(_render_changes_section(state))
    lines.extend(_render_strategy_review(state))
    return "\n".join(lines) + "\n"


def render_technical_report(state: dict[str, Any]) -> str:
    lines = ["# Compass Investigation Report", ""]
    lines.append(f"- session_id: {state.get('session_id', 'unknown')}")
    flow = state.get("flow", {})
    lines.append(f"- current_step: {flow.get('current_step', 'unknown')}")

    conclusion = state.get("conclusion") or {}
    details = conclusion.get("details") or {}
    conclusion_history = state.get("conclusion_history") or []
    if conclusion:
        lines.extend(_render_tldr_card(conclusion))
        lines.extend(_render_timing_section(conclusion))
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

    lines.extend(_render_timeline_section(state))

    lines.extend(_render_changes_section(state))

    lines.extend(_render_applicable_knowledge_section(state))

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
        lines.extend(_render_inference_chain(conclusion, details))
        lines.extend(_render_quality_warnings(conclusion))
        lines.extend(_render_mitigation_remediation(conclusion))
        lines.extend(_render_unsolved_pattern(conclusion))

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
    lines = ["# Compass Investigation Report", ""]
    if conclusion:
        lines.extend(_render_tldr_card(conclusion))
        lines.extend(_render_timing_section(conclusion))
    lines.extend(["", "## 结论", ""])
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

    lines.extend(_render_mitigation_remediation(conclusion))

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

    lines.extend(_render_tldr_card(conclusion))
    lines.extend(_render_timing_section(conclusion))
    lines.extend(
        [
            "",
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

    lines.extend(_render_changes_section(state))

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
        ]
    )

    lines.extend(_render_mitigation_remediation(conclusion))
    lines.extend(_render_unsolved_pattern(conclusion))
    lines.extend(_render_quality_warnings(conclusion))

    lines.extend(["", "## 后续建议", ""])
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
    raw_input = action.get("input") or {}
    raw_gate = action.get("gate") or {}
    explain_text_raw = (
        str(raw_input.get("explain_text") or raw_gate.get("explain_text") or "").strip()
    )

    action_input = mask_mapping({k: v for k, v in raw_input.items() if k != "explain_text"})
    if action_input:
        for key, value in action_input.items():
            lines.append(f"  - {key}: {value}")
    else:
        lines.append("  - 暂无")

    lines.append("- 安全门控：")
    gate = mask_mapping({k: v for k, v in raw_gate.items() if k != "explain_text"})
    if gate:
        for key, value in gate.items():
            lines.append(f"  - {key}: {value}")
    else:
        lines.append("  - 未记录")

    if explain_text_raw:
        lines.extend(
            [
                "- EXPLAIN 原文（可直接复制回贴）：",
                "",
                "```text",
                mask_text(explain_text_raw),
                "```",
            ]
        )

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


def _render_timeline_section(state: dict[str, Any], *, heading: str = "## 故障时间线") -> list[str]:
    """渲染故障时间线（仅当有带 event_at 的事件时显示）。

    Args:
        state: session state
        heading: Markdown 二级标题文案（postmortem 等场景可改用「十、Timeline」等）
    """

    entries = build_timeline(state)
    if not entries:
        return []
    lines = [
        "",
        heading,
        "",
        "| 时间 | 类型 | 引用 | 关联变更 | 标题 | 详情 |",
        "|------|------|------|----------|------|------|",
    ]
    for entry in entries:
        ts = mask_text(str(entry.get("ts", "")))
        kind = mask_text(str(entry.get("kind", "")))
        ref = mask_text(str(entry.get("ref_id", "")))
        title = mask_text(str(entry.get("title", "")))
        detail = mask_text(str(entry.get("detail", "")))
        related = entry.get("related_changes") or []
        related_text = mask_text("⤴ " + ", ".join(related)) if related else "—"
        lines.append(f"| {ts} | {kind} | {ref} | {related_text} | {title} | {detail} |")
    return lines


def _render_changes_section(state: dict[str, Any]) -> list[str]:
    """渲染变更窗口（仅当登记了变更时显示）。"""

    changes = state.get("changes") or []
    if not changes:
        return []
    lines = ["", "## 变更窗口", "", "| ID | 类型 | 时间 | 对象 | 描述 | Before → After | 来源 |", "|----|------|------|------|------|----------------|------|"]
    for change in changes:
        before = str(change.get("before", "")).strip()
        after = str(change.get("after", "")).strip()
        delta = "—"
        if before or after:
            before_text = mask_text(before) or "—"
            after_text = mask_text(after) or "—"
            delta = f"{before_text} → {after_text}"
        lines.append(
            "| {cid} | {ctype} | {when} | {target} | {desc} | {delta} | {source} |".format(
                cid=mask_text(str(change.get("id", ""))),
                ctype=mask_text(str(change.get("change_type", ""))),
                when=mask_text(str(change.get("event_at", ""))),
                target=mask_text(str(change.get("target", ""))),
                desc=mask_text(str(change.get("description", ""))),
                delta=delta,
                source=mask_text(str(change.get("source", ""))),
            )
        )
    return lines


def _render_applicable_knowledge_section(state: dict[str, Any]) -> list[str]:
    """渲染本次召回到的通用知识。"""

    items = state.get("applicable_knowledge") or []
    if not items:
        return []
    lines = ["", "## 适用知识（自动召回）", ""]
    for item in items:
        tags = ",".join(item.get("tags") or [])
        kid = mask_text(str(item.get("id", "")))
        statement = mask_text(str(item.get("statement", "")))
        tags_text = mask_text(tags)
        lines.append(f"- **[{kid}][{tags_text}]** {statement}")
    return lines


def _render_quality_warnings(conclusion: dict[str, Any]) -> list[str]:
    """渲染结论质量警告（仅 conclusion 存在 quality_warnings 时显示）。"""

    warnings = conclusion.get("quality_warnings") or []
    if not warnings:
        return []
    lines = ["", "## 结论质量提示", "", "| 等级 | 代号 | 提示 |", "|------|------|------|"]
    for w in warnings:
        level = mask_text(str(w.get("level", "warn")).upper())
        code = mask_text(str(w.get("code", "")))
        msg = mask_text(str(w.get("message", "")))
        lines.append(f"| {level} | {code} | {msg} |")
    return lines


def _render_mitigation_remediation(conclusion: dict[str, Any]) -> list[str]:
    """渲染止血与根治：以表格形式输出 description/owner/due/status/url。"""

    mitigation = conclusion.get("mitigation") or []
    remediation = conclusion.get("remediation") or []
    if not mitigation and not remediation:
        return []
    lines = ["", "## 止血与根治"]
    if mitigation:
        lines.extend(["", "### 止血动作（短期降低影响）"])
        lines.extend(_render_action_items_table(mitigation))
    if remediation:
        lines.extend(["", "### 根治动作（长期解决根因）"])
        lines.extend(_render_action_items_table(remediation))
    return lines


def _render_action_items_table(items: list[Any]) -> list[str]:
    """把 mitigation/remediation 列表（dict 或字符串）渲染为统一表格。"""

    if not items:
        return []
    lines = ["", "| # | 动作 | Owner | Due | 状态 | 链接 |", "|---|------|-------|-----|------|------|"]
    for idx, raw in enumerate(items, start=1):
        if isinstance(raw, dict):
            desc = raw.get("description", "") or ""
            owner = raw.get("owner", "") or "—"
            due = raw.get("due", "") or "—"
            status = raw.get("status", "") or "open"
            url = raw.get("url", "") or "—"
        else:
            desc = str(raw)
            owner = "—"
            due = "—"
            status = "open"
            url = "—"
        lines.append(
            f"| {idx} | {mask_text(desc)} | {mask_text(str(owner))} | {mask_text(str(due))} | "
            f"{mask_text(str(status))} | {mask_text(str(url))} |"
        )
    return lines


def _render_tldr_card(conclusion: dict[str, Any]) -> list[str]:
    """渲染 TL;DR + 严重等级头条卡片。"""

    tldr = (conclusion.get("tldr") or "").strip()
    severity = (conclusion.get("severity") or "").strip()
    if not tldr and not severity:
        return []
    sev_icon = {"sev1": "🔴", "sev2": "🟠", "sev3": "🟡", "sev4": "🟢"}.get(severity, "⚪")
    sev_label = severity.upper() if severity else "—"
    lines: list[str] = ["", "## TL;DR"]
    if tldr:
        lines.extend(["", f"> {mask_text(tldr)}"])
    lines.extend(
        [
            "",
            "| 字段 | 内容 |",
            "|------|------|",
            f"| 严重等级 | {sev_icon} {mask_text(sev_label)} |",
        ]
    )
    return lines


def _render_timing_section(conclusion: dict[str, Any]) -> list[str]:
    """渲染 MTTD / MTTM / MTTR 时序指标卡。"""

    timing = conclusion.get("timing") or {}
    if not timing:
        return []

    def _fmt(minutes: Any) -> str:
        if minutes is None:
            return "—"
        try:
            value = float(minutes)
        except (TypeError, ValueError):
            return mask_text(str(minutes))
        if value < 1:
            return f"{value * 60:.0f}s"
        if value < 60:
            return f"{value:.1f}m"
        return f"{value / 60:.2f}h ({value:.0f}m)"

    rows = [
        ("MTTD（发现 → 响应）", "mttd_minutes", "detected_at", "acknowledged_at"),
        ("MTTM（响应 → 止血）", "mttm_minutes", "acknowledged_at", "mitigated_at"),
        ("MTTR（发现 → 解决）", "mttr_minutes", "detected_at", "resolved_at"),
    ]
    body = []
    has_any = False
    for label, key, start_k, end_k in rows:
        m = timing.get(key)
        if m is None and not (timing.get(start_k) and timing.get(end_k)):
            body.append(f"| {label} | — | {mask_text(str(timing.get(start_k, '') or '—'))} | {mask_text(str(timing.get(end_k, '') or '—'))} |")
            continue
        has_any = True
        body.append(
            f"| {label} | {mask_text(_fmt(m))} | {mask_text(str(timing.get(start_k, '') or '—'))} | "
            f"{mask_text(str(timing.get(end_k, '') or '—'))} |"
        )
    if not has_any and not any(timing.get(k) for _, _, k, _ in rows):
        return []
    lines = [
        "",
        "## 时序指标（MTTD / MTTM / MTTR）",
        "",
        "| 指标 | 时长 | 起点 | 终点 |",
        "|------|------|------|------|",
    ]
    lines.extend(body)
    return lines


def _render_inference_chain(conclusion: dict[str, Any], details: dict[str, Any]) -> list[str]:
    """把推断链拆段为有序步骤表。"""

    steps = conclusion.get("inference_steps") or []
    raw_chain = (details or {}).get("inference_chain", "") or ""
    if not steps and not raw_chain.strip():
        return []
    lines = ["", "## 推断链"]
    if steps:
        lines.extend(
            [
                "",
                "| # | 推断步骤 | 引用 |",
                "|---|----------|------|",
            ]
        )
        for i, step in enumerate(steps, start=1):
            if isinstance(step, dict):
                idx = step.get("index") or i
                text = step.get("text", "")
                refs = ", ".join(step.get("evidence_refs") or [])
            else:
                idx = i
                text = str(step)
                refs = ""
            lines.append(f"| {idx} | {mask_text(str(text))} | {mask_text(refs) or '—'} |")
    elif raw_chain.strip():
        lines.extend(["", mask_text(raw_chain.strip())])
    return lines


def _render_unsolved_pattern(conclusion: dict[str, Any]) -> list[str]:
    """渲染未解之谜与同类扫描方向。"""

    unsolved = conclusion.get("unsolved") or []
    pattern_scan = conclusion.get("pattern_scan") or []
    if not unsolved and not pattern_scan:
        return []
    lines: list[str] = []
    if unsolved:
        lines.extend(["", "## 未解之谜（保留为开放问题）"])
        for item in unsolved:
            lines.append(f"- {mask_text(str(item))}")
    if pattern_scan:
        lines.extend(["", "## 同类扫描方向"])
        for item in pattern_scan:
            lines.append(f"- {mask_text(str(item))}")
    return lines
