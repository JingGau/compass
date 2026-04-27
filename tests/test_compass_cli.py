from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "compass_cli", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_intake_outputs_structured_json() -> None:
    result = run_cli("intake", "用户支付成功但订单没有推进，订单号 123456，今天上午", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["scene"] == "payment"
    assert payload["standard_problem"]
    assert payload["entities"]["order_no"] == "123456"
    assert "hypotheses" in payload


def test_kb_search_reads_markdown_roots(tmp_path: Path) -> None:
    vault = tmp_path / "obsidian-vault"
    vault.mkdir()
    note = vault / "清分.md"
    note.write_text("清分单应由订单完成触发，入金通知只是允许推送银行的信号。", encoding="utf-8")

    result = run_cli("kb", "search", "入金通知", "--root", str(vault), "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["query"] == "入金通知"
    assert payload["matches"][0]["path"].endswith("清分.md")
    assert "允许推送银行" in payload["matches"][0]["snippet"]


def test_state_show_uses_custom_state_file(tmp_path: Path) -> None:
    state_file = tmp_path / "state.yaml"

    result = run_cli("state", "show", "--state-file", str(state_file), "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["state"]["flow"]["current_step"] == 1
    assert state_file.exists()


def test_report_renders_markdown_from_state(tmp_path: Path) -> None:
    state_file = tmp_path / "state.yaml"
    state_file.write_text(
        """
session_id: sess_test
flow:
  current_step: 2
entities:
  order_no: "123456"
evidence:
  - id: E1
    source: kb
    summary: 清分单由订单完成触发
hypotheses:
  - id: H1
    statement: 入金通知不是生成清分单的触发器
    status: 支持
""".strip(),
        encoding="utf-8",
    )

    result = run_cli("report", "--state-file", str(state_file), "--format", "markdown")

    assert result.returncode == 0, result.stderr
    assert "# Compass Investigation Report" in result.stdout
    assert "order_no" in result.stdout
    assert "清分单由订单完成触发" in result.stdout


def test_start_creates_controlled_session_and_requires_confirmation(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"

    result = run_cli(
        "start",
        "用户礼品卡不展示，手机号 15921195068，今天下午",
        "--state-file",
        str(state_file),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["state"]["flow"]["phase"] == "awaiting_confirmation"
    assert payload["state"]["problem"]["scene"] == "payment"
    assert payload["state"]["environment"] == "prod"
    assert payload["state"]["problem"]["environment"] == "prod"
    assert payload["state"]["mode"] == "investigation_only"
    assert payload["state"]["write_policy"] == "no_code_or_data_mutation"
    assert payload["state"]["entities"]["phone"] == "15921195068"
    assert payload["state"]["flow"]["confirmed"] is False

    blocked = run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡",
        "--finding",
        "payWaysPanels contains gift card",
        "--supports",
        "H1",
        "--json",
    )

    assert blocked.returncode == 1
    error = json.loads(blocked.stdout)
    assert error["ok"] is False
    assert "确认" in error["error"]


def test_start_uses_explicit_non_prod_environment_only_when_user_says_so(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"

    result = run_cli(
        "start",
        "uat环境 用户礼品卡不展示，手机号 15921195068，今天下午",
        "--state-file",
        str(state_file),
        "--json",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["state"]["environment"] == "uat"
    assert payload["state"]["problem"]["environment"] == "uat"


def test_sql_action_plan_defaults_to_session_environment_prod(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SQL1",
        "--track",
        "sql",
        "--source",
        "Doris",
        "--objective",
        "确认支付方式明细",
        "--success-criteria",
        "查询到该用户支付方式记录",
        "--input",
        "sql=select * from t_pay where phone='15921195068'",
        "--gate",
        "type=sql",
        "--gate",
        "explain=passed",
        "--gate",
        "risk=low",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["action"]["input"]["env"] == "prod"


def test_confirm_then_record_action_creates_evidence_and_leads(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))

    confirmed = run_cli("confirm", "--state-file", str(state_file), "--mode", "auto", "--json")

    assert confirmed.returncode == 0, confirmed.stderr
    assert json.loads(confirmed.stdout)["state"]["flow"]["phase"] == "action_ready"

    recorded = run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        "--finding",
        "finance returned subPayWay=3 amount=2319.01",
        "--finding",
        "payment-ways-v2 response removed gift card",
        "--lead",
        "trace_ids=trace-1",
        "--lead",
        "interfaces=/app/gun/payment-ways-v2",
        "--supports",
        "H2",
        "--json",
    )

    assert recorded.returncode == 0, recorded.stderr
    payload = json.loads(recorded.stdout)
    assert payload["ok"] is True
    assert payload["evidence"]["id"] == "E1"
    assert payload["state"]["flow"]["phase"] == "evidence_collecting"
    assert payload["state"]["evidence_graph"]["nodes"]


def test_conclude_requires_valid_evidence_refs_and_structured_fields(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "用户问题",
    )

    no_evidence = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "guan-zhong 过滤礼品卡",
        "--evidence",
        "E1",
        "--json",
    )

    assert no_evidence.returncode == 1
    assert "不存在" in json.loads(no_evidence.stdout)["error"]

    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        "--finding",
        "finance returned gift card",
        "--supports",
        "H2",
    )

    incomplete = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "礼品卡在 guan-zhong payment-ways-v2 链路被过滤",
        "--evidence",
        "E1",
        "--confidence",
        "high",
        "--json",
    )

    assert incomplete.returncode == 1
    assert "缺少结论字段" in json.loads(incomplete.stdout)["error"]

    concluded = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "礼品卡在 guan-zhong payment-ways-v2 链路被过滤",
        "--evidence",
        "E1",
        "--confidence",
        "high",
        "--what",
        "用户切换支付方式后礼品卡不展示",
        "--where",
        "guan-zhong /app/gun/payment-ways-v2",
        "--when",
        "2026-04-25 16:51 前后",
        "--why-technical",
        "payment-ways-v2 链路未填充 tradeModes，互联站过滤逻辑误过滤礼品卡",
        "--why-business",
        "用户在国网互联站 App 端切换支付方式",
        "--blast-radius",
        "已知影响该用户在该站 App 切换支付方式场景",
        "--how",
        "App 切换支付方式 → guan-zhong 查询站点基础信息 → tradeModes 为空 → 过滤礼品卡 → 返回个人钱包 0",
        "--inference-chain",
        "财务返回礼品卡 → guan-zhong payment-ways-v2 最终响应无礼品卡 → 代码过滤点依赖 tradeModes → 定位为 guan-zhong 过滤",
        "--json",
    )

    assert concluded.returncode == 0, concluded.stderr
    payload = json.loads(concluded.stdout)
    assert payload["state"]["flow"]["phase"] == "concluded"
    assert payload["state"]["conclusion"]["evidence"] == ["E1"]
    assert payload["state"]["conclusion"]["details"]["what"] == "用户切换支付方式后礼品卡不展示"
    assert payload["state"]["strategy_review"]["status"] == "pending"
    assert "strategy keep" in payload["state"]["flow"]["allowed_commands"]

    next_result = run_cli("next", "--state-file", str(state_file), "--json")
    next_payload = json.loads(next_result.stdout)
    assert "确认是否保留" in next_payload["next"]["message"]

    report = run_cli("report", "--state-file", str(state_file), "--audience", "review")
    assert report.returncode == 0, report.stderr
    assert "## 策略沉淀确认" in report.stdout
    assert "是否将本次最终查询策略保留" in report.stdout

    memory_file = tmp_path / "strategy-playbooks.json"
    kept = run_cli(
        "strategy",
        "keep",
        "--state-file",
        str(state_file),
        "--memory-file",
        str(memory_file),
        "--note",
        "App 支付方式过滤类问题可复用",
        "--json",
    )
    assert kept.returncode == 0, kept.stderr
    kept_payload = json.loads(kept.stdout)
    assert kept_payload["strategy_review"]["status"] == "kept"
    memory_payload = json.loads(memory_file.read_text(encoding="utf-8"))
    assert memory_payload["strategies"][0]["summary"] == "礼品卡在 guan-zhong payment-ways-v2 链路被过滤"


def test_report_renders_structured_technical_and_business_views(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "详情页展示礼品卡",
    )
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "payment-ways-v2 不展示礼品卡",
    )
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "SLS trace",
    )
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        "--finding",
        "finance returned gift card",
        "--lead",
        "trace_ids=trace-1",
        "--lead",
        "interfaces=/app/gun/payment-ways-v2",
        "--supports",
        "H2",
    )
    conclude = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "礼品卡在 guan-zhong payment-ways-v2 链路被过滤",
        "--evidence",
        "E1",
        "--confidence",
        "high",
        "--what",
        "用户切换支付方式后礼品卡不展示",
        "--where",
        "guan-zhong /app/gun/payment-ways-v2",
        "--when",
        "2026-04-25 16:51 前后",
        "--why-technical",
        "payment-ways-v2 链路未填充 tradeModes",
        "--why-business",
        "用户在国网互联站 App 端切换支付方式",
        "--blast-radius",
        "已知影响该用户在该站 App 切换支付方式场景",
        "--how",
        "App 切换支付方式 → guan-zhong 过滤礼品卡",
        "--inference-chain",
        "财务返回礼品卡 → guan-zhong 最终响应无礼品卡 → 代码过滤点命中",
    )
    assert conclude.returncode == 0, conclude.stdout + conclude.stderr

    technical = run_cli("report", "--state-file", str(state_file), "--audience", "technical")
    business = run_cli("report", "--state-file", str(state_file), "--audience", "business")
    review = run_cli("report", "--state-file", str(state_file), "--audience", "review")

    assert technical.returncode == 0, technical.stderr
    assert "## 排查结论" in technical.stdout
    assert "## 证据链" in technical.stdout
    assert "## 证据图" in technical.stdout
    assert "## 推断链" in technical.stdout
    assert "guan-zhong /app/gun/payment-ways-v2" in technical.stdout
    assert "trace:trace-1" in technical.stdout

    assert business.returncode == 0, business.stderr
    assert "## 结论" in business.stdout
    assert "技术根因" not in business.stdout
    assert "payment-ways-v2 链路未填充 tradeModes" not in business.stdout

    assert review.returncode == 0, review.stderr
    assert "# 排查结果" in review.stdout
    assert "问题复盘报告" not in review.stdout
    assert "## 关键过程" in review.stdout
    assert "| 时间 | 角色/系统 | 位置 | 动作 | 结果 |" in review.stdout
    assert "2026-04-25 16:51 前后" in review.stdout
    assert "用户" in review.stdout
    assert "guan-zhong /app/gun/payment-ways-v2" in review.stdout
    assert "## 链路说明" in review.stdout
    assert "## 原因分析" in review.stdout
    assert "## 根因定位" not in review.stdout
    assert "技术根因" not in review.stdout
    assert "定位位置" not in review.stdout
    assert "技术原因" in review.stdout
    assert "涉及位置" in review.stdout
    assert "## 影响范围" in review.stdout
    assert "## 后续建议" in review.stdout
    assert "## 证据参考" in review.stdout


