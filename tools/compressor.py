from __future__ import annotations

from typing import Any


def summarize_step(step: int, content: str, max_chars: int = 300) -> str:
    text = content.strip().replace("\n", " ")
    if len(text) <= max_chars:
        return f"[Step {step}] {text}"
    return f"[Step {step}] {text[:max_chars]}..."


def compress(targets: list[dict[str, Any]]) -> dict[str, Any]:
    compressed: list[dict[str, Any]] = []
    freed_chars = 0
    for item in targets:
        step = int(item.get("step", 0))
        raw = str(item.get("content", ""))
        summary = summarize_step(step, raw)
        compressed.append({"step": step, "summary": summary})
        freed_chars += max(0, len(raw) - len(summary))
    return {
        "compressed": compressed,
        "freed_tokens": max(0, freed_chars // 4),
    }
