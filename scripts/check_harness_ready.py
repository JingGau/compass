from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent


def _ok(path: Path) -> bool:
    return path.exists()


def main() -> int:
    must_exist = [
        ROOT / "tools/session_state.py",
        ROOT / "tools/context_injector.py",
        ROOT / "tools/sensors.py",
        ROOT / "tools/compressor.py",
        ROOT / "tools/tool_protocol.md",
        ROOT / "guards/flow-checkpoints.yaml",
        ROOT / "memory/session-state.yaml",
        ROOT / "memory/strategies.yaml",
        ROOT / "knowledge/system-topology.md",
        ROOT / "projects/omp-shop.md",
    ]
    missing = [str(p.relative_to(ROOT)) for p in must_exist if not _ok(p)]
    if missing:
        print("❌ Harness 未就绪，缺失文件:")
        for m in missing:
            print(" -", m)
        return 1
    print("✅ Harness 基础文件检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())