def test_review_report_escapes_markdown_table_pipes(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "trace 命中 /app/gun/payment|ways",
    )
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS|prod",
        "--summary",
        "16:51:02 finance|guan 响应差异",
        "--finding",
        "finance returned gift card",
        "--lead",
        "trace_ids=trace-1",
        "--supports",
        "H1",
    )
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment|ways",
        "--source",
        "SLS trace",
    )
    conclude = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "礼品卡在 guan|zhong 链路被过滤",
        "--evidence",
        "E1",
        "--confidence",
        "high",
        "--what",
        "用户切换 payment|ways 后礼品卡不展示",
        "--where",
        "guan-zhong /app/gun/payment|ways",
        "--when",
        "2026-04-25 16:51 前后",
        "--why-technical",
        "tradeModes|giftCard 未填充",
        "--why-business",
        "用户在国网互联站 App 端切换支付方式",
        "--blast-radius",
        "已知影响该用户",
        "--how",
        "App → guan|zhong → 礼品卡过滤",
        "--inference-chain",
        "财务返回礼品卡 → guan-zhong 最终响应无礼品卡",
    )
    assert conclude.returncode == 0, conclude.stdout + conclude.stderr

    review = run_cli("report", "--state-file", str(state_file), "--audience", "review")

    assert review.returncode == 0, review.stderr
    assert "SLS\\|prod" in review.stdout
    assert "payment\\|ways" in review.stdout
    assert "tradeModes\\|giftCard" in review.stdout


