from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.compressor import compress
from tools.context_injector import ContextInjector
from tools.env_config import int_env, load_dotenv
from tools.sensors import (
    sense_context_size,
    sense_flow_deviation,
    sense_log_track_progress,
    sense_query_result,
)
from tools.session_state import SessionState


def run_turn(sm: SessionState, injector: ContextInjector, declared_step: int, scene: str) -> dict:
    # 1) read_state
    state = sm.read_state()
    actual_step = int(state["flow"]["current_step"])

    # 2) flow deviation
    flow_signal = sense_flow_deviation(declared_step=declared_step, actual_step=actual_step)
    if flow_signal["action"] == "ROLLBACK":
        return {"ok": False, "stage": "flow", "signal": flow_signal}

    # 3) get_context
    context_pkg = injector.get_context(step=actual_step, scene=scene, state=state)

    # 4) query_result (demo signal)
    query_signal = sense_query_result(rows=20, retries=0)
    if query_signal["signal"] == "RETRY_LIMIT":
        sm.add_pending_confirmation({"id": "retry-limit", "reason": "query retry limit reached"})
        return {"ok": False, "stage": "query", "signal": query_signal}

    # 5) mark checkpoint (per-step minimal auto mark)
    checkpoint_map = {
        1: ["entities_extracted", "questions_asked_if_missing"],
        2: ["scene_classified", "category_matched"],
        3: ["code_or_page_mapped"],
        4: ["query_plan_shown", "track_declared", "user_confirmed_mode"],
        5: ["safety_gate_passed"],
        6: ["execution_started", "execution_completed"],
        7: ["conclusion_output", "analysis_complete"],
        8: ["feedback_collected", "strategy_archived"],
    }
    for name in checkpoint_map.get(actual_step, []):
        sm.mark_checkpoint(actual_step, name, True)

    # 6) log track gate (only on step6)
    if actual_step == 6:
        log_signal = sense_log_track_progress(
            {
                "keyword_searched": True,
                "trace_id_extracted": True,
                "full_chain_pulled": True,
                "code_track_triggered": True,
            }
        )
        if not log_signal["complete"]:
            return {"ok": False, "stage": "log_track", "signal": log_signal}

    # 7) assert_step_complete
    assert_result = sm.assert_step_complete(actual_step)
    if not assert_result.ok:
        return {"ok": False, "stage": "assert", "signal": asdict(assert_result)}

    # 8) context size -> maybe compress
    limits = yaml.safe_load((ROOT / "guards/query-limits.yaml").read_text(encoding="utf-8"))
    warn_tokens = int_env("HARN_CONTEXT_WARN_TOKENS", int(limits["context_sensor"]["warn_tokens"]))
    compress_tokens = int_env("HARN_CONTEXT_COMPRESS_TOKENS", int(limits["context_sensor"]["compress_tokens"]))
    emergency_tokens = int_env("HARN_CONTEXT_EMERGENCY_TOKENS", int(limits["context_sensor"]["emergency_tokens"]))
    size_signal = sense_context_size(
        current_tokens=int(context_pkg.estimated_tokens),
        warn=warn_tokens,
        compress=compress_tokens,
        emergency=emergency_tokens,
    )
    compressed = None
    if size_signal["action"] in {"COMPRESS", "EMERGENCY_COMPRESS"}:
        compressed = compress([{"step": actual_step, "content": str(context_pkg.content)}])

    # 9) advance_step
    if actual_step < 8:
        sm.advance_step(actual_step, actual_step + 1)

    # 10) write_state
    sm.write_state({"context": {"estimated_tokens": int(context_pkg.estimated_tokens)}})

    return {
        "ok": True,
        "step": actual_step,
        "flow_signal": flow_signal,
        "query_signal": query_signal,
        "size_signal": size_signal,
        "compressed": compressed,
    }


def main() -> int:
    load_dotenv(ROOT)
    runtime = ROOT / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    protocol_state = runtime / "protocol-session-state.yaml"
    if protocol_state.exists():
        protocol_state.unlink()

    sm = SessionState(
        state_path=protocol_state,
        flow_checkpoints_path=ROOT / "guards/flow-checkpoints.md",
    )
    injector = ContextInjector(ROOT)

    for declared in range(1, 9):
        result = run_turn(sm, injector, declared_step=declared, scene="C端")
        print(f"[turn:{declared}] {result}")
        if not result.get("ok"):
            return 1

    final_state = sm.read_state()
    print("[done] current_step=", final_state["flow"]["current_step"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

