#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat >&2 <<'USAGE'
Usage: scripts/compass-agent-auto.sh <agent-command> [args...]

Run Hermes/minimax/Codex-style agent processes with Compass runtime guards.
The wrapped process cannot accidentally bypass adapter action context.
USAGE
  exit 2
fi

export COMPASS_ADAPTER_MODE=runtime
export COMPASS_AGENT_AUTO=1

exec "$@"
