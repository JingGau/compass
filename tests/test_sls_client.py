from pathlib import Path

from adapters.sls.client import SLSClient


def test_query_logs_requires_confirmation_for_non_default_logstore(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SLS[0].NAME", "PROD")
    monkeypatch.setenv("SLS[0].ENV", "prod")
    monkeypatch.setenv("SLS[0].ENDPOINT", "cn-hangzhou.log.aliyuncs.com")
    monkeypatch.setenv("SLS[0].ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("SLS[0].ACCESS_KEY_SECRET", "sk")
    monkeypatch.setenv("SLS[0].PROJECT", "project-prod")
    monkeypatch.setenv("SLS[0].LOGSTORE", "all")
    config = tmp_path / "config.yaml"
    config.write_text(
        """
enabled: true
profiles_from_env: "SLS"
default_env: "prod"
""".strip(),
        encoding="utf-8",
    )

    client = SLSClient(config_path=str(config))
    result = client.query_logs(
        query="order_no_123",
        from_time="-1h",
        logstore="app-logstore",
    )

    assert result["success"] is False
    assert result["error"] == "SLS 非默认 logstore 查询需要用户确认"
    assert result["requires_confirmation"] is True
    assert result["confirmation"]["default_logstore"] == "all"
    assert result["confirmation"]["requested_logstore"] == "app-logstore"


def test_agent_auto_rejects_direct_sls_query_without_runtime_action(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("COMPASS_AGENT_AUTO", "1")
    monkeypatch.delenv("COMPASS_RUNTIME_ACTION_ID", raising=False)
    monkeypatch.delenv("COMPASS_RUNTIME_STATE_FILE", raising=False)
    monkeypatch.setenv("SLS[0].NAME", "PROD")
    monkeypatch.setenv("SLS[0].ENV", "prod")
    monkeypatch.setenv("SLS[0].ENDPOINT", "cn-hangzhou.log.aliyuncs.com")
    monkeypatch.setenv("SLS[0].ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("SLS[0].ACCESS_KEY_SECRET", "sk")
    monkeypatch.setenv("SLS[0].PROJECT", "project-prod")
    monkeypatch.setenv("SLS[0].LOGSTORE", "all")
    config = tmp_path / "config.yaml"
    config.write_text(
        """
enabled: true
profiles_from_env: "SLS"
default_env: "prod"
""".strip(),
        encoding="utf-8",
    )

    client = SLSClient(config_path=str(config))
    result = client.query_logs(query="order_no_123", from_time="-1h")

    assert result["success"] is False
    assert result["requires_runtime_action"] is True
    assert "禁止 agent 自动模式裸调 adapter" in result["error"]