def test_review_report_without_conclusion_uses_neutral_wording(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))

    review = run_cli("report", "--state-file", str(state_file), "--audience", "review")

    assert review.returncode == 0, review.stderr
    assert "# 排查结果" in review.stdout
    assert "当前还没有可输出的排查结论。" in review.stdout
    assert "复盘" not in review.stdout
    assert "根因" not in review.stdout


def test_concluded_session_blocks_more_actions(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "SLS trace",
    )
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡",
        "--supports",
        "H2",
    )
    run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "礼品卡在 guan-zhong payment-ways-v2 链路被过滤",
        "--evidence",
        "E1",
        "--what",
        "用户切换支付方式后礼品卡不展示",
        "--where",
        "guan-zhong /app/gun/payment-ways-v2",
        "--when",
        "2026-04-25 16:51 前后",
        "--why-technical",
        "payment-ways-v2 链路未填充 tradeModes",
        "--why-business",
        "用户在国网互联站 App 端切换支付方式",
        "--blast-radius",
        "已知影响该用户在该站 App 切换支付方式场景",
        "--how",
        "App 切换支付方式 → guan-zhong 过滤礼品卡",
        "--inference-chain",
        "财务返回礼品卡 → guan-zhong 最终响应无礼品卡 → 代码过滤点命中",
    )

    blocked = run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A2",
        "--source",
        "SLS",
        "--summary",
        "结论后追加证据",
        "--json",
    )

    assert blocked.returncode == 1
    assert "当前阶段 concluded 不允许记录 action" in json.loads(blocked.stdout)["error"]


