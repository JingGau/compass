from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Mapping


MIN_VERSION = (3, 10)
INSTALLABLE_ENV_SOURCES = {"COMPASS_PYTHON", ".venv", "VIRTUAL_ENV"}
REQUIREMENT_FILES = (
    "tools/requirements.txt",
    "adapters/sls/requirements.txt",
    "adapters/platform/requirements.txt",
    "adapters/mysql/requirements.txt",
    "adapters/redis/requirements.txt",
    "adapters/elasticsearch/requirements.txt",
)


@dataclass
class PythonEnvironmentReport:
    selected_python: str | None
    source: str
    version: str | None
    usable: bool
    reason: str | None
    create_venv_command: str
    install_command: str


def detect_python_environment(
    root: str | Path,
    environ: Mapping[str, str] | None = None,
    include_path: bool = True,
) -> PythonEnvironmentReport:
    root_path = Path(root)
    env = dict(os.environ if environ is None else environ)
    candidates = _candidate_pythons(root_path, env, include_path=include_path)
    for source, executable in candidates:
        version = _read_version(executable)
        if version is None:
            continue
        usable = _version_tuple(version) >= MIN_VERSION
        if usable:
            return _report(
                selected_python=str(executable),
                source=source,
                version=version,
                usable=True,
                reason=None,
                root=root_path,
            )
    return _report(
        selected_python=None,
        source="missing",
        version=None,
        usable=False,
        reason="未找到 Python 3.10+，需要安装 Python 或指定 COMPASS_PYTHON",
        root=root_path,
    )


def _candidate_pythons(
    root: Path,
    env: Mapping[str, str],
    include_path: bool,
) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    if env.get("COMPASS_PYTHON"):
        candidates.append(("COMPASS_PYTHON", env["COMPASS_PYTHON"]))

    venv_python = root / ".venv" / "bin" / "python"
    if venv_python.exists():
        candidates.append((".venv", str(venv_python)))

    if env.get("VIRTUAL_ENV"):
        candidates.append(("VIRTUAL_ENV", str(Path(env["VIRTUAL_ENV"]) / "bin" / "python")))

    candidates.append(("current", sys.executable))

    if include_path:
        for name in ("python3", "python"):
            found = shutil.which(name)
            if found:
                candidates.append((name, found))
    return candidates


def _read_version(executable: str) -> str | None:
    path = Path(executable)
    if not path.exists():
        return None
    try:
        proc = subprocess.run(
            [str(path), "-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _version_tuple(version: str) -> tuple[int, int, int]:
    parts = version.split(".")
    padded = (parts + ["0", "0", "0"])[:3]
    try:
        return int(padded[0]), int(padded[1]), int(padded[2])
    except ValueError:
        return (0, 0, 0)


def _report(
    selected_python: str | None,
    source: str,
    version: str | None,
    usable: bool,
    reason: str | None,
    root: Path,
) -> PythonEnvironmentReport:
    create_cmd = f"{selected_python or 'python3'} -m venv .venv"
    install_python = selected_python if selected_python and source in INSTALLABLE_ENV_SOURCES else ".venv/bin/python"
    install_cmd = " && ".join(f"{install_python} -m pip install -r {path}" for path in REQUIREMENT_FILES)
    return PythonEnvironmentReport(
        selected_python=selected_python,
        source=source,
        version=version,
        usable=usable,
        reason=reason,
        create_venv_command=f"cd {root} && {create_cmd}",
        install_command=f"cd {root} && {install_cmd}",
    )
