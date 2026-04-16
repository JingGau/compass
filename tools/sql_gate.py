from __future__ import annotations

from dataclasses import dataclass
import re

from tools.action_cards import SafetyGateResult


@dataclass
class DorisExplainSummary:
    cardinality: int | None = None
    partitions: str | None = None
    tablets: str | None = None
    has_olap_scan: bool = False
    predicates: str | None = None


def parse_doris_explain(explain_text: str) -> DorisExplainSummary:
    cardinality = _int_match(r"cardinality=(\d+)", explain_text)
    partitions = _str_match(r"partitions=([^\s]+)", explain_text)
    tablets = _str_match(r"tablets=([^\s,]+)", explain_text)
    predicates = _str_match(r"PREDICATES:\s*(.+)", explain_text)
    return DorisExplainSummary(
        cardinality=cardinality,
        partitions=partitions,
        tablets=tablets,
        has_olap_scan="VOlapScanNode" in explain_text,
        predicates=predicates,
    )


def assess_sql_explain(sql: str, explain_text: str, environment: str) -> SafetyGateResult:
    if environment != "prod":
        return SafetyGateResult(
            gate_type="sql",
            status="passed",
            risk_level="low",
            summary=f"{environment} 环境跳过 EXPLAIN 风险强卡",
            details={"sql": sql},
            requires_confirmation=False,
        )

    summary = parse_doris_explain(explain_text)
    rows = summary.cardinality
    details = {
        "rows": rows if rows is not None else "未知",
        "partitions": summary.partitions or "未知",
        "tablets": summary.tablets or "未知",
        "scan": "VOlapScanNode" if summary.has_olap_scan else "未知",
    }
    if summary.predicates:
        details["predicates"] = summary.predicates

    if rows is None:
        return SafetyGateResult(
            gate_type="sql",
            status="blocked",
            risk_level="high",
            summary="EXPLAIN 未解析到 rows/cardinality，按失败关闭处理",
            details=details,
            requires_confirmation=True,
        )
    if rows > 1_000_000:
        return SafetyGateResult(
            gate_type="sql",
            status="blocked",
            risk_level="high",
            summary=f"预估扫描约 {rows} 行，超过 100 万行高风险阈值",
            details=details,
            requires_confirmation=True,
        )
    if rows >= 100_000:
        return SafetyGateResult(
            gate_type="sql",
            status="warning",
            risk_level="medium",
            summary=f"预估扫描约 {rows} 行，需用户确认后执行",
            details=details,
            requires_confirmation=True,
        )
    return SafetyGateResult(
        gate_type="sql",
        status="passed",
        risk_level="low",
        summary=f"预估扫描约 {rows} 行，低风险自动继续",
        details=details,
        requires_confirmation=False,
    )


def _int_match(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text)
    if not match:
        return None
    return int(match.group(1))


def _str_match(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    if not match:
        return None
    return match.group(1).strip()

