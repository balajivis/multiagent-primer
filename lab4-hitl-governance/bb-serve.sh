#!/usr/bin/env bash
# bb-serve.sh — serve the Lab 4 HITL-desk live mirror in a browser
#
# Boots bb-server.py (a tiny python3 server) that:
#   - serves bb-mirror.html and the live state JSONs (queue, proposals,
#     world-state, audit.log)
#   - accepts POST /api/scenario to set a custom desk scenario (rewrites
#     scenario.md and resets queue/world/audit)
#   - accepts POST /api/reset to clear queue/world/audit only
#
# The existing CLI (hitl-cli/hitl), terminal mirror (hitl-watch.sh), and
# lab4-up.sh launcher keep working unchanged — this is an additive visual
# layer on top of the same files.
#
# usage:  ./bb-serve.sh [port]
# default port: 18768

set -eu
cd "$(dirname "$0")"

PORT="${1:-18768}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3 or use ./hitl-watch.sh (terminal mirror) instead." >&2
  exit 1
fi

URL="http://localhost:${PORT}/bb-mirror.html"

# open browser (best-effort, platform-specific)
if   command -v open      >/dev/null 2>&1; then open      "$URL" 2>/dev/null &
elif command -v xdg-open  >/dev/null 2>&1; then xdg-open  "$URL" 2>/dev/null &
elif command -v wslview   >/dev/null 2>&1; then wslview   "$URL" 2>/dev/null &
fi

exec python3 "$(dirname "$0")/bb-server.py" "$PORT"
