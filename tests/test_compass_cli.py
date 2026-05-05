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


def run_scene_fact(
    state_file: Path,
    *,
    category: str = "entrypoint",
    name: str = "app_payment_ways",
    value: str = "/app/gun/payment-ways-v2",
    source: str = "用户问题",
) -> subprocess.CompletedProcess[str]:
    return run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        category,
        "--name",
        name,
        "--value",
        value,
        "--source",
        source,
    )


def has_scene_fact(state_file: Path) -> bool:
    if not state_file.exists():
        return False
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(state.get("scene_facts"))


def has_playbook_recall(state_file: Path) -> bool:
    if not state_file.exists():
        return False
    try:
        state = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool((state.get("playbook_recall") or {}).get("recalled"))


def run_playbook_recall(
    state_file: Path,
    *,
    match: str = "unknown-entrypoint-log-to-trace",
) -> subprocess.CompletedProcess[str]:
    return run_cli(
        "playbook",
        "recall",
        "--state-file",
        str(state_file),
        "--match",
        match,
    )


def run_planned_action(
    state_file: Path,
    *,
    action_id: str = "A1",
    source: str = "SLS",
    summary: str = "查询完成",
    track: str = "manual",
    objective: str = "验证问题线索",
    success_criteria: str = "产生可引用证据",
    inputs: list[str] | None = None,
    gates: list[str] | None = None,
    elapsed_ms: int | None = None,
    findings: list[str] | None = None,
    leads: list[str] | None = None,
    supports: str | None = None,
    json_output: bool = False,
    ensure_scene: bool = True,
) -> subprocess.CompletedProcess[str]:
    if ensure_scene and not has_scene_fact(state_file):
        fact = run_scene_fact(state_file)
        assert fact.returncode == 0, fact.stdout + fact.stderr
    plan_args = [
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        action_id,
        "--track",
        track,
        "--source",
        source,
        "--objective",
        objective,
        "--success-criteria",
        success_criteria,
    ]
    for item in inputs or []:
        plan_args.extend(["--input", item])
    for item in gates or []:
        plan_args.extend(["--gate", item])
    planned = run_cli(*plan_args)
    assert planned.returncode == 0, planned.stdout + planned.stderr

    complete_args = [
        "action",
        "complete",
        "--state-file",
        str(state_file),
        "--action-id",
        action_id,
        "--summary",
        summary,
    ]
    if elapsed_ms is not None:
        complete_args.extend(["--elapsed-ms", str(elapsed_ms)])
    for item in findings or []:
        complete_args.extend(["--finding", item])
    for item in leads or []:
        complete_args.extend(["--lead", item])
    if supports:
        complete_args.extend(["--supports", supports])
    if json_output:
        complete_args.append("--json")
    return run_cli(*complete_args)


def test_intake_outputs_structured_json() -> None:
    result = run_cli("intake", "用户支付成功但订单没有推进，订单号 123456，今天上午", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["scene"] == "payment"
    assert payload["standard_problem"]
    assert payload["entities"]["order_no"] == "123456"
    assert "hypotheses" not in payload
    assert payload["investigation_hints"][0]["type"] == "candidate_direction"
    assert payload["investigation_hints"][0]["status"] == "reference_only"


def test_start_keeps_intake_hints_out_of_formal_hypotheses(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    result = run_cli("start", "某把枪突然充电校验失败，枪号 G001", "--state-file", str(state_file), "--json")

    assert result.returncode == 0, result.stderr
    state = json.loads(result.stdout)["state"]
    assert state["hypotheses"] == []
    assert state["hypothesis_mode"] == "evidence_first"
    assert state["investigation_hints"]
    assert state["investigation_hints"][0]["type"] == "candidate_direction"


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
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "manual",
        "--source",
        "SLS",
        "--objective",
        "确认财务是否返回礼品卡",
        "--success-criteria",
        "生成可引用证据",
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
    run_scene_fact(state_file)

    explain_low = (
        "0:VOlapScanNode(204)\n"
        "TABLE: t_pay\n"
        "PREDICATES: ((phone = '15921195068'))\n"
        "partitions=1/1\n"
        "tablets=1/1\n"
        "cardinality=1200, avgRowSize=0.0, numNodes=1\n"
    )
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
        "--input",
        f"explain_text={explain_low}",
        "--gate",
        "type=sql",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["action"]["input"]["env"] == "prod"
    assert payload["action"]["status"] == "planned"
    assert payload["action"]["gate"]["status"] == "passed"
    assert payload["action"]["gate"]["risk"] == "low"
    assert payload["action"]["gate"]["assessor"] == "compass.sql_gate.assess_sql_explain"


def test_confirm_then_record_action_creates_evidence_and_leads(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))

    confirmed = run_cli("confirm", "--state-file", str(state_file), "--mode", "auto", "--json")

    assert confirmed.returncode == 0, confirmed.stderr
    assert json.loads(confirmed.stdout)["state"]["flow"]["phase"] == "action_ready"

    recorded = run_planned_action(
        state_file,
        summary="财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        findings=[
            "finance returned subPayWay=3 amount=2319.01",
            "payment-ways-v2 response removed gift card",
        ],
        leads=["trace_ids=trace-1", "interfaces=/app/gun/payment-ways-v2"],
        supports="H2",
        json_output=True,
    )

    assert recorded.returncode == 0, recorded.stderr
    payload = json.loads(recorded.stdout)
    assert payload["ok"] is True
    assert payload["evidence"]["id"] == "E1"
    assert payload["state"]["flow"]["phase"] == "evidence_collecting"
    assert "evidence_graph" not in payload["state"]


def test_next_guides_agents_to_plan_actions_not_record_after_confirm(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    confirmed = run_cli("confirm", "--state-file", str(state_file), "--mode", "auto", "--json")

    assert confirmed.returncode == 0, confirmed.stderr
    allowed = json.loads(confirmed.stdout)["state"]["flow"]["allowed_commands"]
    assert "scene fact" in allowed
    assert "action plan" in allowed
    assert "action record" not in allowed

    next_res = run_cli("next", "--state-file", str(state_file), "--json")
    assert next_res.returncode == 0, next_res.stderr
    next_actions = json.loads(next_res.stdout)["next"]["next_actions"]
    assert "scene fact" in next_actions
    assert "action plan" in next_actions
    assert "action record" not in next_actions

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
        "绕过 action plan 的事后补录",
        "--json",
    )
    assert recorded.returncode == 2
    assert "invalid choice" in recorded.stderr


