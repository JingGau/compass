from __future__ import annotations

import unittest

from tools.sensors import (
    sense_context_size,
    sense_flow_deviation,
    sense_log_track_progress,
    sense_query_result,
)


class SensorsTest(unittest.TestCase):
    def test_flow_deviation(self) -> None:
        ok = sense_flow_deviation(2, 2)
        self.assertEqual(ok["signal"], "FLOW_OK")
        bad = sense_flow_deviation(3, 2)
        self.assertEqual(bad["signal"], "STEP_DEVIATION")

    def test_query_result(self) -> None:
        self.assertEqual(sense_query_result(0, 0)["signal"], "EMPTY_RESULT")
        self.assertEqual(sense_query_result(10, 3)["signal"], "RETRY_LIMIT")
        self.assertEqual(sense_query_result(600, 0)["signal"], "LARGE_RESULT")
        self.assertEqual(sense_query_result(20, 0)["signal"], "RESULT_OK")

    def test_context_size(self) -> None:
        self.assertEqual(sense_context_size(30000, 40000, 60000, 80000)["signal"], "CONTEXT_OK")
        self.assertEqual(sense_context_size(45000, 40000, 60000, 80000)["signal"], "CONTEXT_WARN")
        self.assertEqual(
            sense_context_size(70000, 40000, 60000, 80000)["signal"], "CONTEXT_COMPRESS_REQUIRED"
        )
        self.assertEqual(sense_context_size(90000, 40000, 60000, 80000)["signal"], "CONTEXT_EMERGENCY")

    def test_log_track_progress(self) -> None:
        incomplete = sense_log_track_progress({"keyword_searched": True})
        self.assertEqual(incomplete["signal"], "LOG_TRACK_INCOMPLETE")
        complete = sense_log_track_progress(
            {
                "keyword_searched": True,
                "trace_id_extracted": True,
                "full_chain_pulled": True,
                "code_track_triggered": True,
            }
        )
        self.assertEqual(complete["signal"], "LOG_TRACK_COMPLETE")


if __name__ == "__main__":
    unittest.main()

