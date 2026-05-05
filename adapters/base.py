"""
Adapter 公共基类
提供配置加载、启用检查、配置校验、多 profile 管理等公共能力。
所有 adapter 的 client 可继承此基类减少重复代码。

所有 adapter 均已继承此基类：
  - SLS: BaseAdapter（环境模式，非 profile）
  - Platform: BaseAdapter（单连接）
  - MySQL / Redis / Elasticsearch: MultiProfileAdapter（多 profile）
"""

from __future__ import annotations

import os
import re
import json
from pathlib import Path
from typing import Mapping, Optional

import yaml

# 自动加载 .env 文件（仅在文件存在时，不覆盖已有环境变量）
_SKILL_ROOT = Path(__file__).resolve().parent.parent
_dotenv = _SKILL_ROOT / ".env"
if _dotenv.exists():
    for _line in _dotenv.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

_ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::-(.*?))?\}')
_ENV_PROFILE_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]*)\[(\d+)\]\.([A-Z0-9_]+)$")
_INT_FIELDS = {"port", "db", "timeout", "export_timeout"}
_FIELD_ALIASES = {
    "desc": "description",
    "database": "database",
    "db": "db",
    "env": "env",
    "host": "host",
    "hosts": "hosts",
    "link": "link",
    "logstore": "logstore",
    "mode": "mode",
    "name": "name",
    "password": "password",
    "port": "port",
    "project": "project",
    "url": "url",
    "user": "user",
    "username": "username",
    "endpoint": "endpoint",
    "access_key_id": "access_key_id",
    "access_key_secret": "access_key_secret",
    "base_url": "base_url",
    "header_user": "header_user",
    "header_pass": "header_pass",
    "timeout": "timeout",
    "export_timeout": "export_timeout",
}


def _resolve_env_vars(value):
    """递归解析配置值中的环境变量引用 ${VAR} 或 ${VAR:-default}。
    纯整数结果自动转换为 int（适用于 port、db 等字段）。
    """
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    if isinstance(value, str):
        def replacer(m: re.Match) -> str:
            var_name, default = m.group(1), m.group(2)
            result = os.environ.get(var_name)
            if result is None:
                if default is None:
                    # 凭证缺失时返回空串，不阻止其他 profile 初始化
                    return ""
                return default
            return result
        resolved = _ENV_VAR_PATTERN.sub(replacer, value)
        if resolved != value and re.fullmatch(r'-?\d+', resolved):
            return int(resolved)
        return resolved
    return value


def _coerce_profile_value(field: str, value: str):
    if field in _INT_FIELDS and re.fullmatch(r"-?\d+", value):
        return int(value)
    if field == "hosts":
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def build_profiles_from_env(prefix: str, environ: Mapping[str, str] | None = None) -> list[dict]:
    """从 REDIS[0].HOST 这类数组式环境变量生成 profiles。

    字段名统一转成小写蛇形字段；DESC 会映射为 description。
    """
    source = os.environ if environ is None else environ
    wanted = prefix.upper()
    buckets: dict[int, dict] = {}
    for key, raw_value in source.items():
        match = _ENV_PROFILE_PATTERN.match(key)
        if not match:
            continue
        current_prefix, index_raw, field_raw = match.groups()
        if current_prefix != wanted:
            continue
        field_key = field_raw.lower()
        field = _FIELD_ALIASES.get(field_key, field_key)
        buckets.setdefault(int(index_raw), {})[field] = _coerce_profile_value(field, raw_value)
    return [buckets[index] for index in sorted(buckets)]


def _apply_dynamic_profiles(cfg: dict) -> dict:
    prefix = cfg.get("profiles_from_env")
    if not prefix:
        return cfg
    cfg["profiles"] = build_profiles_from_env(str(prefix))
    default_profile = cfg.get("default_profile")
    if not default_profile and cfg["profiles"]:
        cfg["default_profile"] = cfg["profiles"][0].get("name")
    return cfg


DISABLED_RESP = {
    "success": False,
    "data": None,
    "error": "adapter 已禁用（config.yaml enabled=false）",
}

_TRUTHY = {"1", "true", "yes", "on"}
_AGENT_ADAPTER_MODES = {"agent_auto", "agent-auto", "auto", "agent", "runtime"}
_MANUAL_ADAPTER_MODES = {"manual", "human", "user"}


def agent_auto_runtime_guard(adapter: str, operation: str, *, expected_track: str | None = None) -> dict | None:
    """阻止 Agent 绕过 Compass Runtime 直接查询 adapter。

    人工直接使用 adapter 时不会设置 runtime 变量，因此不受影响。
    Agent 排查必须先通过 action plan 生成 action，再设置 runtime action 上下文进入 adapter。
    """

    mode = _adapter_runtime_mode()
    if mode == "manual":
        return None
    if mode == "invalid":
        return _runtime_guard_block(adapter, operation, "COMPASS_ADAPTER_MODE 无效", adapter_mode=mode)

    state_file = os.environ.get("COMPASS_RUNTIME_STATE_FILE", "").strip()
    action_id = os.environ.get("COMPASS_RUNTIME_ACTION_ID", "").strip()
    if not state_file or not action_id:
        return _runtime_guard_block(
            adapter,
            operation,
            "缺少 COMPASS_RUNTIME_STATE_FILE 或 COMPASS_RUNTIME_ACTION_ID",
            adapter_mode=mode,
        )

    try:
        state = json.loads(Path(state_file).read_text(encoding="utf-8"))
    except Exception as exc:
        return _runtime_guard_block(adapter, operation, f"无法读取 runtime state：{exc}", adapter_mode=mode)

    if not state.get("flow", {}).get("confirmed"):
        return _runtime_guard_block(adapter, operation, "会话尚未 confirm", adapter_mode=mode)

    action = next((item for item in state.get("action_plan") or [] if str(item.get("action_id")) == action_id), None)
    if not action:
        return _runtime_guard_block(adapter, operation, f"找不到已规划 action：{action_id}", adapter_mode=mode)
    if action.get("status") != "planned":
        return _runtime_guard_block(
            adapter,
            operation,
            f"action {action_id} 状态为 {action.get('status')}，不能执行 adapter",
            adapter_mode=mode,
        )
    if expected_track and str(action.get("track", "")).lower() != expected_track.lower():
        return _runtime_guard_block(
            adapter,
            operation,
            f"action {action_id} track 不是 {expected_track}",
            adapter_mode=mode,
        )
    return None