def test_action_plan_requires_scene_fact_first(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")

    blocked = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "manual",
        "--source",
        "SLS",
        "--objective",
        "查询支付方式链路",
        "--success-criteria",
        "产生可引用证据",
        "--json",
    )

    assert blocked.returncode == 1
    assert "缺少场景事实" in json.loads(blocked.stdout)["error"]


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

    run_planned_action(
        state_file,
        summary="财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        findings=["finance returned gift card"],
        supports="H2",
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
    assert "report" in payload["state"]["flow"]["allowed_commands"]
    assert "strategy keep" not in payload["state"]["flow"]["allowed_commands"]

    next_result = run_cli("next", "--state-file", str(state_file), "--json")
    next_payload = json.loads(next_result.stdout)
    assert "生成报告" in next_payload["next"]["message"]

    report = run_cli("report", "--state-file", str(state_file), "--audience", "review")
    assert report.returncode == 0, report.stderr
    assert "## 策略沉淀确认" in report.stdout
    assert "是否将本次最终查询策略保留" in report.stdout

    memory_file = tmp_path / "strategies.yaml"
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
    assert "strategy keep" not in kept_payload["state"]["flow"]["allowed_commands"]
    import yaml

    memory_payload = yaml.safe_load(memory_file.read_text(encoding="utf-8"))
    strategy = memory_payload["strategies"][0]
    assert strategy["pattern"]["category"] == "payment"
    assert strategy["pattern"]["entity_types"] == ["phone", "time_range"]
    assert strategy["score"]["effectiveness"] == 0.0
    assert strategy["meta"]["source_summary"] == "礼品卡在 guan-zhong payment-ways-v2 链路被过滤"
    assert strategy["meta"]["note"] == "App 支付方式过滤类问题可复用"

    duplicate_keep = run_cli(
        "strategy",
        "keep",
        "--state-file",
        str(state_file),
        "--memory-file",
        str(memory_file),
        "--json",
    )
    assert duplicate_keep.returncode == 1
    assert "策略沉淀已确认" in json.loads(duplicate_keep.stdout)["error"]


def test_strategy_review_requires_report_after_conclusion(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    memory_file = tmp_path / "strategies.yaml"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)
    run_planned_action(state_file, ensure_scene=False)
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

    assert blocked.returncode == 1
    assert "请先生成报告" in json.loads(blocked.stdout)["error"]

    report = run_cli("report", "--state-file", str(state_file), "--audience", "review", "--format", "json")
    assert report.returncode == 0, report.stderr
    report_payload = json.loads(report.stdout)
    assert report_payload["state"]["flow"]["report_generated"] is True
    assert "strategy keep" in report_payload["state"]["flow"]["allowed_commands"]


def test_strategy_memory_preserves_planned_action_query_path(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    memory_file = tmp_path / "strategies.yaml"
    run_cli("start", "支付单 2604251117229860 预付款停充，今天 11:17", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "charge_start",
        "--value",
        "预付款启动充电",
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
        "charge-server",
        "--objective",
        "确认下发电桩余额时使用的是余额账户还是预付款账户",
        "--success-criteria",
        "日志包含支付单号并能看到下发余额字段来源",
        "--input",
        "query=2604251117229860",
        "--input",
        "anchor=2604251117229860",
        "--input",
        "time_range=2026-04-25 11:00~12:00",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--gate",
        "keyword_source=none",
    )
    run_cli(
        "action",
        "complete",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--summary",
        "日志显示下发电桩余额取自 balanceAmount=10",
        "--finding",
        "balanceAmount=10",
    )
    concluded = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "预付款启动后下发电桩余额错误使用余额账户金额",
        "--evidence",
        "E1",
        "--confidence",
        "high",
        "--what",
        "预付款启动充电后电桩收到的可用金额为余额账户 10 元",
        "--where",
        "charge-server /start-charge balanceAmount",
        "--when",
        "2026-04-25 11:17 前后",
        "--why-technical",
        "启动链路组装电桩余额时读取余额账户字段，未区分预付款支付方式",
        "--why-business",
        "用户预付 20 元启动后又充值余额 10 元",
        "--blast-radius",
        "已知影响单充电单 2604251117229860，批量影响待同类支付方式确认",
        "--how",
        "用户预付款启动 → 余额充值 10 元 → 启动链路取余额账户金额 → 下发电桩 10 元 → 电桩余额不足停充",
        "--inference-chain",
        "用户描述预付 20 元和余额充值 10 元 → SLS 显示下发 balanceAmount=10 → 定位为启动链路余额来源错误",
    )
    assert concluded.returncode == 0, concluded.stderr
    run_cli("report", "--state-file", str(state_file), "--audience", "review")
    kept = run_cli(
        "strategy",
        "keep",
        "--state-file",
        str(state_file),
        "--memory-file",
        str(memory_file),
        "--json",
    )
    assert kept.returncode == 0, kept.stderr

    import yaml

    strategy = yaml.safe_load(memory_file.read_text(encoding="utf-8"))["strategies"][0]
    assert strategy["plan"][0]["action"] == "确认下发电桩余额时使用的是余额账户还是预付款账户"
    assert strategy["plan"][0]["template"] == "2604251117229860"
    assert strategy["plan"][0]["success_criteria"] == "日志包含支付单号并能看到下发余额字段来源"


def test_strategy_keep_rejects_invalid_strategy_memory_shape(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    memory_file = tmp_path / "strategies.yaml"
    memory_file.write_text("strategies: {}\n", encoding="utf-8")
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
    run_planned_action(
        state_file,
        summary="财务返回礼品卡，guan-zhong 最终响应无礼品卡",
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
    run_cli("report", "--state-file", str(state_file), "--audience", "review")

    kept = run_cli(
        "strategy",
        "keep",
        "--state-file",
        str(state_file),
        "--memory-file",
        str(memory_file),
        "--json",
    )

    assert kept.returncode == 1
    assert "strategies 字段必须是列表" in json.loads(kept.stdout)["error"]


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
    run_planned_action(
        state_file,
        summary="财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        findings=["finance returned gift card"],
        leads=["trace_ids=trace-1", "interfaces=/app/gun/payment-ways-v2"],
        supports="H2",
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
    assert "## 证据图" not in technical.stdout
    assert "## 推断链" in technical.stdout
    assert "guan-zhong /app/gun/payment-ways-v2" in technical.stdout
    assert "trace_ids: trace-1" in technical.stdout

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
    run_planned_action(
        state_file,
        source="SLS|prod",
        summary="16:51:02 finance|guan 响应差异",
        findings=["finance returned gift card"],
        leads=["trace_ids=trace-1"],
        supports="H1",
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
    run_planned_action(
        state_file,
        summary="财务返回礼品卡",
        supports="H2",
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
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A2",
        "--track",
        "manual",
        "--source",
        "SLS",
        "--objective",
        "结论后追加证据",
        "--success-criteria",
        "不应允许",
        "--json",
    )

    assert blocked.returncode == 1
    assert "当前阶段 concluded 不允许规划 action" in json.loads(blocked.stdout)["error"]


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
    run_planned_action(
        state_file,
        summary="财务返回礼品卡",
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


def test_action_plan_complete_stores_structured_history_and_report_flow(tmp_path: Path) -> None:
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

    recorded = run_planned_action(
        state_file,
        track="sls",
        source="SLS",
        summary="财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        inputs=[
            "query=15921195068 AND payment-ways-v2",
            "time_range=2026-04-25 16:40~17:10",
            "anchor=15921195068",
        ],
        gates=["type=sls", "status=passed", "keyword_source=code"],
        elapsed_ms=1200,
        findings=["finance returned gift card"],
        leads=["trace_ids=trace-1"],
        supports="H2",
        json_output=True,
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


def test_action_plan_rejects_duplicate_action_id(tmp_path: Path) -> None:
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
    run_planned_action(
        state_file,
        summary="第一次查询 payment-ways-v2 日志",
    )

    duplicate = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "manual",
        "--source",
        "SLS",
        "--objective",
        "第二次查询 payment-ways-v2 日志",
        "--success-criteria",
        "不应允许",
        "--json",
    )

    assert duplicate.returncode == 1
    assert "action_id 已存在：A1" in json.loads(duplicate.stdout)["error"]


def test_action_plan_then_complete_creates_evidence_and_history(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)

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


def test_action_plan_and_complete_render_natural_language_display(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)

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
    )

    assert planned.returncode == 0, planned.stderr
    assert "准备执行：" in planned.stdout
    assert "命令原文：" in planned.stdout
    assert "compass action plan --action-id A1" in planned.stdout
    assert "门禁评估：通过" in planned.stdout
    assert "结果：" in planned.stdout
    assert "结果原文：" not in planned.stdout
    assert '"action_id"' not in planned.stdout

    completed = run_cli(
        "action",
        "complete",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--summary",
        "财务返回礼品卡，最终响应无礼品卡",
        "--finding",
        "finance returned gift card",
    )

    assert completed.returncode == 0, completed.stderr
    assert "执行结论：" in completed.stdout
    assert "生成证据 E1" in completed.stdout
    assert "结果原文：" not in completed.stdout
    assert '"summary"' not in completed.stdout


def test_action_plan_json_includes_display_contract(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)

    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
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

    assert planned.returncode == 0, planned.stderr
    display = json.loads(planned.stdout)["display"]
    assert display["before"].startswith("准备执行：")
    assert display["command_raw"].startswith("compass action plan --action-id A1")
    assert display["after"].startswith("结果：")


def test_runtime_records_lightweight_events_for_observability(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)
    completed = run_planned_action(state_file, json_output=True)

    assert completed.returncode == 0, completed.stderr
    state = json.loads(completed.stdout)["state"]
    event_types = [event["type"] for event in state["events"]]
    assert event_types[:4] == [
        "session_started",
        "session_confirmed",
        "scene_fact_recorded",
        "action_planned",
    ]
    assert event_types[-1] == "action_completed"
    assert state["events"][-1]["summary"] == "查询完成"
    assert state["events"][-1]["refs"]["action_id"] == "A1"
    assert state["events"][-1]["refs"]["evidence_id"] == "E1"


def test_action_plan_records_applied_playbooks_and_knowledge(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)
    run_playbook_recall(state_file, match="direct-failure-to-change-root-cause")

    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "manual",
        "--source",
        "playbook",
        "--objective",
        "按通用知识检查是否只是半原因",
        "--success-criteria",
        "结论前补最近变更证据",
        "--playbook",
        "direct-failure-to-change-root-cause",
        "--knowledge",
        "K001",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    action = payload["action"]
    assert action["applied_playbooks"] == ["direct-failure-to-change-root-cause"]
    assert action["applied_knowledge"] == ["K001"]
    assert "--playbook direct-failure-to-change-root-cause" in payload["display"]["command_raw"]


def test_action_plan_injects_context_without_requiring_recall_step(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户提供截图，页面提示校验失败，手机号 15921195068", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file, category="entrypoint", name="screenshot_keyword", value="页面提示校验失败", source="用户截图")

    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "manual",
        "--source",
        "用户截图",
        "--objective",
        "根据截图关键字查当时调用日志",
        "--success-criteria",
        "action 自动携带 playbook/知识上下文",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    action = json.loads(planned.stdout)["action"]
    context = action["context"]
    assert context["playbook_index"] == "knowledge/playbooks/_index.md"
    assert context["playbook_recall"]["recalled"] is False
    assert context["investigation_hints"]
    assert "knowledge_candidates" in context
    assert "PLAYBOOK_RECALL_MISSING" in context["quality_flags"]
    assert "PLAYBOOK_NOT_APPLIED" in context["quality_flags"]


def test_action_plan_injects_recalled_playbook_context_when_available(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户提供截图，页面提示校验失败，手机号 15921195068", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file, category="entrypoint", name="screenshot_keyword", value="页面提示校验失败", source="用户截图")
    recalled = run_playbook_recall(state_file, match="screenshot-or-keyword-to-runtime-logs")
    assert recalled.returncode == 0, recalled.stderr

    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "manual",
        "--source",
        "用户截图",
        "--objective",
        "根据截图关键字查当时调用日志",
        "--success-criteria",
        "action 自动携带 playbook 召回上下文",
        "--playbook",
        "screenshot-or-keyword-to-runtime-logs",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    context = json.loads(planned.stdout)["action"]["context"]
    assert context["playbook_recall"]["matched"] == ["screenshot-or-keyword-to-runtime-logs"]
    assert context["quality_flags"] == []


def test_next_json_includes_lightweight_health_summary(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)
    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "A1",
        "--track",
        "manual",
        "--source",
        "用户补充",
        "--objective",
        "确认用户端操作路径",
        "--success-criteria",
        "用户确认 App 切换支付方式后礼品卡消失",
    )
    assert planned.returncode == 0, planned.stderr

    result = run_cli("next", "--state-file", str(state_file), "--json")

    assert result.returncode == 0, result.stderr
    health = json.loads(result.stdout)["next"]["health"]
    assert health["pending_actions"] == 1
    assert health["scene_facts"] == 1
    assert "pending_actions" in health["quality_flags"]


def test_next_task_card_recommends_log_plan_for_screenshot_keyword(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户提供截图，页面提示校验失败，手机号 15921195068", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file, category="entrypoint", name="screenshot_keyword", value="页面提示校验失败", source="用户截图")

    result = run_cli("next", "--state-file", str(state_file), "--json")

    assert result.returncode == 0, result.stderr
    task = json.loads(result.stdout)["next"]["task"]
    assert task["task_type"] == "sls_plan"
    assert task["playbook"] == "screenshot-or-keyword-to-runtime-logs"
    assert "anchor" in task["required_inputs"]
    assert "time_range" in task["required_inputs"]
    assert "查当时真实调用" in task["rationale"]


def test_next_task_card_recommends_change_check_for_direct_failure(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "某把枪突然充电校验失败，手机号 15921195068", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file, category="object", name="gun_tcp", value="枪 TCP 连不上网关", source="SLS")
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "sls",
        "--summary",
        "日志显示 TCP 连不上网关",
        "--kind",
        "log",
        "--strength",
        "strong",
    )

    result = run_cli("next", "--state-file", str(state_file), "--json")

    assert result.returncode == 0, result.stderr
    task = json.loads(result.stdout)["next"]["task"]
    assert task["task_type"] == "change_check"
    assert task["playbook"] == "direct-failure-to-change-root-cause"
    assert "change record" in task["suggested_commands"][0]
    assert "recent_change" in task["quality_flags"]


def test_sls_generic_keywords_can_be_configured_by_environment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("COMPASS_SLS_GENERIC_KEYWORDS", "payment-ways-v2")
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)

    blocked = run_cli(
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

    assert blocked.returncode == 1
    assert "payment-ways-v2" in json.loads(blocked.stdout)["error"]


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
    run_scene_fact(state_file)
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
    run_scene_fact(state_file)

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
        "--input",
        "anchor=15921195068",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--json",
    )

    assert sls_missing_time.returncode == 1
    assert "track sls 缺少 gate 字段：keyword_source" in json.loads(sls_missing_time.stdout)["error"]

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
    assert "input.explain_text" in json.loads(sql_missing_explain.stdout)["error"]


def test_sls_action_plan_defaults_time_range_to_seven_days(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)

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
        "用户未提供时间时按默认一周查日志",
        "--success-criteria",
        "生成带默认时间窗的 SLS action",
        "--input",
        "query=15921195068",
        "--input",
        "anchor=15921195068",
        "--gate",
        "type=sls",
        "--gate",
        "status=passed",
        "--gate",
        "keyword_source=none",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["action"]["input"]["time_range"] == "-7d"


def test_non_prod_sls_gate_can_be_relaxed_by_environment_switch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("COMPASS_NON_PROD_RELAX_GATES", "1")
    state_file = tmp_path / "session.json"
    run_cli("start", "uat 用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)

    relaxed = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SLSUAT",
        "--track",
        "sls",
        "--source",
        "SLS-UAT",
        "--objective",
        "在 UAT 查询宽松日志关键词",
        "--success-criteria",
        "命中测试日志即可",
        "--input",
        "query=异常 支付",
        "--input",
        "time_range=2026-04-25 16:40~17:10",
        "--input",
        "env=uat",
        "--gate",
        "type=sls",
        "--json",
    )

    assert relaxed.returncode == 0, relaxed.stderr
    action = json.loads(relaxed.stdout)["action"]
    assert action["gate"]["policy"] == "relaxed_non_prod"
    assert action["gate"]["env"] == "uat"


def test_non_prod_gate_switch_does_not_relax_prod_sls(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("COMPASS_NON_PROD_RELAX_GATES", "1")
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)

    blocked = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SLSPROD",
        "--track",
        "sls",
        "--source",
        "SLS",
        "--objective",
        "生产日志仍必须有实体锚点",
        "--success-criteria",
        "不能绕过生产门禁",
        "--input",
        "query=异常 支付",
        "--input",
        "time_range=2026-04-25 16:40~17:10",
        "--gate",
        "type=sls",
        "--json",
    )

    assert blocked.returncode == 1
    assert "缺少 input 字段：anchor" in json.loads(blocked.stdout)["error"]


def test_action_plan_accepts_valid_track_specific_fields(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)

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
    run_scene_fact(state_file, name="charge_start", value="预付款启动充电", source="用户问题")

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
    run_scene_fact(state_file)

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
    run_scene_fact(state_file)

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
    run_planned_action(
        state_file,
        source="SLS",
        summary="用户手机号 15921195068，token=abc-secret-token",
        findings=["phone=15921195068"],
        supports="H2",
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
    run_planned_action(
        state_file,
        summary="财务返回礼品卡",
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
    added = run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "SLS",
        "--summary",
        "财务返回礼品卡",
        "--supports",
        "H2",
        "--json",
    )
    assert added.returncode == 0, added.stderr

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
    assert "假设必须引用至少一个 scene fact / evidence / change" in json.loads(blocked.stdout)["error"]


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
    assert "action plan" in payload["next"]["next_actions"]
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
    run_planned_action(
        state_file,
        summary="财务返回礼品卡，guan-zhong 最终响应无礼品卡",
        supports="H2",
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
    assert state["schema_version"] == 2
    assert state["scene_facts"] == []
    assert state["action_history"] == []
    assert state["applicable_knowledge"] == []
    assert state["changes"] == []
    assert state["pending_confirmations"] == []


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
    assert persisted["schema_version"] == 2
    assert persisted["scene_facts"] == []
    assert persisted["action_history"] == []
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
    assert payload["state"]["schema_version"] == 2


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
    run_planned_action(
        state_file,
        summary="财务返回礼品卡，guan-zhong 最终响应无礼品卡",
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
    assert "strategy_review" not in state
    assert state["conclusion_history"][0]["status"] == "superseded"
    assert state["conclusion_history"][0]["reopen_reason"] == "用户补充微信小程序可用，需要修订 App 端影响范围"
    assert state["conclusion_history"][0]["strategy_review"]["status"] == "pending"

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


_EXPLAIN_LOW_RISK = (
    "0:VOlapScanNode(204)\n"
    "TABLE: t_pay\n"
    "PREDICATES: ((phone = '15921195068'))\n"
    "partitions=1/1\n"
    "tablets=1/1\n"
    "cardinality=1200, avgRowSize=0.0, numNodes=1\n"
)

_EXPLAIN_HIGH_RISK = (
    "0:VOlapScanNode(211)\n"
    "TABLE: ods_finance_cdc.ods_finance_d_t_third_pay_info\n"
    "PREDICATES: ((flow_number = '20260413234173136502786'))\n"
    "partitions=1/69 (p202604)\n"
    "tablets=3/3\n"
    "cardinality=2470577, avgRowSize=0.0, numNodes=1\n"
)


def _start_sql_session(tmp_path: Path) -> Path:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户礼品卡不展示，手机号 15921195068，今天下午", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_scene_fact(state_file)
    return state_file


def test_sql_plan_blocks_high_risk_until_action_confirm(tmp_path: Path) -> None:
    state_file = _start_sql_session(tmp_path)

    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SQLH",
        "--track",
        "sql",
        "--source",
        "Doris",
        "--objective",
        "查询三方支付明细",
        "--success-criteria",
        "拿到第三方流水",
        "--input",
        "sql=select * from ods_finance_cdc.ods_finance_d_t_third_pay_info where flow_number='20260413234173136502786'",
        "--input",
        "env=prod",
        "--input",
        f"explain_text={_EXPLAIN_HIGH_RISK}",
        "--gate",
        "type=sql",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["action"]["status"] == "requires_confirmation"
    assert payload["action"]["gate"]["risk"] == "high"
    assert payload["action"]["gate"]["status"] == "blocked"
    pendings = payload["state"].get("pending_confirmations") or []
    assert any(item.get("action_id") == "SQLH" for item in pendings)

    blocked_complete = run_cli(
        "action",
        "complete",
        "--state-file",
        str(state_file),
        "--action-id",
        "SQLH",
        "--summary",
        "查询结果",
        "--json",
    )
    assert blocked_complete.returncode == 1
    assert "requires_confirmation" in json.loads(blocked_complete.stdout)["error"] or "待确认" in json.loads(blocked_complete.stdout)["error"]

    confirmed = run_cli(
        "action",
        "confirm",
        "--state-file",
        str(state_file),
        "--action-id",
        "SQLH",
        "--note",
        "已与 DBA 评估，分区已限定",
        "--json",
    )
    assert confirmed.returncode == 0, confirmed.stderr
    confirmed_payload = json.loads(confirmed.stdout)
    assert confirmed_payload["action"]["status"] == "planned"
    assert not confirmed_payload["state"].get("pending_confirmations")

    completed = run_cli(
        "action",
        "complete",
        "--state-file",
        str(state_file),
        "--action-id",
        "SQLH",
        "--summary",
        "三方支付明细已查到",
        "--json",
    )
    assert completed.returncode == 0, completed.stderr


def test_sql_plan_passes_low_risk_without_confirmation(tmp_path: Path) -> None:
    state_file = _start_sql_session(tmp_path)

    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SQLL",
        "--track",
        "sql",
        "--source",
        "Doris",
        "--objective",
        "查询单条支付记录",
        "--success-criteria",
        "命中订单",
        "--input",
        "sql=select * from t_pay where phone='15921195068'",
        "--input",
        "env=prod",
        "--input",
        f"explain_text={_EXPLAIN_LOW_RISK}",
        "--gate",
        "type=sql",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["action"]["status"] == "planned"
    assert payload["action"]["gate"]["status"] == "passed"
    assert payload["action"]["gate"]["risk"] == "low"
    assert payload["action"]["gate"]["rows"] == "1200"
    assert not payload["state"].get("pending_confirmations")


def test_sql_plan_skips_explain_in_test_environment(tmp_path: Path) -> None:
    state_file = _start_sql_session(tmp_path)

    planned = run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SQLT",
        "--track",
        "sql",
        "--source",
        "MySQL",
        "--objective",
        "uat 环境校验表结构",
        "--success-criteria",
        "拿到字段定义",
        "--input",
        "sql=select 1 from t_pay limit 1",
        "--input",
        "env=uat",
        "--gate",
        "type=sql",
        "--json",
    )

    assert planned.returncode == 0, planned.stderr
    payload = json.loads(planned.stdout)
    assert payload["action"]["status"] == "planned"
    assert payload["action"]["gate"]["risk"] == "low"
    assert payload["action"]["input"]["env"] == "uat"


def test_action_confirm_rejects_when_no_pending_risk(tmp_path: Path) -> None:
    state_file = _start_sql_session(tmp_path)

    run_cli(
        "action",
        "plan",
        "--state-file",
        str(state_file),
        "--action-id",
        "SQLOK",
        "--track",
        "sql",
        "--source",
        "Doris",
        "--objective",
        "低风险查询",
        "--success-criteria",
        "命中目标",
        "--input",
        "sql=select * from t_pay where phone='15921195068'",
        "--input",
        "env=prod",
        "--input",
        f"explain_text={_EXPLAIN_LOW_RISK}",
        "--gate",
        "type=sql",
    )

    bogus = run_cli(
        "action",
        "confirm",
        "--state-file",
        str(state_file),
        "--action-id",
        "SQLOK",
        "--note",
        "尝试无脑解锁",
        "--json",
    )
    assert bogus.returncode == 1
    assert "没有待确认" in json.loads(bogus.stdout)["error"]


# ============================================================================
# 以下测试覆盖 v4 新增能力：KB Learn / Change / Timeline / 反思警告 / Falsifiable / mitigation 拆分
# ============================================================================


def test_kb_learn_persists_and_suggest_recalls_top_n(tmp_path: Path) -> None:
    """录入若干条知识后，suggest 能按相关度返回 top-N。"""

    kb_file = tmp_path / "kb.yaml"
    run_cli(
        "kb",
        "learn",
        "--statement",
        "C 端订单号是 19 位数字，前 14 位为 yyyyMMddHHmmss",
        "--tag",
        "order",
        "--tag",
        "id-rule",
        "--knowledge-file",
        str(kb_file),
    )
    run_cli(
        "kb",
        "learn",
        "--statement",
        "OR 开头的短订单号是 B 端 mock 数据",
        "--tag",
        "order",
        "--tag",
        "mock",
        "--knowledge-file",
        str(kb_file),
    )
    result = run_cli(
        "kb",
        "suggest",
        "--query",
        "用户订单号 19 位",
        "--top",
        "5",
        "--knowledge-file",
        str(kb_file),
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    matches = payload["matches"]
    assert len(matches) >= 1
    assert matches[0]["id"] == "K001"
    assert matches[0]["score"] > matches[-1]["score"] - 1e-6


def test_kb_learn_rejects_overlong_statement(tmp_path: Path) -> None:
    kb_file = tmp_path / "kb.yaml"
    long_statement = "占位" * 200
    result = run_cli(
        "kb",
        "learn",
        "--statement",
        long_statement,
        "--knowledge-file",
        str(kb_file),
        "--json",
    )
    assert result.returncode == 1
    assert "超过上限" in json.loads(result.stdout)["error"]


def test_change_record_then_list_round_trip(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "用户 15921195068 礼品卡不展示", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    record = run_cli(
        "change",
        "record",
        "--state-file",
        str(state_file),
        "--type",
        "deploy",
        "--target",
        "order-server@v1.2.3",
        "--description",
        "上线 v1.2.3，含 SQL DDL",
        "--event-at",
        "2026-04-29 13:30",
        "--source",
        "jenkins-#1234",
        "--json",
    )
    assert record.returncode == 0, record.stderr
    payload = json.loads(record.stdout)
    assert payload["change"]["id"] == "C1"
    assert payload["change"]["change_type"] == "deploy"

    listed = run_cli("change", "list", "--state-file", str(state_file), "--json")
    assert listed.returncode == 0
    listed_payload = json.loads(listed.stdout)
    assert listed_payload["count"] == 1
    assert listed_payload["changes"][0]["target"] == "order-server@v1.2.3"


def test_change_record_rejects_unknown_type(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "礼品卡不展示", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    result = run_cli(
        "change",
        "record",
        "--state-file",
        str(state_file),
        "--type",
        "magic",
        "--target",
        "x",
        "--description",
        "y",
        "--event-at",
        "2026-04-29 13:30",
        "--json",
    )
    assert result.returncode == 1
    assert "未知 change_type" in json.loads(result.stdout)["error"]


def test_timeline_orders_changes_and_facts_chronologically(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "礼品卡不展示", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "user_complaint",
        "--value",
        "首次报障",
        "--source",
        "工单",
        "--event-at",
        "2026-04-29 14:00",
    )
    run_cli(
        "change",
        "record",
        "--state-file",
        str(state_file),
        "--type",
        "deploy",
        "--target",
        "order-server@v1.2.3",
        "--description",
        "上线",
        "--event-at",
        "2026-04-29 13:30",
    )
    result = run_cli("timeline", "--state-file", str(state_file), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    timeline = payload["timeline"]
    assert len(timeline) == 2
    assert timeline[0]["kind"] == "change"
    assert timeline[1]["kind"] == "scene_fact"


def test_scene_fact_diff_requires_comparison_keyword(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "礼品卡不展示", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    bad = run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "diff",
        "--name",
        "balance_state",
        "--value",
        "balance is 0",
        "--source",
        "DB",
        "--json",
    )
    assert bad.returncode == 1
    assert "对比性" in json.loads(bad.stdout)["error"]

    good = run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "diff",
        "--name",
        "balance_state",
        "--value",
        "故障时余额=0，正常时应为 100，差异为 -100",
        "--source",
        "DB",
        "--json",
    )
    assert good.returncode == 0


def test_hypothesis_falsifiable_field_persists(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "礼品卡不展示", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "k",
        "--value",
        "v",
        "--source",
        "src",
    )
    result = run_cli(
        "hypothesis",
        "add",
        "--state-file",
        str(state_file),
        "--id",
        "H1",
        "--statement",
        "缓存击穿导致余额展示为 0",
        "--source-fact",
        "k",
        "--falsifiable",
        "如果 Redis 在故障窗口期 TTL 未过期则该假设不成立",
        "--json",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    h = next(h for h in payload["state"]["hypotheses"] if h["id"] == "H1")
    assert "falsifiable" in h
    assert "TTL" in h["falsifiable"]


def test_conclude_quality_warnings_for_high_confidence_without_strong_evidence(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "礼品卡不展示", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "k",
        "--value",
        "v",
        "--source",
        "src",
    )
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "manual-note",
        "--summary",
        "凭经验觉得是缓存问题",
        "--kind",
        "manual",
        "--strength",
        "weak",
    )
    res = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "Redis 缓存导致余额展示为 0",
        "--evidence",
        "E1",
        "--confidence",
        "high",
        "--what",
        "余额查询返回 0",
        "--where",
        "wallet-server WalletServiceImpl#getBalance 第3层调用",
        "--when",
        "2026-04-29 14:32 持续 3 分钟",
        "--why-technical",
        "Redis TTL 过期导致缓存击穿到 DB",
        "--why-business",
        "用户充值后立即刷新页面",
        "--blast-radius",
        "影响 1 人",
        "--how",
        "用户刷新 → Redis 过期 → DB 未更新 → 返回 0",
        "--inference-chain",
        "Redis 过期 → 余额为 0",
        "--json",
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    warnings = payload["state"]["conclusion"]["quality_warnings"]
    codes = {w["code"] for w in warnings}
    assert "CONF_GATE" in codes
    assert "NO_MITIGATION" in codes
    assert "NO_REMEDIATION" in codes


def test_conclude_warns_when_direct_failure_has_no_change_evidence(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "某把枪突然充电校验失败", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "object",
        "--name",
        "gun",
        "--value",
        "单枪充电校验失败",
        "--source",
        "用户问题",
    )
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "sls",
        "--summary",
        "日志显示枪 TCP 连接连不上网关",
        "--kind",
        "log",
        "--strength",
        "strong",
    )

    res = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "充电校验失败是因为枪 TCP 连接连不上网关",
        "--evidence",
        "E1",
        "--confidence",
        "medium",
        "--what",
        "单枪充电校验失败",
        "--where",
        "charge-server GunGatewayService#validateBeforeCharge 到 gateway-tcp 链路",
        "--when",
        "2026-04-29 14:32 开始",
        "--why-technical",
        "枪 TCP 连接连不上网关导致校验失败",
        "--why-business",
        "用户发起充电校验",
        "--blast-radius",
        "影响单把枪",
        "--how",
        "用户发起充电 → 枪连接网关失败 → 校验失败",
        "--inference-chain",
        "SLS 日志显示 TCP 连不上网关 → 因链路不可达 → 导致充电校验失败",
        "--mitigation",
        "先切回可达网关或通知运维恢复连接",
        "--remediation",
        "补充网关变更校验和配置同步检查",
        "--json",
    )

    assert res.returncode == 0, res.stderr
    warnings = json.loads(res.stdout)["state"]["conclusion"]["quality_warnings"]
    codes = {w["code"] for w in warnings}
    assert "HALF_ROOT_CAUSE" in codes


def test_conclude_with_mitigation_and_remediation_persists(tmp_path: Path) -> None:
    state_file = tmp_path / "session.json"
    run_cli("start", "礼品卡不展示", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "k",
        "--value",
        "v",
        "--source",
        "src",
    )
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "sls",
        "--summary",
        "支付回调日志缺失",
        "--kind",
        "log",
        "--strength",
        "strong",
    )
    res = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "支付回调消息丢失",
        "--evidence",
        "E1",
        "--confidence",
        "high",
        "--what",
        "支付回调未推进订单",
        "--where",
        "order-server OrderCallbackServiceImpl#onPaySuccess 第4层",
        "--when",
        "2026-04-29 14:32 持续 3 分钟",
        "--why-technical",
        "MQ 消息丢失，消费方未收到",
        "--why-business",
        "用户充值后未到账",
        "--blast-radius",
        "影响 50 人",
        "--how",
        "支付成功 → MQ 发送丢失 → 订单状态未推进 → 用户未到账",
        "--inference-chain",
        "支付回调日志 E1 → 因 MQ 丢失 → 触发余额为 0",
        "--mitigation",
        "立即补发对账消息",
        "--remediation",
        "MQ 增加幂等并接入告警",
        "--unsolved",
        "为何同时段其他订单未受影响",
        "--pattern-scan",
        "充电订单同链路是否也丢消息",
        "--json",
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    conc = payload["state"]["conclusion"]
    assert conc["mitigation"][0]["description"] == "立即补发对账消息"
    assert conc["remediation"][0]["description"] == "MQ 增加幂等并接入告警"
    assert conc["unsolved"] == ["为何同时段其他订单未受影响"]
    assert conc["pattern_scan"] == ["充电订单同链路是否也丢消息"]
    codes = {w["code"] for w in conc["quality_warnings"]}
    assert "CONF_GATE" not in codes
    assert "NO_MITIGATION" not in codes
    assert "NO_REMEDIATION" not in codes


def _setup_minimal_session(tmp_path: Path) -> Path:
    """快速构造一个进入 evidence_collecting 阶段、含 1 条强证据的会话。"""

    state_file = tmp_path / "session.json"
    run_cli("start", "支付回调丢失导致订单不到账", "--state-file", str(state_file))
    run_cli("confirm", "--state-file", str(state_file), "--mode", "auto")
    run_cli(
        "scene",
        "fact",
        "--state-file",
        str(state_file),
        "--category",
        "entrypoint",
        "--name",
        "trigger",
        "--value",
        "支付成功后未推进订单",
        "--source",
        "用户反馈",
    )
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "sls",
        "--summary",
        "支付回调日志缺失",
        "--kind",
        "log",
        "--strength",
        "strong",
    )
    return state_file


def test_conclude_renders_tldr_severity_and_mttr(tmp_path: Path) -> None:
    state_file = _setup_minimal_session(tmp_path)
    res = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "MQ 丢消息导致回调未触发，订单未推进",
        "--evidence",
        "E1",
        "--confidence",
        "high",
        "--what",
        "支付回调链路丢消息",
        "--where",
        "order-server consume queue",
        "--when",
        "2026-04-29 13:30 前后",
        "--why-technical",
        "MQ 节点 GC 抖动期间消息未正确 ACK",
        "--why-business",
        "用户支付成功后短时间内订单未推进",
        "--blast-radius",
        "影响 50 名用户的订单状态推进",
        "--how",
        "支付回调 → MQ 丢失 → 订单未推进 → 用户未到账",
        "--inference-chain",
        "支付回调日志 E1 → 因 MQ 丢失 → 触发余额为 0",
        "--mitigation",
        "立即补发对账消息",
        "--remediation-item",
        "desc=MQ 加幂等并接入告警;owner=@team-mq;due=2026-05-15;status=planned",
        "--tldr",
        "MQ 丢消息致 50 名用户订单未推进，已补发对账消息止血。",
        "--severity",
        "sev2",
        "--detected-at",
        "2026-04-29T13:30:00+08:00",
        "--acknowledged-at",
        "2026-04-29T13:35:00+08:00",
        "--mitigated-at",
        "2026-04-29T13:50:00+08:00",
        "--resolved-at",
        "2026-04-29T15:30:00+08:00",
        "--json",
    )
    assert res.returncode == 0, res.stderr
    conc = json.loads(res.stdout)["state"]["conclusion"]
    assert conc["tldr"].startswith("MQ 丢消息")
    assert conc["severity"] == "sev2"
    timing = conc["timing"]
    assert timing["mttd_minutes"] == 5
    assert timing["mttm_minutes"] == 15
    assert timing["mttr_minutes"] == 120
    assert conc["remediation"][0]["owner"] == "@team-mq"
    assert conc["remediation"][0]["due"] == "2026-05-15"
    rep = run_cli("report", "--state-file", str(state_file), "--audience", "technical")
    assert rep.returncode == 0
    out = rep.stdout
    assert "TL;DR" in out
    assert "MTTR" in out
    assert "🟠 SEV2" in out


def test_technical_report_renders_conclusion_timeline_before_root_cause(tmp_path: Path) -> None:
    state_file = _setup_minimal_session(tmp_path)
    run_cli(
        "change",
        "record",
        "--state-file",
        str(state_file),
        "--type",
        "deploy",
        "--target",
        "order-server@v1.2.3",
        "--description",
        "上线 MQ 客户端升级",
        "--event-at",
        "2026-04-29T13:00:00+08:00",
    )
    run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "sls",
        "--summary",
        "13:30 后开始出现回调日志缺失",
        "--kind",
        "log",
        "--strength",
        "strong",
        "--event-at",
        "2026-04-29T13:30:00+08:00",
    )
    res = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "MQ 客户端升级后 ACK 异常导致订单未推进",
        "--evidence",
        "E1",
        "--evidence",
        "E2",
        "--confidence",
        "high",
        "--what",
        "支付回调消息丢失",
        "--where",
        "order-server consume queue",
        "--when",
        "2026-04-29 13:30 前后",
        "--why-technical",
        "MQ 客户端升级后 ACK 异常",
        "--why-business",
        "用户支付后订单未推进",
        "--blast-radius",
        "影响 50 名用户",
        "--how",
        "支付回调 → MQ ACK 异常 → 订单未推进",
        "--inference-chain",
        "C1 变更 → E2 日志缺失 → E1 用户反馈",
        "--mitigation",
        "补发对账消息",
        "--remediation",
        "回滚 MQ 客户端并补充 ACK 告警",
        "--detected-at",
        "2026-04-29T13:30:00+08:00",
        "--acknowledged-at",
        "2026-04-29T13:35:00+08:00",
        "--mitigated-at",
        "2026-04-29T13:50:00+08:00",
        "--resolved-at",
        "2026-04-29T15:30:00+08:00",
    )
    assert res.returncode == 0, res.stderr

    report = run_cli("report", "--state-file", str(state_file), "--audience", "technical")
    assert report.returncode == 0, report.stderr
    text = report.stdout
    assert "## 结论时间线" in text
    assert text.index("## 结论时间线") < text.index("## 排查结论")
    assert "发现/检测" in text
    assert "开始响应" in text
    assert "完成止血" in text
    assert "问题恢复" in text
    assert "C1" in text
    assert "E2" in text


def test_conclude_warns_on_too_long_tldr(tmp_path: Path) -> None:
    state_file = _setup_minimal_session(tmp_path)
    long_tldr = "句子一。句子二。句子三！句子四？"
    res = run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "MQ 丢消息致回调未触发，订单未推进",
        "--evidence",
        "E1",
        "--confidence",
        "medium",
        "--what",
        "支付回调消息丢失",
        "--where",
        "order-server consume queue",
        "--when",
        "2026-04-29 13:30 前后",
        "--why-technical",
        "MQ 节点 GC 抖动期间消息未正确 ACK",
        "--why-business",
        "用户支付成功后订单未推进",
        "--blast-radius",
        "影响 50 名用户的订单状态推进",
        "--how",
        "支付回调 → MQ 丢失 → 订单未推进",
        "--inference-chain",
        "支付回调日志 E1 → MQ 丢失 → 订单未推进",
        "--mitigation",
        "立即补发对账消息",
        "--remediation-item",
        "desc=MQ 加幂等;owner=@team-mq",
        "--tldr",
        long_tldr,
        "--json",
    )
    assert res.returncode == 0, res.stderr
    codes = {w["code"] for w in json.loads(res.stdout)["state"]["conclusion"]["quality_warnings"]}
    assert "TLDR_TOO_LONG" in codes


