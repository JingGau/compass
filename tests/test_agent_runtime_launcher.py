from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_agent_runtime_launcher_forces_guard_environment() -> None:
    env = os.environ.copy()
    env["COMPASS_ADAPTER_MODE"] = "manual"
    env["COMPASS_RUNTIME_GUARD"] = "0"

    result = subprocess.run(
        [
            "bash",
            "scripts/compass-agent-runtime.sh",
            sys.executable,
            "-c",
            (
                "import json, os; "
                "print(json.dumps({"
                "'mode': os.environ.get('COMPASS_ADAPTER_MODE'), "
                "'runtime_guard': os.environ.get('COMPASS_RUNTIME_GUARD')"
                "}))"
            ),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {"mode": "runtime", "runtime_guard": "1"}
