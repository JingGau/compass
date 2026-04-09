from __future__ import annotations

import unittest

from scripts.harness_protocol_runner import main


class ProtocolRunnerTest(unittest.TestCase):
    def test_runner_full_flow(self) -> None:
        code = main()
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()

