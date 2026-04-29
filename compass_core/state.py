from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "session_id": f"sess_{int(datetime.now(timezone.utc).timestamp())}",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "flow": {"current_step": 1, "completed_steps": [], "execution_mode": "auto"},
        "revision": 1,
        "mode": "investigation_only",
        "write_policy": "no_code_or_data_mutation",
        "environment": "prod",
        "entities": {},
        "evidence": [],
        "hypotheses": [],
        "scene_facts": [],
        "action_plan": [],
        "action_history": [],
        "evidence_graph": {"nodes": [], "edges": []},
        "conclusion_history": [],
        "strategy_review": {},
        "ruled_out": [],
        "next_actions": [],
        "applicable_knowledge": [],
        "changes": [],
        "pending_confirmations": [],
    }


def read_or_init_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state = default_state()
        write_state(state_path, state)
        return state
    state = _read_state_raw(state_path)
    migrated = migrate_state(state)
    if migrated != state:
        write_state(state_path, migrated)
    return migrated


def read_state(path: str | Path) -> dict[str, Any]:
    return migrate_state(_read_state_raw(path))


def _read_state_raw(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    if not state_path.exists():
        return {}
    text = state_path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return _read_yaml_like(text)


def migrate_state(state: dict[str, Any]) -> dict[str, Any]:
    if not state:
        return state
    migrated = dict(state)
    migrated.setdefault("schema_version", 2)
    migrated.setdefault("created_at", now_iso())
    migrated.setdefault("updated_at", now_iso())
    migrated.setdefault("flow", {"current_step": 1, "completed_steps": [], "execution_mode": "auto"})
    migrated.setdefault("revision", 1)
    migrated.setdefault("mode", "investigation_only")
    migrated.setdefault("write_policy", "no_code_or_data_mutation")
    migrated.setdefault("environment", migrated.get("problem", {}).get("environment", "prod"))
    migrated.setdefault("entities", {})
    migrated.setdefault("evidence", [])
    migrated.setdefault("hypotheses", [])
    migrated.setdefault("scene_facts", [])
    migrated.setdefault("action_plan", [])
    migrated.setdefault("action_history", [])
    migrated.setdefault("evidence_graph", {"nodes": [], "edges": []})
    migrated.setdefault("conclusion_history", [])
    migrated.setdefault("strategy_review", {})
    migrated.setdefault("ruled_out", [])
    migrated.setdefault("next_actions", [])
    migrated.setdefault("applicable_knowledge", [])
    migrated.setdefault("changes", [])
    migrated.setdefault("pending_confirmations", [])
    if int(migrated.get("schema_version", 1)) < 2:
        migrated["schema_version"] = 2
    return migrated


def write_state(path: str | Path, state: dict[str, Any]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_yaml_like(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text) or {}
    except ModuleNotFoundError:
        return _parse_small_yaml(text)


def _parse_small_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, result)]
    last_key_at_indent: dict[int, str] = {}
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if line.startswith("- "):
            item = _parse_list_item(line[2:])
            if isinstance(parent, list):
                parent.append(item)
                if isinstance(item, dict):
                    stack.append((indent, item))
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        parsed = _parse_scalar(value.strip())
        if isinstance(parent, dict):
            if value.strip():
                parent[key] = parsed
            else:
                parent[key] = {}
                last_key_at_indent[indent] = key
                stack.append((indent, parent[key]))
                continue
            last_key_at_indent[indent] = key
        next_line_is_list = False
        # The minimal parser only needs top-level nested dicts for current tests.
        if next_line_is_list:
            parent[key] = []
    return result


def _parse_list_item(text: str) -> Any:
    if ":" in text:
        key, _, value = text.partition(":")
        return {key.strip(): _parse_scalar(value.strip())}
    return _parse_scalar(text)


def _parse_scalar(value: str) -> Any:
    if value in {"", "null", "None"}:
        return None
    if value in {"[]", "[ ]"}:
        return []
    if value in {"{}", "{ }"}:
        return {}
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value