def _adapter_runtime_mode() -> str:
    if os.environ.get("COMPASS_RUNTIME_GUARD", "").strip().lower() in _TRUTHY:
        return "runtime"
    if os.environ.get("COMPASS_AGENT_AUTO", "").strip().lower() in _TRUTHY:
        return "runtime"
    explicit = os.environ.get("COMPASS_ADAPTER_MODE", "").strip().lower()
    if explicit in _AGENT_ADAPTER_MODES:
        return "runtime"
    if explicit in _MANUAL_ADAPTER_MODES or not explicit:
        return "manual"
    return "invalid"


def _runtime_guard_block(adapter: str, operation: str, reason: str, *, adapter_mode: str = "runtime") -> dict:
    return {
        "success": False,
        "data": None,
        "error": f"禁止 agent runtime 裸调 adapter：{adapter}.{operation}。请先通过 compass action plan 并携带 runtime action 上下文。原因：{reason}",
        "requires_runtime_action": True,
        "adapter_mode": adapter_mode,
        "adapter": adapter,
        "operation": operation,
    }


def load_config(config_path: Optional[str] = None, caller_file: Optional[str] = None) -> dict:
    """
    加载 adapter 的 config.yaml。
    - config_path: 显式指定路径
    - caller_file: 调用者的 __file__，自动推断同目录的 config.yaml
    """
    if config_path is None:
        if caller_file is None:
            raise ValueError("必须提供 config_path 或 caller_file")
        config_path = Path(caller_file).parent / "config.yaml"
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    try:
        with open(path, "r") as f:
            cfg = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"配置文件 YAML 格式错误: {path} — {e}")
    if cfg is None:
        raise ValueError(f"配置文件为空: {path}")
    return _apply_dynamic_profiles(_resolve_env_vars(cfg))


def validate_config(cfg: dict, required_keys: list[str], adapter_name: str = "adapter") -> None:
    """
    校验配置中是否包含所有必需的 key。
    缺失时抛出 ValueError 并列出所有缺失项。
    """
    missing = [k for k in required_keys if k not in cfg]
    if missing:
        raise ValueError(
            f"{adapter_name} 配置缺少必需字段: {missing}，请检查 config.yaml"
        )


class BaseAdapter:
    """
    Adapter 基类，提供公共能力。

    子类应在 __init__ 中调用 super().__init__() 并传入 config_path。
    """

    ADAPTER_NAME: str = "base"
    REQUIRED_CONFIG_KEYS: list[str] = []

    def __init__(self, config_path: Optional[str] = None, caller_file: Optional[str] = None):
        self._cfg = load_config(config_path, caller_file)
        validate_config(self._cfg, self.REQUIRED_CONFIG_KEYS, self.ADAPTER_NAME)
        self._enabled = self._cfg.get("enabled", True)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _disabled_response(self) -> dict:
        return dict(DISABLED_RESP)

    def _check_enabled(self) -> Optional[dict]:
        """如果禁用，返回禁用响应；否则返回 None（可继续执行）。"""
        if not self._enabled:
            return self._disabled_response()
        return None

    def _health_payload(
        self,
        status: str,
        latency_ms: int | None = None,
        environment: str | None = None,
        error: str | None = None,
    ) -> dict:
        return {
            "adapter": self.ADAPTER_NAME,
            "status": status,
            "latency_ms": latency_ms,
            "environment": environment,
            "error": error,
        }


class MultiProfileAdapter(BaseAdapter):
    """
    支持多 profile（多环境/多实例）的 Adapter 基类。
    适用于 MySQL、Redis、Elasticsearch 等需要多连接配置的 adapter。
    """

    def __init__(self, config_path: Optional[str] = None, caller_file: Optional[str] = None):
        super().__init__(config_path, caller_file)
        self._profiles = {p["name"]: p for p in self._cfg.get("profiles", [])}
        self._default = self._cfg.get("default_profile")

    def _get_profile(self, profile_name: Optional[str] = None) -> dict:
        name = profile_name or self._default
        if not name or name not in self._profiles:
            raise ValueError(f"profile '{name}' 不存在，可用: {list(self._profiles.keys())}")
        return self._profiles[name]

    def list_profiles(self) -> dict:
        """列出所有可用的连接配置。子类可 override 以添加额外字段。"""
        blocked = self._check_enabled()
        if blocked:
            return blocked
        profiles = [
            {"name": name, **{k: v for k, v in p.items() if k not in ("password", "access_key_secret")}}
            for name, p in self._profiles.items()
        ]
        return {"success": True, "data": profiles, "error": None}
