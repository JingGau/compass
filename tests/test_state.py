from __future__ import annotations

import json
import tempfile
import unittest
from multiprocessing import Process
from pathlib import Path

from compass_core.runtime import add_evidence, confirm_session, start_session
from compass_core.state import read_state, update_state, write_state


def _write_large_state(path: Path, writer: int) -> None:
    write_state(
        path,
        {
            "schema_version": 2,
            "writer": writer,
            "payload": f"并发写入-{writer}-" * 5000,
            "flow": {"current_step": writer, "completed_steps": [], "execution_mode": "auto"},
        },
    )


def _append_evidence(path: Path, index: int) -> None:
    def mutate(state):
        state.setdefault("evidence", []).append({"id": index})

    update_state(path, mutate)


def _runtime_add_evidence(path: Path, index: int) -> None:
    add_evidence(
        path,
        source="并发测试",
        summary=f"状态机证据 {index}",
        kind="manual",
        strength="medium",
    )


class StateTest(unittest.TestCase):
    def test_concurrent_state_writes_keep_json_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            state_path = tmp_path / "compass-state.json"
            processes = [Process(target=_write_large_state, args=(state_path, index)) for index in range(10)]

            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=10)

            self.assertTrue(all(process.exitcode == 0 for process in processes))
            self.assertIn(json.loads(state_path.read_text(encoding="utf-8"))["writer"], range(10))
            self.assertIn(read_state(state_path)["writer"], range(10))
            self.assertEqual([], list(tmp_path.glob(".compass-state.json.*.tmp")))

    def test_update_state_serializes_read_modify_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "compass-state.json"
            write_state(state_path, {"schema_version": 2, "evidence": []})
            processes = [Process(target=_append_evidence, args=(state_path, index)) for index in range(20)]

            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=10)

            self.assertTrue(all(process.exitcode == 0 for process in processes))
            evidence = read_state(state_path)["evidence"]
            self.assertEqual(20, len(evidence))
            self.assertEqual(set(range(20)), {item["id"] for item in evidence})

    def test_runtime_evidence_add_uses_transactional_state_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "compass-state.json"
            start_session(state_path, "用户支付失败，订单号 123456，今天 12:00")
            confirm_session(state_path)
            processes = [Process(target=_runtime_add_evidence, args=(state_path, index)) for index in range(12)]

            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=10)

            self.assertTrue(all(process.exitcode == 0 for process in processes))
            state = read_state(state_path)
            evidence = state["evidence"]
            self.assertEqual(12, len(evidence))
            self.assertEqual({f"E{index}" for index in range(1, 13)}, {item["id"] for item in evidence})
            self.assertEqual(
                {f"状态机证据 {index}" for index in range(12)},
                {item["summary"] for item in evidence},
            )


if __name__ == "__main__":
    unittest.main()
