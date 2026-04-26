from __future__ import annotations

import re
from typing import Any


PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
TOKEN_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|secret|token|credential|cookie|session|jwt|key)\s*=\s*[^,\s|，；;]+"
)


def mask_text(value: Any) -> str:
    text = str(value)
    text = PHONE_RE.sub(lambda match: f"{match.group(1)[:3]}****{match.group(1)[-4:]}", text)
    text = TOKEN_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=******", text)
    return text


def mask_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: mask_value(key, value) for key, value in mapping.items()}


def mask_value(key: str, value: Any) -> Any:
    normalized = key.replace("_", "").replace("-", "").lower()
    if any(marker in normalized for marker in ("password", "secret", "token", "credential", "cookie", "session", "jwt")):
        return "******"
    if isinstance(value, dict):
        return mask_mapping(value)
    if isinstance(value, list):
        return [mask_value(key, item) for item in value]
    return mask_text(value)
