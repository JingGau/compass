from __future__ import annotations

import unittest

from tools.action_cards import ActionResult
from tools.evidence_graph import EvidenceGraph


class EvidenceGraphTest(unittest.TestCase):
    def test_records_page_to_api_to_method_to_table(self) -> None:
        graph = EvidenceGraph()

        graph.link("page", "UserFinanceList.vue", "api", "/userFinance/driverFinance/list", "calls")
        graph.link(
            "api",
            "/userFinance/driverFinance/list",
            "method",
            "UserFinanceDriverController#list",
            "handled_by",
        )
        graph.link(
            "method",
            "UserFinanceDriverController#list",
            "table",
            "base_s_t_charging_user",
            "reads",
        )

        exported = graph.to_dict()

        self.assertEqual(len(exported["nodes"]), 4)
        self.assertEqual(len(exported["edges"]), 3)
        self.assertIn(
            {
                "from": "api:/userFinance/driverFinance/list",
                "to": "method:UserFinanceDriverController#list",
                "relation": "handled_by",
            },
            exported["edges"],
        )

    def test_adds_leads_from_action_result(self) -> None:
        graph = EvidenceGraph()
        result = ActionResult(
            status="success",
            elapsed_ms=100,
            summary="命中日志",
            key_findings=[],
            leads={
                "interfaces": ["/online/queryOnlineRechargeForPage"],
                "methods": ["OnlineRechargeOrRefundController#queryOnlineRechargeForPage"],
                "tables": ["finance_d_t_third_pay_info"],
                "trace_ids": ["trace-1"],
            },
            next_actions=[],
        )

        graph.add_result_leads("step-1", result)
        exported = graph.to_dict()
        node_ids = {node["id"] for node in exported["nodes"]}

        self.assertIn("api:/online/queryOnlineRechargeForPage", node_ids)
        self.assertIn("method:OnlineRechargeOrRefundController#queryOnlineRechargeForPage", node_ids)
        self.assertIn("table:finance_d_t_third_pay_info", node_ids)
        self.assertIn("trace:trace-1", node_ids)


if __name__ == "__main__":
    unittest.main()

