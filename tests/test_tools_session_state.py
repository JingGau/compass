from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.session_state import SessionState


class SessionStateTest(unittest.TestCase):
    def test_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mem = root / "memory" / "session-state.yaml"
            guard = root / "guards" / "flow-checkpoints.yaml"
            guard.parent.mkdir(parents=True, exist_ok=True)
            guard.write_text(
                "steps:\n  step_1:\n    - ready\n  step_2:\n    - done\n",
                encoding="utf-8",
            )
            sm = SessionState(state_path=mem, flow_checkpoints_path=guard)

            state = sm.read_state()
            self.assertEqual(state["flow"]["current_step"], 1)

            result = sm.assert_step_complete(step=1)
            self.assertFalse(result.ok)
            self.assertIn("ready", result.missing)

            sm.mark_checkpoint(step=1, checkpoint="ready", value=True)
            result2 = sm.assert_step_complete(step=1)
            self.assertTrue(result2.ok)

            advanced = sm.advance_step(from_step=1, to_step=2)
            self.assertEqual(advanced["flow"]["current_step"], 2)
            self.assertIn(1, advanced["flow"]["completed_steps"])


if __name__ == "__main__":
    unittest.main()

