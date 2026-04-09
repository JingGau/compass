from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AssertResult:
    ok: bool
    missing: list[str]
    block_reason: str | None = None


class SessionState:
    def __init__(
        self,
        state_path: str | Path = "memory/session-state.yaml",
        flow_checkpoints_path: str | Path = "guards/flow-checkpoints.md",
    ) -> None:
        self.state_path = Path(state_path)
        self.flow_checkpoints_path = Path(flow_checkpoints_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def init_if_missing(self) -> None:
        if self.state_path.exists():
            return
        base = {
            "session_id": f"sess_{int(datetime.now(timezone.utc).timestamp())}",
            "created_at": _now(),
            "updated_at": _now(),
            "flow": {"current_step": 1, "completed_steps": [], "execution_mode": "auto"},
            "entities": {},
            "checkpoints": {},
            "pending_confirmations": [],
            "context": {"estimated_tokens": 0, "compressed_steps": []},
            "active_tools": {"adapter": None, "track": None},
            "temp_files": [],
        }
        self._save(base)

    def read_state(self) -> dict[str, Any]:
        self.init_if_missing()
        with self.state_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def write_state(self, patch: dict[str, Any]) -> dict[str, Any]:
        state = self._merge(self.read_state(), patch)
        state["updated_at"] = _now()
        self._save(state)
        return state

    def mark_checkpoint(self, step: int, checkpoint: str, value: Any) -> dict[str, Any]:
        state = self.read_state()
        key = f"step_{step}"
        state.setdefault("checkpoints", {}).setdefault(key, {})[checkpoint] = value
        state["updated_at"] = _now()
        self._save(state)
        return state

    def add_pending_confirmation(self, item: dict[str, Any]) -> dict[str, Any]:
        state = self.read_state()
        state.setdefault("pending_confirmations", []).append(item)
        state["updated_at"] = _now()
        self._save(state)
        return state

    def resolve_pending(self, item_id: str) -> dict[str, Any]:
        state = self.read_state()
        state["pending_confirmations"] = [
            x for x in state.get("pending_confirmations", []) if str(x.get("id")) != item_id
        ]
        state["updated_at"] = _now()
        self._save(state)
        return state

    def assert_step_complete(self, step: int) -> AssertResult:
        required = self._load_required_checkpoints(step)
        state = self.read_state()
        bucket = state.get("checkpoints", {}).get(f"step_{step}", {})
        missing = [name for name in required if not bool(bucket.get(name))]
        if missing:
            return AssertResult(
                ok=False,
                missing=missing,
                block_reason=f"Step {step} 未完成，缺失: {', '.join(missing)}",
            )
        return AssertResult(ok=True, missing=[])

    def advance_step(self, from_step: int, to_step: int) -> dict[str, Any]:
        state = self.read_state()
        current = int(state.get("flow", {}).get("current_step", 1))
        if current != from_step:
            raise ValueError(f"状态不一致: current={current}, from={from_step}")
        if to_step != from_step + 1:
            raise ValueError(f"步骤不连续: from={from_step}, to={to_step}")
        flow = state.setdefault("flow", {})
        flow.setdefault("completed_steps", []).append(from_step)
        flow["current_step"] = to_step
        state["updated_at"] = _now()
        self._save(state)
        return state

    def _load_required_checkpoints(self, step: int) -> list[str]:
        if not self.flow_checkpoints_path.exists():
            return []
        text = self.flow_checkpoints_path.read_text(encoding="utf-8")
        required: list[str] = []
        in_step = False
        for raw in text.splitlines():
            line = raw.strip()
            if line.startswith("## Step "):
                in_step = line == f"## Step {step}"
                continue
            if not in_step:
                continue
            if line.startswith("- ") and ".checkpoints.step_" in line:
                # 形如: - flow.checkpoints.step_4.query_plan_shown
                name = line.split(".")[-1]
                required.append(name)
        return required

    def _save(self, state: dict[str, Any]) -> None:
        with self.state_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(state, f, allow_unicode=True, sort_keys=False)

    def _merge(self, a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
        out = dict(a)
        for k, v in b.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = self._merge(out[k], v)  # type: ignore[index]
            else:
                out[k] = v
        return out
