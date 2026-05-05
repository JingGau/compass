from adapters.platform.client import PlatformClient


def test_agent_auto_rejects_direct_platform_query_without_runtime_action(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("COMPASS_AGENT_AUTO", "1")
    monkeypatch.delenv("COMPASS_RUNTIME_ACTION_ID", raising=False)
    monkeypatch.delenv("COMPASS_RUNTIME_STATE_FILE", raising=False)
    monkeypatch.setenv("PLATFORM[0].NAME", "PROD")
    monkeypatch.setenv("PLATFORM[0].ENV", "prod")
    monkeypatch.setenv("PLATFORM[0].BASE_URL", "http://example.invalid")
    monkeypatch.setenv("PLATFORM[0].USERNAME", "u")
    monkeypatch.setenv("PLATFORM[0].PASSWORD", "p")
    config = tmp_path / "config.yaml"
    config.write_text(
        """
enabled: true
profiles_from_env: "PLATFORM"
default_profile: "PROD"
""".strip(),
        encoding="utf-8",
    )

    client = PlatformClient(config_path=str(config))
    result = client.query_sql("select * from t_order where order_no='123'")

    assert result["success"] is False
    assert result["requires_runtime_action"] is True
    assert "禁止 agent 自动模式裸调 adapter" in result["error"]
