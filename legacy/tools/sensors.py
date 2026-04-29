from __future__ import annotations

from typing import Any


def sense_flow_deviation(declared_step: int, actual_step: int) -> dict[str, Any]:
    if declared_step == actual_step:
        return {"signal": "FLOW_OK", "deviation": False, "action": "CONTINUE"}
    return {
        "signal": "STEP_DEVIATION",
        "deviation": True,
        "declared_step": declared_step,
        "actual_step": actual_step,
        "action": "ROLLBACK",
        "instruction": f"回到 Step {actual_step}，禁止跳步。",
    }


def sense_query_result(rows: int, retries: int, max_retry_count: int = 3, large_threshold: int = 500) -> dict[str, Any]:
    if retries >= max_retry_count:
        return {"signal": "RETRY_LIMIT", "severity": "warn", "action": "PAUSE", "block_conclusion": True}
    if rows == 0:
        return {
            "signal": "EMPTY_RESULT",
            "severity": "warn",
            "action": "REQUIRE_ALTERNATIVE_PATH",
            "block_conclusion": True,
        }
    if rows > large_threshold:
        return {
            "signal": "LARGE_RESULT",
            "severity": "info",
            "action": "SUMMARIZE_AND_TRUNCATE",
            "block_conclusion": False,
        }
    return {"signal": "RESULT_OK", "severity": "info", "action": "CONTINUE", "block_conclusion": False}


def sense_context_size(current_tokens: int, warn: int, compress: int, emergency: int) -> dict[str, Any]:
    if current_tokens >= emergency:
        return {"signal": "CONTEXT_EMERGENCY", "action": "EMERGENCY_COMPRESS", "threshold": emergency}
    if current_tokens >= compress:
        return {"signal": "CONTEXT_COMPRESS_REQUIRED", "action": "COMPRESS", "threshold": compress}
    if current_tokens >= warn:
        return {"signal": "CONTEXT_WARN", "action": "WARN", "threshold": warn}
    return {"signal": "CONTEXT_OK", "action": "CONTINUE"}


def sense_log_track_progress(checkpoint_bucket: dict[str, Any]) -> dict[str, Any]:
    required = ["keyword_searched", "trace_id_extracted", "full_chain_pulled", "code_track_triggered"]
    missing = [k for k in required if not bool(checkpoint_bucket.get(k))]
    if missing:
        return {
            "signal": "LOG_TRACK_INCOMPLETE",
            "complete": False,
            "missing": missing,
            "action": "BLOCK_CONCLUSION",
            "block_reason": f"日志轨四步未完成: {', '.join(missing)}",
        }
    return {"signal": "LOG_TRACK_COMPLETE", "complete": True, "action": "CONTINUE"}
