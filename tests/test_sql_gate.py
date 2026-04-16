from __future__ import annotations

import unittest

from tools.sql_gate import assess_sql_explain, parse_doris_explain


class SqlGateTest(unittest.TestCase):
    def test_doris_high_cardinality_requires_confirmation(self) -> None:
        explain = """
        0:VOlapScanNode(211)
        TABLE: ods_finance_cdc.ods_finance_d_t_third_pay_info
        PREDICATES: ((flow_number = '20260413234173136502786'))
        partitions=1/69 (p202604)
        tablets=3/3
        cardinality=2470577, avgRowSize=0.0, numNodes=1
        """

        summary = parse_doris_explain(explain)
        gate = assess_sql_explain("SELECT * FROM t WHERE flow_number='x'", explain, environment="prod")

        self.assertEqual(summary.cardinality, 2470577)
        self.assertEqual(summary.partitions, "1/69")
        self.assertTrue(summary.has_olap_scan)
        self.assertEqual(gate.risk_level, "high")
        self.assertTrue(gate.requires_confirmation)
        self.assertEqual(gate.status, "blocked")

    def test_doris_low_cardinality_can_auto_continue(self) -> None:
        explain = """
        0:VOlapScanNode(204)
        PREDICATES: ((user_id = 123))
        partitions=1/1
        tablets=1/1
        cardinality=50000, avgRowSize=0.0, numNodes=1
        """

        gate = assess_sql_explain("SELECT * FROM t WHERE user_id=123", explain, environment="prod")

        self.assertEqual(gate.risk_level, "low")
        self.assertFalse(gate.requires_confirmation)
        self.assertEqual(gate.status, "passed")

    def test_non_prod_skips_explain_risk(self) -> None:
        gate = assess_sql_explain("SELECT * FROM t", "", environment="uat")

        self.assertEqual(gate.status, "passed")
        self.assertEqual(gate.risk_level, "low")
        self.assertFalse(gate.requires_confirmation)


if __name__ == "__main__":
    unittest.main()