def test_evidence_change_link_and_timeline(tmp_path: Path) -> None:
    state_file = _setup_minimal_session(tmp_path)
    run_cli(
        "change",
        "record",
        "--state-file",
        str(state_file),
        "--type",
        "deploy",
        "--target",
        "order-server@v1.2.3",
        "--description",
        "上线 v1.2.3 包含 MQ 客户端升级",
        "--event-at",
        "2026-04-29T13:00:00+08:00",
    )
    res = run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "sls",
        "--summary",
        "上线后开始出现回调日志缺失",
        "--kind",
        "log",
        "--strength",
        "strong",
        "--event-at",
        "2026-04-29T13:30:00+08:00",
        "--change",
        "C1",
        "--json",
    )
    assert res.returncode == 0, res.stderr
    ev = json.loads(res.stdout)["evidence"]
    assert ev["change_ids"] == ["C1"]

    tl = run_cli("timeline", "--state-file", str(state_file), "--json")
    assert tl.returncode == 0
    timeline = json.loads(tl.stdout)["timeline"]
    evidence_entry = next(e for e in timeline if e["kind"] == "evidence")
    assert evidence_entry["related_changes"] == ["C1"]


def test_evidence_change_link_rejects_unknown_change(tmp_path: Path) -> None:
    state_file = _setup_minimal_session(tmp_path)
    res = run_cli(
        "evidence",
        "add",
        "--state-file",
        str(state_file),
        "--source",
        "sls",
        "--summary",
        "无效的关联",
        "--kind",
        "log",
        "--strength",
        "medium",
        "--change",
        "C99",
        "--json",
    )
    assert res.returncode == 1
    assert "引用的变更不存在" in json.loads(res.stdout)["error"]


