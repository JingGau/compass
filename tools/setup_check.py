from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
from typing import Mapping

from tools.python_env import PythonEnvironmentReport, detect_python_environment


MINIMUM_REQUIRED = ("CODE_ROOT",)

ADAPTER_PROFILE_REQUIREMENTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "sls": ("SLS", ("NAME", "ENV", "ENDPOINT", "PROJECT", "ACCESS_KEY_ID", "ACCESS_KEY_SECRET")),
    "platform": ("PLATFORM", ("NAME", "ENV", "BASE_URL", "USERNAME", "PASSWORD")),
    "elasticsearch": ("ES", ("NAME", "ENV", "URL", "USERNAME", "PASSWORD")),
    "mysql": ("MYSQL", ("NAME", "ENV", "HOST", "PORT", "USER", "PASSWORD", "DATABASE")),
    "redis": ("REDIS", ("NAME", "ENV", "HOST", "PORT", "PASSWORD", "DB")),
}
_PROFILE_KEY_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]*)\[(\d+)\]\.([A-Z0-9_]+)$")


@dataclass
class AdapterSetupStatus:
    name: str
    configured: bool
    missing_variables: list[str] = field(default_factory=list)
    profiles: list[str] = field(default_factory=list)


@dataclass
class SetupReport:
    env_exists: bool
    minimum_ready: bool
    missing_minimum: list[str]
    code_root: str | None
    code_root_exists: bool
    adapter_status: dict[str, AdapterSetupStatus]
    python_environment: PythonEnvironmentReport
    next_steps: list[str]


def inspect_setup(root: str | Path, environ: Mapping[str, str] | None = None) -> SetupReport:
    root_path = Path(root)
    env_path = root_path / ".env"
    values = _read_env_file(env_path)
    runtime_env = dict(os.environ if environ is None else environ)
    for key, value in runtime_env.items():
        values.setdefault(key, value)

    python_environment = detect_python_environment(root_path, environ=values)
    missing_minimum = [name for name in MINIMUM_REQUIRED if not _has_value(values.get(name))]
    code_root = values.get("CODE_ROOT")
    code_root_exists = bool(code_root and Path(code_root).exists())
    if code_root and not code_root_exists and Path(code_root).expanduser().exists():
        code_root_exists = True

    adapter_status: dict[str, AdapterSetupStatus] = {}
    for adapter, (prefix, required_fields) in ADAPTER_PROFILE_REQUIREMENTS.items():
        profile_values = _profiles_by_prefix(values, prefix)
        missing = _missing_profile_fields(profile_values, prefix, required_fields)
        adapter_status[adapter] = AdapterSetupStatus(
            name=adapter,
            configured=not missing,
            missing_variables=missing,
            profiles=[profile.get("NAME", f"{prefix}[{idx}]") for idx, profile in sorted(profile_values.items())],
        )

    minimum_ready = env_path.exists() and not missing_minimum and code_root_exists
    return SetupReport(
        env_exists=env_path.exists(),
        minimum_ready=minimum_ready,
        missing_minimum=missing_minimum,
        code_root=code_root,
        code_root_exists=code_root_exists,
        adapter_status=adapter_status,
        python_environment=python_environment,
        next_steps=_next_steps(env_path.exists(), missing_minimum, code_root, code_root_exists),
    )


def render_setup_report(report: SetupReport) -> str:
    lines = ["## Compass 配置检查"]
    lines.append(f"- .env：{'已存在' if report.env_exists else '缺失'}")
    lines.append(f"- 最小配置：{'可用' if report.minimum_ready else '未完成，先完成配置'}")
    if report.code_root:
        exists = "存在" if report.code_root_exists else "不存在"
        lines.append(f"- CODE_ROOT：{report.code_root}（{exists}）")
    else:
        lines.append("- CODE_ROOT：未配置")
    py = report.python_environment
    if py.usable:
        lines.append(f"- Python：{py.selected_python}（{py.source}, {py.version}）")
    else:
        lines.append(f"- Python：不可用（{py.reason}）")

    lines.append("")
    lines.append("### Adapter 凭证")
    for status in report.adapter_status.values():
        if status.configured:
            profile_text = f"（{', '.join(status.profiles)}）" if status.profiles else ""
            lines.append(f"- {status.name}：已配置{profile_text}")
        else:
            lines.append(f"- {status.name}：未配置（缺少 {', '.join(status.missing_variables)}）")

    if report.next_steps:
        lines.append("")
        lines.append("### 下一步")
        for step in report.next_steps:
            lines.append(f"- {step}")
        if not report.python_environment.usable:
            lines.append(f"- 准备 Python：{report.python_environment.create_venv_command}")
        lines.append(f"- 依赖安装命令（执行前需确认）：{report.python_environment.install_command}")
    return "\n".join(lines)


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = _strip_quotes(value.strip())
    return values


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _has_value(value: str | None) -> bool:
    return bool(value and value.strip())


def _profiles_by_prefix(values: Mapping[str, str], prefix: str) -> dict[int, dict[str, str]]:
    profiles: dict[int, dict[str, str]] = {}
    for key, value in values.items():
        match = _PROFILE_KEY_PATTERN.match(key)
        if not match:
            continue
        current_prefix, index_raw, field = match.groups()
        if current_prefix != prefix:
            continue
        profiles.setdefault(int(index_raw), {})[field] = value
    return profiles


def _missing_profile_fields(
    profiles: dict[int, dict[str, str]],
    prefix: str,
    required_fields: tuple[str, ...],
) -> list[str]:
    if not profiles:
        return [f"{prefix}[0].{field}" for field in required_fields]
    missing: list[str] = []
    for index, profile in sorted(profiles.items()):
        for field in required_fields:
            if not _has_value(profile.get(field)):
                missing.append(f"{prefix}[{index}].{field}")
    return missing


def _next_steps(
    env_exists: bool,
    missing_minimum: list[str],
    code_root: str | None,
    code_root_exists: bool,
) -> list[str]:
    steps: list[str] = []
    if not env_exists:
        steps.append("复制模板：cp .env.example .env")
    if missing_minimum:
        steps.append(f"在 .env 中填写最小必填项：{', '.join(missing_minimum)}")
    if code_root and not code_root_exists:
        steps.append("修正 CODE_ROOT，确保它指向本机代码仓库根目录")
    if not steps:
        steps.append("按需补充 SLS / Platform / MySQL / Redis / ES 凭证，然后运行 adapter health_check")
    return steps