def test_concluded_session_blocks_manual_evidence_add(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "SLS trace",
    )
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡",
    )
    run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "礼品卡在 guan-zhong payment-ways-v2 链路被过滤",
        "--evidence",
        "E1",
        "--what",
        "用户切换支付方式后礼品卡不展示",
        "--where",
        "guan-zhong /app/gun/payment-ways-v2",
        "--when",
        "2026-04-25 16:51 前后",
        "--why-technical",
        "payment-ways-v2 链路未填充 tradeModes",
        "--why-business",
        "用户在国网互联站 App 端切换支付方式",
        "--blast-radius",
        "已知影响该用户在该站 App 切换支付方式场景",
        "--how",
        "App 切换支付方式 → guan-zhong 过滤礼品卡",
        "--inference-chain",
        "财务返回礼品卡 → guan-zhong 最终响应无礼品卡 → 代码过滤点命中",
    )

    blocked = run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "结论后追加证据",
        "--json",
    )

    assert blocked.returncode == 1
    assert "当前阶段 concluded 不允许新增证据" in json.loads(blocked.stdout)["error"]


def test_action_record_stores_structured_history_and_report_flow(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    recorded = run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "sls",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        "--input",
        "query=15921195068 AND payment-ways-v2",
        "--input",
        "time_range=2026-04-25 16:40~17:10",
        "--input",
        "anchor=15921195068",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--gate",
        "keyword_source=code",
        "--elapsed-ms",
        "1200",
        "--finding",
        "finance returned gift card",
        "--lead",
        "trace_ids=trace-1",
        "--supports",
        "H2",
        "--json",
    )

    assert recorded.returncode == 0, recorded.stderr
    payload = json.loads(recorded.stdout)
    history = payload["state"]["action_history"]
    assert history[0]["input"]["query"] == "15921195068 AND payment-ways-v2"
    assert history[0]["gate"]["status"] == "passed"
    assert history[0]["output"]["elapsed_ms"] == 1200

    report = run_cli("report", "--state-file", str(state_file), "--audience", "technical")

    assert report.returncode == 0, report.stderr
    assert "## 完整排查流程" in report.stdout
    assert "查询 #1" in report.stdout
    assert "操作输入" in report.stdout
    assert "安全门控" in report.stdout
    assert "操作输出" in report.stdout


def test_action_record_rejects_duplicate_action_id(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "第一次查询 payment-ways-v2 日志",
    )

    duplicate = run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "第二次查询 payment-ways-v2 日志",
        "--json",
    )

    assert duplicate.returncode == 1
    assert "action_id 已存在：A1" in json.loads(duplicate.stdout)["error"]