def test_action_card_renders_explain_text_block(tmp_path: Path) -> None:
    """模拟 action_history 含 explain_text 时，Action Card 用 fenced 代码块独立渲染。"""

    state_file = _setup_minimal_session(tmp_path)

    import yaml as _yaml

    with state_file.open("r", encoding="utf-8") as f:
        state = _yaml.safe_load(f) or {}
    state.setdefault("action_history", []).append(
        {
            "action_id": "demo-sql",
            "track": "sql",
            "source": "manual",
            "input": {"sql": "select 1", "explain_text": "id|select_type|table\n1|SIMPLE|t_user"},
            "gate": {"type": "sql", "status": "passed", "risk": "low", "explain_text": "id|select_type|table\n1|SIMPLE|t_user"},
            "output": {"summary": "EXPLAIN 通过", "findings": [], "leads": {}, "elapsed_ms": 10, "evidence_id": "E1"},
        }
    )
    state.setdefault("evidence", [])
    if not any(e.get("id") == "E1" for e in state["evidence"]):
        state["evidence"].append({"id": "E1", "source": "sls", "summary": "占位证据", "kind": "log", "strength": "medium", "created_at": "2026-04-29T13:30:00+08:00"})
    with state_file.open("w", encoding="utf-8") as f:
        _yaml.safe_dump(state, f, allow_unicode=True)

    rep = run_cli("report", "--state-file", str(state_file), "--audience", "technical")
    assert rep.returncode == 0, rep.stderr
    assert "EXPLAIN 原文（可直接复制回贴）" in rep.stdout
    assert "```text" in rep.stdout
    assert "SIMPLE|t_user" in rep.stdout


