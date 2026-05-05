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