def test_action_plan_then_complete_creates_evidence_and_history(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "sls",
        "--source",
        "SLS",
        "--objective",
        "确认财务是否返回礼品卡",
        "--success-criteria",
        "拿到 payment-ways-v2 trace 中财务返回和最终响应差异",
        "--input",
        "query=15921195068 AND payment-ways-v2",
        "--input",
        "time_range=2026-04-25 16:40~17:10",
        "--input",
        "anchor=15921195068",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--gate",
        "keyword_source=code",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    planned_payload = json.loads(planned.stdout)
    action = planned_payload["action"]
    assert action["action_id"] == "A1"
    assert action["status"] == "planned"
    assert planned_payload["state"]["action_plan"][0]["objective"] == "确认财务是否返回礼品卡"

    completed = run_cli(
        "action",
        "complete",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--summary",
        "财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        "--elapsed-ms",
        "1200",
        "--finding",
        "finance returned gift card",
        "--lead",
        "trace_ids=trace-1",
        "--supports",
        "H2",
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["evidence"]["id"] == "E1"
    assert payload["state"]["action_plan"][0]["status"] == "completed"
    assert payload["state"]["action_plan"][0]["evidence_id"] == "E1"
    history = payload["state"]["action_history"][0]
    assert history["action_id"] == "A1"
    assert history["input"]["query"] == "15921195068 AND payment-ways-v2"
    assert history["gate"]["status"] == "passed"
    assert history["output"]["summary"] == "财务返回礼品卡，guan-zhong 最终响应无礼品卡"


def test_action_complete_rejects_unplanned_action(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    completed = run_cli(
        "action",
        "complete",
        "--state-file",
        str(state_file),
        "--action-id",
        "A404",
        "--summary",
        "没有计划直接完成",
        "--json",
    )

    assert completed.returncode == 1
    assert "action plan 不存在：A404" in json.loads(completed.stdout)["error"]


def test_action_complete_rejects_already_completed_action(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--objective",
        "确认财务是否返回礼品卡",
        "--success-criteria",
        "拿到财务返回和最终响应差异",
    )
    run_cli(
        "action",
        "complete",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--summary",
        "财务返回礼品卡",
    )

    duplicate = run_cli(
        "action",
        "complete",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--summary",
        "再次完成同一个 action",
        "--json",
    )

    assert duplicate.returncode == 1
    assert "action 已完成：A1" in json.loads(duplicate.stdout)["error"]


def test_next_and_report_surface_pending_action_plan(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "用户问题",
    )
    run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "sls",
        "--source",
        "SLS",
        "--objective",
        "确认财务是否返回礼品卡",
        "--success-criteria",
        "拿到 payment-ways-v2 trace 中财务返回和最终响应差异",
        "--input",
        "query=15921195068 AND payment-ways-v2",
        "--input",
        "time_range=2026-04-25 16:40~17:10",
        "--input",
        "anchor=15921195068",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--gate",
        "keyword_source=code",
    )

    next_result = run_cli("next", "--state-file", str(state_file), "--json")
    report = run_cli("report", "--state-file", str(state_file), "--audience", "technical")

    assert next_result.returncode == 0, next_result.stderr
    payload = json.loads(next_result.stdout)
    assert "待完成 action" in payload["next"]["message"]
    assert "action complete A1" in payload["next"]["next_actions"]

    assert report.returncode == 0, report.stderr
    assert "## Action Plan" in report.stdout
    assert "确认财务是否返回礼品卡" in report.stdout
    assert "planned" in report.stdout


def test_action_plan_requires_track_specific_fields(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    sls_missing_time = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "sls",
        "--source",
        "SLS",
        "--objective",
        "确认财务是否返回礼品卡",
        "--success-criteria",
        "拿到财务返回和最终响应差异",
        "--input",
        "query=15921195068 AND payment-ways-v2",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--json",
    )

    assert sls_missing_time.returncode == 1
    assert "track sls 缺少 input 字段：time_range" in json.loads(sls_missing_time.stdout)["error"]

    sql_missing_explain = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A2",
        "--track",
        "sql",
        "--source",
        "Doris",
        "--objective",
        "确认订单是否存在礼品卡支付记录",
        "--success-criteria",
        "查询到订单支付方式明细",
        "--input",
        "sql=select * from t_order where order_no='123456'",
        "--input",
        "env=prod",
        "--gate",
        "type=sql",
        "--json",
    )

    assert sql_missing_explain.returncode == 1
    assert "track sql 缺少 gate 字段：explain" in json.loads(sql_missing_explain.stdout)["error"]


def test_action_plan_accepts_valid_track_specific_fields(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    valid = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "sls",
        "--source",
        "SLS",
        "--objective",
        "确认财务是否返回礼品卡",
        "--success-criteria",
        "拿到财务返回和最终响应差异",
        "--input",
        "query=15921195068 AND payment-ways-v2",
        "--input",
        "time_range=2026-04-25 16:40~17:10",
        "--input",
        "anchor=15921195068",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--gate",
        "keyword_source=code",
        "--json",
    )

    assert valid.returncode == 0, valid.stderr
    payload = json.loads(valid.stdout)
    assert payload["action"]["input"]["time_range"] == "2026-04-25 16:40~17:10"
    assert payload["action"]["gate"]["status"] == "passed"


def test_sls_action_plan_requires_distinctive_anchor_and_keyword_source(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "充电单号 2604251117229860 余额不足停充", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    generic_anchor = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SLS1",
        "--track",
        "sls",
        "--source",
        "SLS",
        "--objective",
        "查询余额不足日志",
        "--success-criteria",
        "命中问题日志",
        "--input",
        "query=余额不足",
        "--input",
        "time_range=2026-04-25 11:00~12:00",
        "--input",
        "anchor=余额不足",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--gate",
        "keyword_source=none",
        "--json",
    )

    assert generic_anchor.returncode == 1
    assert "anchor 区分度不足" in json.loads(generic_anchor.stdout)["error"]

    guessed_keyword = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SLS2",
        "--track",
        "sls",
        "--source",
        "SLS",
        "--objective",
        "查询订单余额不足日志",
        "--success-criteria",
        "命中问题日志",
        "--input",
        "query=2604251117229860 AND 余额不足",
        "--input",
        "time_range=2026-04-25 11:00~12:00",
        "--input",
        "anchor=2604251117229860",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--gate",
        "keyword_source=none",
        "--json",
    )

    assert guessed_keyword.returncode == 1
    assert "低区分度/猜测性关键词" in json.loads(guessed_keyword.stdout)["error"]

    valid = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SLS3",
        "--track",
        "sls",
        "--source",
        "SLS",
        "--objective",
        "查询订单 setAccount 日志",
        "--success-criteria",
        "命中余额下发日志",
        "--input",
        "query=2604251117229860 AND setAccount",
        "--input",
        "time_range=2026-04-25 11:00~12:00",
        "--input",
        "anchor=2604251117229860",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--gate",
        "keyword_source=code",
        "--json",
    )

    assert valid.returncode == 0, valid.stderr


def test_action_plan_validates_code_kb_and_unknown_tracks(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    code_missing_target = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "code",
        "--source",
        "repo",
        "--objective",
        "确认 guan-zhong 是否过滤礼品卡",
        "--success-criteria",
        "定位到过滤分支",
        "--input",
        "repo=guan-zhong",
        "--gate",
        "type=code",
        "--gate",
        "scope=read-only",
        "--json",
    )
    assert code_missing_target.returncode == 1
    assert "track code 缺少 input 字段：target" in json.loads(code_missing_target.stdout)["error"]

    kb_valid = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A2",
        "--track",
        "kb",
        "--source",
        "Obsidian",
        "--objective",
        "查找互联站礼品卡规则",
        "--success-criteria",
        "找到交易模式与礼品卡展示规则",
        "--input",
        "query=互联站 礼品卡 tradeMode",
        "--gate",
        "type=kb",
        "--json",
    )
    assert kb_valid.returncode == 0, kb_valid.stderr

    unknown = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A3",
        "--track",
        "browser",
        "--source",
        "Chrome",
        "--objective",
        "打开页面查看",
        "--success-criteria",
        "看到页面现象",
        "--json",
    )
    assert unknown.returncode == 1
    assert "未知 action track：browser" in json.loads(unknown.stdout)["error"]


