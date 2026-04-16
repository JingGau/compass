from __future__ import annotations

import unittest

from tools.action_cards import (
    ActionResult,
    InvestigationAction,
    SafetyGateResult,
    build_pending_confirmation,
    render_after_card,
    render_before_card,
    render_safety_gate_card,
    should_execute,
)


class ActionCardsTest(unittest.TestCase):
    def test_sql_before_card_prints_exact_sql(self) -> None:
        action = InvestigationAction(
            step_id="step-5",
            title="SQL 核验账号用户类型",
            track="sql",
            purpose="确认账号是否被用户财务列表过滤条件排除",
            tool="platform",
            environment="prod",
            target={
                "sql": "SELECT user_id, user_account FROM t_user WHERE user_account = '13266525252'",
            },
            expected="拿到 user_type / is_channel",
        )

        card = render_before_card(action)

        self.assertIn("▶ Step step-5 — SQL 核验账号用户类型", card)
        self.assertIn("将执行 SQL", card)
        self.assertIn("SELECT user_id, user_account FROM t_user", card)
        self.assertIn("成功标准", card)

    def test_code_before_card_prints_apps_and_methods(self) -> None:
        action = InvestigationAction(
            step_id="step-2",
            title="代码轨定位用户财务入口",
            track="code",
            purpose="确认页面点击查询后调用哪个后端接口",
            tool="code",
            environment="local",
            target={
                "applications": ["omp-shop", "finance_server", "base_server"],
                "methods": [
                    "UserFinanceList.vue#getData",
                    "UserFinanceDriverController#list",
                    "FinanceMapper.queryUserList",
                ],
            },
            expected="拿到接口路径、服务方法、Mapper、表名和过滤条件",
        )

        card = render_before_card(action)

        self.assertIn("应用：omp-shop → finance_server → base_server", card)
        self.assertIn("UserFinanceList.vue#getData", card)
        self.assertIn("FinanceMapper.queryUserList", card)

    def test_high_risk_gate_renders_confirmation_and_blocks_execution(self) -> None:
        action = InvestigationAction(
            step_id="step-6",
            title="SQL 核验",
            track="sql",
            purpose="确认数据状态",
            tool="platform",
            environment="prod",
            target={"sql": "SELECT * FROM big_table"},
            expected="返回目标行",
        )
        gate = SafetyGateResult(
            gate_type="sql",
            status="blocked",
            risk_level="high",
            summary="预估扫描约 247 万行",
            details={"rows": 2470577, "reason": "超过 100 万行"},
            requires_confirmation=True,
        )

        card = render_safety_gate_card(action, gate)

        self.assertFalse(should_execute(gate))
        self.assertIn("🔴", card)
        self.assertIn("确认执行", card)
        self.assertIn("我来改写 SQL", card)
        self.assertIn("跳过此步", card)
        self.assertIn("明确回复「确认执行」", card)
        pending = build_pending_confirmation(action, gate)
        self.assertEqual(pending["action_id"], "step-6")
        self.assertEqual(pending["risk_level"], "high")

    def test_sls_after_card_lists_leads_and_next_options(self) -> None:
        action = InvestigationAction(
            step_id="step-3",
            title="SLS 搜索用户财务接口日志",
            track="sls",
            purpose="确认账号查询是否打到后端",
            tool="sls",
            environment="prod",
            target={"query": "13266525252 AND /userFinance/driverFinance/list", "limit": 50},
            expected="命中请求日志并提取 traceId",
        )
        result = ActionResult(
            status="success",
            elapsed_ms=1200,
            summary="SLS 命中 18 条，全量载入 18 条",
            key_findings=[
                "接口：/userFinance/driverFinance/list",
                "服务：finance-server → base-server",
            ],
            leads={
                "trace_ids": ["abc123"],
                "interfaces": ["/userFinance/driverFinance/list"],
                "methods": ["UserFinanceDriverController#list"],
                "tables": ["base_s_t_charging_user"],
            },
            next_actions=[
                "用 traceId 拉全链路日志",
                "根据接口读 Controller/Service 代码",
                "根据请求参数模拟 SQL 过滤条件",
            ],
        )

        card = render_after_card(action, result)

        self.assertIn("✅ Step step-3 完成", card)
        self.assertIn("SLS 命中 18 条", card)
        self.assertIn("traceId：abc123", card)
        self.assertIn("接口：/userFinance/driverFinance/list", card)
        self.assertIn("表：base_s_t_charging_user", card)
        self.assertIn("可继续下钻", card)


if __name__ == "__main__":
    unittest.main()

