from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    import fcntl
except ImportError:  # pragma: no cover - fcntl is available on macOS/Linux.
    fcntl = None  # type: ignore[assignment]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "session_id": f"sess_{int(datetime.now(timezone.utc).timestamp())}",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "flow": {
            "current_step": 1,
            "completed_steps": [],
            "confirmed": False,
            "confirmation_policy": "first_confirm_then_continue_until_gate",
        },
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
        "conclusion_history": [],
        "strategy_review": {},
        "ruled_out": [],
        "next_actions": [],
        "applicable_knowledge": [],
        "investigation_hints": [],
        "changes": [],
        "pending_confirmations": [],
        "events": [],
    }


def read_or_init_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    with _state_file_lock(state_path):
        if not state_path.exists():
            state = default_state()
            _write_state_unlocked(state_path, state)
            return state
        state = _read_state_raw(state_path)
        migrated = migrate_state(state)
        if migrated != state:
            _write_state_unlocked(state_path, migrated)
        return migrated


def read_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    with _state_file_lock(state_path):
        return migrate_state(_read_state_raw(state_path))


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
    migrated.setdefault(
        "flow",
        {
            "current_step": 1,
            "completed_steps": [],
            "confirmed": False,
            "confirmation_policy": "first_confirm_then_continue_until_gate",
        },
    )
    if isinstance(migrated.get("flow"), dict):
        flow = migrated["flow"]
        normalized_flow = {
            "current_step": flow.get("current_step", 1),
            "completed_steps": flow.get("completed_steps", []),
            "confirmed": flow.get("confirmed", False),
            "confirmation_policy": flow.get("confirmation_policy", "first_confirm_then_continue_until_gate"),
        }
        for key in ("phase", "allowed_commands", "report_generated", "report_generated_at"):
            if key in flow:
                normalized_flow[key] = flow[key]
        migrated["flow"] = normalized_flow
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
    migrated.setdefault("conclusion_history", [])
    migrated.setdefault("strategy_review", {})
    migrated.setdefault("ruled_out", [])
    migrated.setdefault("next_actions", [])
    migrated.setdefault("applicable_knowledge", [])
    migrated.setdefault("investigation_hints", [])
    migrated.setdefault("changes", [])
    migrated.setdefault("pending_confirmations", [])
    migrated.setdefault("events", [])
    if int(migrated.get("schema_version", 1)) < 2:
        migrated["schema_version"] = 2
    return migrated


def write_state(path: str | Path, state: dict[str, Any]) -> None:
    state_path = Path(path)
    with _state_file_lock(state_path):
        _write_state_unlocked(state_path, state)


def update_state(path: str | Path, mutator: Callable[[dict[str, Any]], Any]) -> dict[str, Any]:
    """Read, mutate, and persist state while holding the same file lock."""

    state_path = Path(path)
    with _state_file_lock(state_path):
        state = migrate_state(_read_state_raw(state_path)) if state_path.exists() else default_state()
        result = mutator(state)
        next_state = result if isinstance(result, dict) else state
        _write_state_unlocked(state_path, next_state)
        return next_state


@contextmanager
def _state_file_lock(state_path: str | Path):
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_name(f"{state_path.name}.lock")
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _write_state_unlocked(path: str | Path, state: dict[str, Any]) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=state_path.parent,
            prefix=f".{state_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_name = temp_file.name
            temp_file.write(payload)
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_name, state_path)
        temp_name = None
        _fsync_directory(state_path.parent)
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


def _fsync_directory(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


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