def test_report_postmortem_audience_renders_section_headings(tmp_path: Path) -> None:
    state_file = _setup_minimal_session(tmp_path)
    run_cli(
        "conclude",
        "--state-file",
        str(state_file),
        "--conclusion",
        "MQ 丢消息导致订单未推进",
        "--evidence",
        "E1",
        "--confidence",
        "medium",
        "--what",
        "支付回调消息丢失",
        "--where",
        "order-server consume queue",
        "--when",
        "2026-04-29 13:30 前后",
        "--why-technical",
        "MQ 未正确 ACK",
        "--why-business",
        "用户支付后订单未推进",
        "--blast-radius",
        "影响 50 名用户",
        "--how",
        "支付回调 → MQ 丢失 → 订单未推进",
        "--inference-chain",
        "E1 → MQ 丢失 → 订单未推进",
        "--mitigation",
        "补发对账消息",
        "--remediation-item",
        "desc=MQ 加固;owner=@team-mq;due=2026-06-01;status=planned",
        "--tldr",
        "简述一句。两句。第三句以内。",
        "--severity",
        "sev3",
        "--detected-at",
        "2026-04-29T13:30:00+08:00",
        "--acknowledged-at",
        "2026-04-29T13:40:00+08:00",
    )
    out = run_cli("report", "--audience", "postmortem", "--state-file", str(state_file))
    assert out.returncode == 0, out.stderr
    text = out.stdout
    assert "Postmortem · 事故复盘" in text
    assert "## 一、" in text and "Executive Summary" in text
    assert "## 二、" in text and "Impact" in text
    assert "## 九、" in text and "References" in text
    assert "## 十、" in text and "Timeline" in text