def test_manual_action_plan_allows_empty_input_and_gate(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    manual = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "M1",
        "--track",
        "manual",
        "--source",
        "用户补充",
        "--objective",
        "确认用户端操作路径",
        "--success-criteria",
        "用户确认 App 切换支付方式后礼品卡消失",
        "--json",
    )

    assert manual.returncode == 0, manual.stderr
    payload = json.loads(manual.stdout)
    assert payload["action"]["input"] == {}
    assert payload["action"]["gate"] == {}


def test_report_masks_sensitive_display_values(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "用户手机号 15921195068，token=abc-secret-token",
        "--finding",
        "phone=15921195068",
        "--supports",
        "H2",
    )

    report = run_cli("report", "--state-file", str(state_file), "--audience", "technical")

    assert report.returncode == 0, report.stderr
    assert "15921195068" not in report.stdout
    assert "159****5068" in report.stdout
    assert "abc-secret-token" not in report.stdout


def test_report_masks_sensitive_values_in_conclusion_details(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "用户问题",
    )
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡",
    )
    run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "手机号 15921195068 的礼品卡在 guan-zhong payment-ways-v2 链路被过滤",
        "--evidence",
        "E1",
        "--what",
        "手机号 15921195068 用户切换支付方式后礼品卡不展示",
        "--where",
        "guan-zhong /app/gun/payment-ways-v2",
        "--when",
        "2026-04-25 16:51 前后",
        "--why-technical",
        "payment-ways-v2 链路未填充 tradeModes",
        "--why-business",
        "手机号 15921195068 用户在国网互联站 App 端切换支付方式",
        "--blast-radius",
        "已知影响手机号 15921195068 在该站 App 切换支付方式场景",
        "--how",
        "手机号 15921195068 用户切换支付方式 → guan-zhong 过滤礼品卡",
        "--inference-chain",
        "手机号 15921195068 财务返回礼品卡 → guan-zhong 最终响应无礼品卡 → 代码过滤点命中",
    )

    technical = run_cli("report", "--state-file", str(state_file), "--audience", "technical")
    business = run_cli("report", "--state-file", str(state_file), "--audience", "business")

    assert technical.returncode == 0, technical.stderr
    assert business.returncode == 0, business.stderr
    assert "15921195068" not in technical.stdout
    assert "15921195068" not in business.stdout
    assert "159****5068" in technical.stdout
    assert "159****5068" in business.stdout


def test_conclude_requires_scene_facts_before_hypothesis_lock_in(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡",
        "--supports",
        "H2",
    )

    blocked = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "礼品卡在 guan-zhong 链路被过滤",
        "--evidence",
        "E1",
        "--what",
        "用户切换支付方式后礼品卡不展示",
        "--where",
        "guan-zhong /app/gun/payment-ways-v2",
        "--when",
        "2026-04-25 16:51 前后",
        "--why-technical",
        "payment-ways-v2 链路未填充 tradeModes",
        "--why-business",
        "用户在国网互联站 App 端切换支付方式",
        "--blast-radius",
        "已知影响该用户在该站 App 切换支付方式场景",
        "--how",
        "App 切换支付方式 → guan-zhong 过滤礼品卡",
        "--inference-chain",
        "财务返回礼品卡 → guan-zhong 最终响应无礼品卡 → 代码过滤点命中",
        "--json",
    )

    assert blocked.returncode == 1
    assert "缺少场景事实" in json.loads(blocked.stdout)["error"]


def test_scene_fact_records_evidence_first_context_and_report_renders_it(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS trace",
        "--summary",
        "命中 /app/gun/payment-ways-v2 入口",
    )

    fact = run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "SLS trace",
        "--evidence",
        "E1",
        "--json",
    )

    assert fact.returncode == 0, fact.stderr
    payload = json.loads(fact.stdout)
    assert payload["state"]["scene_facts"][0]["category"] == "entrypoint"
    assert payload["state"]["scene_facts"][0]["name"] == "app_payment_ways"

    report = run_cli("report", "--state-file", str(state_file), "--audience", "technical")

    assert report.returncode == 0, report.stderr
    assert "## 场景事实" in report.stdout
    assert "app_payment_ways" in report.stdout
    assert "/app/gun/payment-ways-v2" in report.stdout


