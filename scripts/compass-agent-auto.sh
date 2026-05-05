#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat >&2 <<'USAGE'
Usage: scripts/compass-agent-auto.sh <agent-command> [args...]

Run Hermes/minimax/Codex-style agent processes in Compass automatic mode.
The wrapped process cannot accidentally look like a human manual adapter call.
USAGE
  exit 2
fi

export COMPASS_ADAPTER_MODE=agent_auto
export COMPASS_AGENT_AUTO=1

exec "$@"
