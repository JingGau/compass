from __future__ import annotations

import re
from typing import Any

from tools.context_injector import estimate_tokens

# Key information patterns to preserve during compression
_KEY_PATTERNS = [
    re.compile(r'(?:实体|entity|userId|user_id)[：:]\s*\S+', re.IGNORECASE),
    re.compile(r'(?:traceId|trace_id|tlogId|tlog_id)[：:]\s*\S+', re.IGNORECASE),
    re.compile(r'(?:确认|confirm|模式|mode)[：:]\s*.*', re.IGNORECASE),
    re.compile(r'(?:结论|conclusion|根因|root_cause)[：:]\s*.*', re.IGNORECASE),
    re.compile(r'(?:关键发现|key_finding|发现)[：:]\s*.*', re.IGNORECASE),
    re.compile(r'(?:错误|error|异常|exception)[：:]\s*.*', re.IGNORECASE),
]

# Structured block markers (preserve these intact)
_STRUCT_STARTS = frozenset({'```', '| ', '- ', '##', '###', '✅', '🔴', '🟡', '🟢'})
_YAML_LINE = re.compile(r'^\s{0,2}\w+:\s*')


def _extract_key_lines(text: str) -> list[str]:
    """Extract lines matching key information patterns."""
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        for pat in _KEY_PATTERNS:
            if pat.search(stripped):
                result.append(stripped)
                break
    return result


def _extract_structured_lines(text: str) -> list[str]:
    """Extract lines that are part of structured blocks (YAML, tables, lists, code)."""
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(m) for m in _STRUCT_STARTS):
            result.append(stripped)
        elif _YAML_LINE.match(stripped):
            result.append(stripped)
    return result


def summarize_step(step: int, content: str, max_chars: int = 300) -> str:
    """Compress step content using section-aware strategy.

    Priority: key info lines > structured blocks > prose (truncated).
    """
    text = content.strip()
    if not text:
        return f"[Step {step}] (空)"
    if len(text) <= max_chars:
        return f"[Step {step}] {text.replace(chr(10), ' ')}"

    # Priority 1: key information lines
    key_lines = _extract_key_lines(text)

    # Priority 2: structured blocks
    struct_lines = _extract_structured_lines(text)

    # Combine with dedup, key lines first
    seen: set[str] = set()
    preserved: list[str] = []
    for line in key_lines + struct_lines:
        if line not in seen:
            preserved.append(line)
            seen.add(line)

    result = "\n".join(preserved)
    if len(result) > max_chars:
        result = result[:max_chars]
    return f"[Step {step}] {result}"


def compress(targets: list[dict[str, Any]]) -> dict[str, Any]:
    """Compress multiple step contents and report freed tokens."""
    compressed: list[dict[str, Any]] = []
    freed_chars = 0
    for item in targets:
        step = int(item.get("step", 0))
        raw = str(item.get("content", ""))
        summary = summarize_step(step, raw, max_chars=300)
        compressed.append({"step": step, "summary": summary})
        freed_chars += max(0, len(raw) - len(summary))
    return {
        "compressed": compressed,
        "freed_tokens": estimate_tokens("x" * freed_chars),
    }
