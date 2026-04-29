"""Timeline 模块：把 scene_facts / evidence / changes / action_history 中带
``event_at`` 的条目合并为按时间排序的"故障时间线"。

一条 timeline 条目的标准结构：

    {
        "ts": "2026-04-29 13:30",   # 显示用的原始时间字符串
        "ts_sort": 17xxxx,            # 排序键（解析失败的条目排到末尾）
        "kind": "change",            # change / scene_fact / evidence / action
        "ref_id": "C1",              # 关联的来源 id
        "title": "deploy order-server@v1.2.3",
        "detail": "把 v1.2.2 升到 v1.2.3，含 SQL 变更 ...",
        "tags": ["deploy", "order-server"],
    }

时间格式宽容：尝试 ISO 8601、``yyyy-MM-dd HH:mm[:ss]``、``yyyyMMddHHmmss``、纯日期。
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any


_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
)

_LOCAL_TZ = timezone(timedelta(hours=8))


def _parse_ts(value: Any) -> float | None:
    """解析时间字符串为 epoch 秒。

    时区策略：
        - 带时区的 ISO 8601 → 直接 timestamp
        - naive 时间 → 视为 UTC+8（与中文运维场景一致），统一基准便于排序
    """

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_LOCAL_TZ)
        return dt.timestamp()
    except ValueError:
        pass
    if re.fullmatch(r"\d{14}", text):
        try:
            dt = datetime.strptime(text, "%Y%m%d%H%M%S")
            return dt.replace(tzinfo=_LOCAL_TZ).timestamp()
        except ValueError:
            return None
    for fmt in _FORMATS:
        try:
            dt = datetime.strptime(text, fmt)
            return dt.replace(tzinfo=_LOCAL_TZ).timestamp()
        except ValueError:
            continue
    return None


def _entry(
    *,
    ts_raw: str,
    ts_sort: float | None,
    kind: str,
    ref_id: str,
    title: str,
    detail: str,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "ts": ts_raw,
        "ts_sort": ts_sort if ts_sort is not None else float("inf"),
        "ts_resolved": ts_sort is not None,
        "kind": kind,
        "ref_id": ref_id,
        "title": title,
        "detail": detail,
        "tags": list(tags or []),
    }


def build_timeline(state: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    for change in state.get("changes") or []:
        ts_raw = str(change.get("event_at", ""))
        entries.append(
            _entry(
                ts_raw=ts_raw,
                ts_sort=_parse_ts(ts_raw),
                kind="change",
                ref_id=str(change.get("id", "")),
                title=f"[{change.get('change_type', 'other')}] {change.get('target', '')}",
                detail=str(change.get("description", "")),
                tags=[
                    str(change.get("change_type", "")),
                    str(change.get("target", "")),
                ],
            )
        )

    for fact in state.get("scene_facts") or []:
        ts_raw = str(fact.get("event_at", "") or fact.get("created_at", ""))
        if not fact.get("event_at"):
            continue
        entries.append(
            _entry(
                ts_raw=str(fact.get("event_at", "")),
                ts_sort=_parse_ts(fact.get("event_at")),
                kind="scene_fact",
                ref_id=str(fact.get("name", "")),
                title=f"[{fact.get('category', '')}] {fact.get('name', '')}",
                detail=str(fact.get("value", "")),
                tags=[str(fact.get("category", ""))],
            )
        )

    for evidence in state.get("evidence") or []:
        if not evidence.get("event_at"):
            continue
        entries.append(
            _entry(
                ts_raw=str(evidence.get("event_at", "")),
                ts_sort=_parse_ts(evidence.get("event_at")),
                kind="evidence",
                ref_id=str(evidence.get("id", "")),
                title=f"[{evidence.get('kind', '')}] {evidence.get('source', '')}",
                detail=str(evidence.get("summary", "")),
                tags=[str(evidence.get("kind", "")), str(evidence.get("strength", ""))],
            )
        )

    for action in state.get("action_history") or []:
        ts_raw = str(action.get("completed_at", "") or action.get("recorded_at", ""))
        ts_sort = _parse_ts(ts_raw)
        if ts_sort is None:
            continue
        entries.append(
            _entry(
                ts_raw=ts_raw,
                ts_sort=ts_sort,
                kind="action",
                ref_id=str(action.get("action_id", "")),
                title=f"[action:{action.get('track', '')}] {action.get('source', '')}",
                detail=str(action.get("summary", "")),
                tags=[str(action.get("track", ""))],
            )
        )

    entries.sort(
        key=lambda e: (
            0 if e["ts_resolved"] else 1,
            e["ts_sort"],
            e["ref_id"],
        )
    )
    return entries


def format_timeline_text(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "（未登记任何带时间的事件）"
    lines: list[str] = []
    for entry in entries:
        ts = entry["ts"] or "(no-ts)"
        kind = entry["kind"]
        ref = entry["ref_id"] or "-"
        title = entry["title"]
        detail = entry["detail"]
        lines.append(f"{ts}  [{kind}/{ref}] {title} :: {detail}")
    return "\n".join(lines)
