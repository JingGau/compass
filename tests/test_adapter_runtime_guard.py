import json

from adapters.base import agent_auto_runtime_guard


def test_agent_auto_runtime_guard_allows_matching_planned_action(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "session.json"
    state_file.write_text(
        json.dumps(
            {
                "flow": {"confirmed": True},
                "action_plan": [
                    {
                        "action_id": "A1",
                        "track": "sls",
                        "status": "planned",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("COMPASS_AGENT_AUTO", "1")
    monkeypatch.setenv("COMPASS_RUNTIME_STATE_FILE", str(state_file))
    monkeypatch.setenv("COMPASS_RUNTIME_ACTION_ID", "A1")

    assert agent_auto_runtime_guard("sls", "query_logs", expected_track="sls") is None


def test_agent_auto_runtime_guard_rejects_wrong_track(tmp_path, monkeypatch) -> None:
    state_file = tmp_path / "session.json"
    state_file.write_text(
        json.dumps(
            {
                "flow": {"confirmed": True},
                "action_plan": [
                    {
                        "action_id": "A1",
                        "track": "code",
                        "status": "planned",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("COMPASS_AGENT_AUTO", "1")
    monkeypatch.setenv("COMPASS_RUNTIME_STATE_FILE", str(state_file))
    monkeypatch.setenv("COMPASS_RUNTIME_ACTION_ID", "A1")

    blocked = agent_auto_runtime_guard("sls", "query_logs", expected_track="sls")

    assert blocked is not None
    assert blocked["requires_runtime_action"] is True
    assert "track 不是 sls" in blocked["error"]


def test_adapter_mode_agent_auto_enforces_runtime_context(monkeypatch) -> None:
    monkeypatch.setenv("COMPASS_ADAPTER_MODE", "agent_auto")
    monkeypatch.delenv("COMPASS_AGENT_AUTO", raising=False)
    monkeypatch.delenv("COMPASS_RUNTIME_STATE_FILE", raising=False)
    monkeypatch.delenv("COMPASS_RUNTIME_ACTION_ID", raising=False)

    blocked = agent_auto_runtime_guard("sls", "query_logs", expected_track="sls")

    assert blocked is not None
    assert blocked["requires_runtime_action"] is True
    assert blocked["adapter_mode"] == "runtime"
    assert "缺少 COMPASS_RUNTIME_STATE_FILE" in blocked["error"]


def test_adapter_mode_manual_keeps_human_direct_calls_unblocked(monkeypatch) -> None:
    monkeypatch.setenv("COMPASS_ADAPTER_MODE", "manual")
    monkeypatch.delenv("COMPASS_AGENT_AUTO", raising=False)

    assert agent_auto_runtime_guard("sls", "query_logs", expected_track="sls") is None


def test_legacy_agent_auto_wins_over_manual_mode(monkeypatch) -> None:
    monkeypatch.setenv("COMPASS_ADAPTER_MODE", "manual")
    monkeypatch.setenv("COMPASS_AGENT_AUTO", "1")
    monkeypatch.delenv("COMPASS_RUNTIME_STATE_FILE", raising=False)
    monkeypatch.delenv("COMPASS_RUNTIME_ACTION_ID", raising=False)

    blocked = agent_auto_runtime_guard("platform", "query_sql", expected_track="sql")

    assert blocked is not None
    assert blocked["adapter_mode"] == "runtime"


def test_invalid_adapter_mode_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("COMPASS_ADAPTER_MODE", "maybe")
    monkeypatch.delenv("COMPASS_AGENT_AUTO", raising=False)

    blocked = agent_auto_runtime_guard("sls", "query_logs", expected_track="sls")

    assert blocked is not None
    assert blocked["adapter_mode"] == "invalid"
    assert "COMPASS_ADAPTER_MODE 无效" in blocked["error"]
