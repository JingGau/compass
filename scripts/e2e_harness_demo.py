from __future__ import annotations

from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.compressor import compress
from tools.context_injector import ContextInjector
from tools.sensors import sense_context_size, sense_flow_deviation, sense_log_track_progress, sense_query_result
from tools.session_state import SessionState


def main() -> int:
    root = ROOT
    sm = SessionState(
        state_path=root / "memory/session-state.yaml",
        flow_checkpoints_path=root / "guards/flow-checkpoints.md",
    )
    injector = ContextInjector(root=root)

    state = sm.read_state()
    current = int(state["flow"]["current_step"])
    print(f"[init] step={current}")

    # Step 1
    print("[step1] read_state + flow_sensor + inject")
    print(sense_flow_deviation(current, int(state["flow"]["current_step"])))
    print(injector.get_context(current, "C端", state))
    sm.mark_checkpoint(1, "entities_extracted", True)
    sm.mark_checkpoint(1, "questions_asked_if_missing", True)
    print(sm.assert_step_complete(1))
    sm.advance_step(1, 2)

    # Step 2
    sm.mark_checkpoint(2, "scene_classified", True)
    sm.mark_checkpoint(2, "category_matched", True)
    print(sm.assert_step_complete(2))
    sm.advance_step(2, 3)

    # Step 3
    sm.mark_checkpoint(3, "code_or_page_mapped", True)
    sm.advance_step(3, 4)

    # Step 4
    sm.mark_checkpoint(4, "query_plan_shown", True)
    sm.mark_checkpoint(4, "track_declared", True)
    sm.mark_checkpoint(4, "user_confirmed_mode", True)
    sm.advance_step(4, 5)

    # Step 5
    sm.mark_checkpoint(5, "safety_gate_passed", True)
    sm.advance_step(5, 6)

    # Step 6
    print("[step6] query sensor demo")
    print(sense_query_result(rows=1200, retries=0))
    print(
        sense_log_track_progress(
            {
                "keyword_searched": True,
                "trace_id_extracted": True,
                "full_chain_pulled": True,
                "code_track_triggered": True,
            }
        )
    )
    sm.mark_checkpoint(6, "execution_started", True)
    sm.mark_checkpoint(6, "execution_completed", True)
    sm.advance_step(6, 7)

    # Step 7
    sm.mark_checkpoint(7, "conclusion_output", True)
    sm.mark_checkpoint(7, "analysis_complete", True)
    sm.advance_step(7, 8)

    # Step 8
    sm.mark_checkpoint(8, "feedback_collected", True)
    sm.mark_checkpoint(8, "strategy_archived", True)
    assert_result = sm.assert_step_complete(8)
    print("[step8] assert:", assert_result)

    state = sm.read_state()
    limits = yaml.safe_load((root / "guards/query-limits.yaml").read_text(encoding="utf-8"))
    sig = sense_context_size(
        current_tokens=65000,
        warn=limits["context_sensor"]["warn_tokens"],
        compress=limits["context_sensor"]["compress_tokens"],
        emergency=limits["context_sensor"]["emergency_tokens"],
    )
    print("[context_sensor]", sig)
    if sig["action"] in {"COMPRESS", "EMERGENCY_COMPRESS"}:
        print("[compress]", compress([{"step": 6, "content": "x" * 1800}]))

    print("[done] final_step=", state["flow"]["current_step"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

