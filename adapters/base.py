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
from pathlib import Path
from typing import Optional

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


DISABLED_RESP = {
    "success": False,
    "data": None,
    "error": "adapter 已禁用（config.yaml enabled=false）",
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
    return _resolve_env_vars(cfg)


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
