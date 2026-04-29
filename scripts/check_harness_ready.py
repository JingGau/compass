"""检查 v4 phase-based runtime 必备文件是否齐全。

旧 v3 step-based harness 已迁到 legacy/，本脚本只检查 CLI Runtime 主流程依赖；
不再检查用户私有目录（projects/、knowledge/b-side/、knowledge/c-side/、memory/session-state.yaml
等被 .gitignore 排除的文件）。
"""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent


REQUIRED_FILES: tuple[Path, ...] = (
    ROOT / "SKILL.md",
    ROOT / "README.md",
    ROOT / ".env.example",
    ROOT / "compass_cli/__main__.py",
    ROOT / "compass_core/runtime.py",
    ROOT / "compass_core/state.py",
    ROOT / "compass_core/intake.py",
    ROOT / "compass_core/report.py",
    ROOT / "compass_core/masking.py",
    ROOT / "compass_core/kb.py",
    ROOT / "compass_core/knowledge.py",
    ROOT / "compass_core/timeline.py",
    ROOT / "memory/knowledge.yaml",
    ROOT / "tools/action_cards.py",
    ROOT / "tools/sql_gate.py",
    ROOT / "tools/setup_check.py",
    ROOT / "tools/python_env.py",
    ROOT / "tools/evidence_graph.py",
    ROOT / "tools/env_config.py",
    ROOT / "guards/sql-safety.md",
    ROOT / "guards/data-masking.md",
    ROOT / "guards/redis-safety.md",
    ROOT / "guards/es-safety.md",
    ROOT / "knowledge/data-source-index.md",
    ROOT / "memory/strategies.yaml",
    ROOT / "references/intake-and-state.md",
    ROOT / "references/runtime-protocol.md",
    ROOT / "references/safety-and-capabilities.md",
)

REQUIRED_ADAPTERS: tuple[str, ...] = ("sls", "platform", "mysql", "redis", "elasticsearch")


def _missing_files() -> list[str]:
    missing: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
    for adapter in REQUIRED_ADAPTERS:
        for filename in ("client.py", "config.yaml", "requirements.txt"):
            target = ROOT / "adapters" / adapter / filename
            if not target.exists():
                missing.append(str(target.relative_to(ROOT)))
    return missing


def main() -> int:
    missing = _missing_files()
    if missing:
        print("\u274c Harness 未就绪，缺失文件:")
        for item in missing:
            print(" -", item)
        return 1
    print("\u2705 Harness 基础文件检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
