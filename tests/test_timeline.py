"""Timeline 模块单元测试。"""

from __future__ import annotations

from compass_core.timeline import build_timeline


def test_build_timeline_orders_chronologically_and_handles_unparseable() -> None:
    state = {
        "changes": [
            {
                "id": "C1",
                "change_type": "deploy",
                "target": "order-server@v1.2.3",
                "description": "上线",
                "event_at": "2026-04-29 13:30",
            },
            {
                "id": "C2",
                "change_type": "config",
                "target": "rate-limit",
                "description": "下调",
                "event_at": "2026-04-29 12:00:00",
            },
        ],
        "scene_facts": [
            {
                "category": "entrypoint",
                "name": "user_complaint",
                "value": "首次报障",
                "event_at": "2026-04-29 14:00",
            },
            {
                "category": "object",
                "name": "no-time",
                "value": "v",
            },
        ],
        "evidence": [
            {
                "id": "E1",
                "kind": "log",
                "source": "sls",
                "summary": "日志 1",
                "event_at": "20260429133500",
                "strength": "strong",
            },
            {
                "id": "E2",
                "kind": "log",
                "source": "sls",
                "summary": "无时间",
            },
        ],
        "action_history": [
            {
                "action_id": "A1",
                "track": "log",
                "source": "sls",
                "summary": "首次查询",
                "completed_at": "2026-04-29T13:35:30+08:00",
            }
        ],
    }
    entries = build_timeline(state)
    refs = [e["ref_id"] for e in entries]
    assert refs == ["C2", "C1", "E1", "A1", "user_complaint"]
    assert all(e["ts_resolved"] for e in entries)


def test_build_timeline_skips_facts_without_event_at_and_unparseable_action_times() -> None:
    state = {
        "scene_facts": [{"name": "x", "value": "y", "category": "object"}],
        "action_history": [
            {"action_id": "A1", "track": "log", "source": "sls", "summary": "x"},
        ],
    }
    assert build_timeline(state) == []