def test_hypothesis_can_be_derived_from_scene_fact_and_evidence(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "详情页展示礼品卡",
    )
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "payment-ways-v2 不展示礼品卡",
    )
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "variant",
        "--name",
        "detail_vs_payment_ways",
        "--value",
        "detail has tradeModes, payment-ways-v2 missing tradeModes",
        "--source",
        "SLS/code",
    )

    derived = run_cli(
        "hypothesis",
        "add",
        "--state-file",
        str(state_file),
        "--id",
        "H4",
        "--statement",
        "入口链路上下文不一致导致礼品卡被误过滤",
        "--source-fact",
        "detail_vs_payment_ways",
        "--source-evidence",
        "E2",
        "--json",
    )

    assert derived.returncode == 0, derived.stderr
    payload = json.loads(derived.stdout)
    hypothesis = next(item for item in payload["state"]["hypotheses"] if item["id"] == "H4")
    assert hypothesis["source_facts"] == ["detail_vs_payment_ways"]
    assert hypothesis["source_evidence"] == ["E2"]
    assert hypothesis["status"] == "待验证"


def test_scene_fact_rejects_unknown_evidence_refs(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    fact = run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "SLS trace",
        "--evidence",
        "E404",
        "--json",
    )

    assert fact.returncode == 1
    assert "引用的 evidence 不存在" in json.loads(fact.stdout)["error"]


def test_manual_evidence_is_visible_in_action_history(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    added = run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "用户补充",
        "--summary",
        "用户反馈 App 端切换支付方式后礼品卡消失",
        "--supports",
        "H2",
        "--json",
    )

    assert added.returncode == 0, added.stderr
    payload = json.loads(added.stdout)
    history = payload["state"]["action_history"]
    assert history[0]["track"] == "manual"
    assert history[0]["output"]["evidence_id"] == "E1"


def test_hypothesis_rejects_unknown_source_refs(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    missing_fact = run_cli(
        "hypothesis",
        "add",
        "--state-file",
        str(state_file),
        "--id",
        "H4",
        "--statement",
        "入口链路上下文不一致导致礼品卡被误过滤",
        "--source-fact",
        "not_exists",
        "--json",
    )

    assert missing_fact.returncode == 1
    assert "引用的 scene fact 不存在" in json.loads(missing_fact.stdout)["error"]

    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "variant",
        "--name",
        "detail_vs_payment_ways",
        "--value",
        "detail has tradeModes, payment-ways-v2 missing tradeModes",
        "--source",
        "SLS/code",
    )
    missing_evidence = run_cli(
        "hypothesis",
        "add",
        "--state-file",
        str(state_file),
        "--id",
        "H4",
        "--statement",
        "入口链路上下文不一致导致礼品卡被误过滤",
        "--source-fact",
        "detail_vs_payment_ways",
        "--source-evidence",
        "E404",
        "--json",
    )

    assert missing_evidence.returncode == 1
    assert "引用的 evidence 不存在" in json.loads(missing_evidence.stdout)["error"]


def test_hypothesis_requires_fact_or_evidence_source(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    blocked = run_cli(
        "hypothesis",
        "add",
        "--state-file",
        str(state_file),
        "--id",
        "H4",
        "--statement",
        "入口链路上下文不一致导致礼品卡被误过滤",
        "--json",
    )

    assert blocked.returncode == 1
    assert "假设必须引用至少一个 scene fact 或 evidence" in json.loads(blocked.stdout)["error"]


def test_next_guides_scene_discovery_before_hypothesis_validation(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    initial_next = run_cli("next", "--state-file", str(state_file), "--json")

    assert initial_next.returncode == 0, initial_next.stderr
    payload = json.loads(initial_next.stdout)
    assert "场景事实" in payload["next"]["message"]
    assert "scene fact" in payload["next"]["next_actions"]

    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "用户问题",
    )
    after_fact = run_cli("next", "--state-file", str(state_file), "--json")

    assert after_fact.returncode == 0, after_fact.stderr
    payload = json.loads(after_fact.stdout)
    assert "action record" in payload["next"]["next_actions"]
    assert "hypothesis add" in payload["next"]["next_actions"]


def test_conclude_rejects_low_information_details(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "用户问题",
    )
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        "--supports",
        "H2",
    )

    weak = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "礼品卡被过滤",
        "--evidence",
        "E1",
        "--what",
        "礼品卡不展示",
        "--where",
        "后端",
        "--when",
        "今天",
        "--why-technical",
        "有问题",
        "--why-business",
        "用户操作",
        "--blast-radius",
        "部分用户",
        "--how",
        "用户操作后出现问题",
        "--inference-chain",
        "财务返回礼品卡 -> guan-zhong 最终响应无礼品卡",
        "--json",
    )

    assert weak.returncode == 1
    error = json.loads(weak.stdout)["error"]
    assert "结论字段质量不足" in error
    assert "where" in error
    assert "when" in error
    assert "blast_radius" in error


def test_state_show_migrates_legacy_state_schema(tmp_path: Path) -> None:
    state_file = tmp_path / "legacy.json"
    state_file.write_text(
        json.dumps(
            {
                "session_id": "sess_legacy",
                "flow": {"current_step": 1},
                "entities": {"phone": "15921195068"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run_cli("state", "show", "--state-file", str(state_file), "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    state = payload["state"]
    assert state["schema_version"] == 1
    assert state["scene_facts"] == []
    assert state["action_history"] == []
    assert state["evidence_graph"] == {"nodes": [], "edges": []}


def test_state_show_writes_migrated_schema_back_to_file(tmp_path: Path) -> None:
    state_file = tmp_path / "legacy.json"
    state_file.write_text(
        json.dumps(
            {
                "session_id": "legacy",
                "flow": {"current_step": 1, "execution_mode": "auto"},
                "entities": {"order_no": "123456"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = run_cli("state", "show", "--state-file", str(state_file), "--json")

    assert result.returncode == 0, result.stderr
    persisted = json.loads(state_file.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == 1
    assert persisted["scene_facts"] == []
    assert persisted["action_history"] == []
    assert persisted["evidence_graph"] == {"nodes": [], "edges": []}


def test_report_json_includes_rendered_report_for_audience(tmp_path: Path) -> None:
    state_file = tmp_path / "state.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "用户问题",
    )
    result = run_cli("report", "--state-file", str(state_file), "--format", "json", "--audience", "technical")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["audience"] == "technical"
    assert "## 场景事实" in payload["report"]
    assert payload["state"]["schema_version"] == 1


def test_reopen_supersedes_conclusion_and_allows_new_evidence(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "app_payment_ways",
        "--value",
        "/app/gun/payment-ways-v2",
        "--source",
        "用户问题",
    )
    run_cli(
        "action",
        "record",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡，guan-zhong 最终响应无礼品卡",
    )
    run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "礼品卡在 guan-zhong payment-ways-v2 链路被过滤",
        "--evidence",
        "E1",
        "--what",
        "用户切换支付方式后礼品卡不展示",
        "--where",
        "guan-zhong /app/gun/payment-ways-v2",
        "--when",
        "2026-04-25 16:51 前后",
        "--why-technical",
        "payment-ways-v2 链路未填充 tradeModes",
        "--why-business",
        "用户在国网互联站 App 端切换支付方式",
        "--blast-radius",
        "已知影响该用户在该站 App 切换支付方式场景",
        "--how",
        "App 切换支付方式 → guan-zhong 过滤礼品卡",
        "--inference-chain",
        "财务返回礼品卡 → guan-zhong 最终响应无礼品卡 → 代码过滤点命中",
    )

    reopened = run_cli(
        "reopen",
        "--state-file",
        str(state_file),
        "--reason",
        "用户补充微信小程序可用，需要修订 App 端影响范围",
        "--json",
    )

    assert reopened.returncode == 0, reopened.stderr
    payload = json.loads(reopened.stdout)
    state = payload["state"]
    assert state["flow"]["phase"] == "evidence_collecting"
    assert state["revision"] == 2
    assert "conclusion" not in state
    assert state["conclusion_history"][0]["status"] == "superseded"
    assert state["conclusion_history"][0]["reopen_reason"] == "用户补充微信小程序可用，需要修订 App 端影响范围"

    added = run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "用户补充",
        "--summary",
        "微信小程序启动充电时礼品卡可展示",
        "--json",
    )

    assert added.returncode == 0, added.stderr

    report = run_cli("report", "--state-file", str(state_file), "--audience", "technical")
    assert report.returncode == 0, report.stderr
    assert "## 结论版本历史" in report.stdout
    assert "用户补充微信小程序可用" in report.stdout


def test_evidence_records_kind_strength_and_report_renders_quality(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    added = run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "payment-ways-v2 最终响应不包含礼品卡",
        "--kind",
        "log",
        "--strength",
        "strong",
        "--raw-ref",
        "trace-1",
        "--json",
    )

    assert added.returncode == 0, added.stderr
    payload = json.loads(added.stdout)
    evidence = payload["evidence"]
    assert evidence["kind"] == "log"
    assert evidence["strength"] == "strong"
    assert evidence["raw_ref"] == "trace-1"

    report = run_cli("report", "--state-file", str(state_file), "--audience", "technical")
    assert report.returncode == 0, report.stderr
    assert "质量" in report.stdout
    assert "log/strong" in report.stdout


def test_evidence_rejects_unknown_quality_values(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    bad_kind = run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "未知类型证据",
        "--kind",
        "screenshot",
        "--json",
    )
    assert bad_kind.returncode == 1
    assert "未知 evidence kind" in json.loads(bad_kind.stdout)["error"]

    bad_strength = run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "未知强度证据",
        "--strength",
        "certain",
        "--json",
    )
    assert bad_strength.returncode == 1
    assert "未知 evidence strength" in json.loads(bad_strength.stdout)["error"]
