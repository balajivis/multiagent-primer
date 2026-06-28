#!/usr/bin/env bash
# bb-serve.sh — serve the Lab 5 Build-Sprint live mirror in a browser
#
# Boots bb-server.py (a tiny python3 server) that:
#   - serves bb-mirror.html and live blackboard.md / tasks.json / project.md
#   - accepts POST /api/spec  to set a custom feature spec
#   - accepts POST /api/reset to clear blackboard + tasks + project/
#   - exposes GET /api/state with roster, per-role task status,
#     performative mix, files shipped, and the eval verdict
#
# usage:  ./bb-serve.sh [port]
# default port: 8769

set -eu
cd "$(dirname "$0")"

PORT="${1:-8769}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Ask Claude to install it, or use ./bb-watch.sh (terminal mirror) instead." >&2
  exit 1
fi

URL="http://localhost:${PORT}/bb-mirror.html"

# open browser (best-effort, platform-specific)
if   command -v open      >/dev/null 2>&1; then open      "$URL" 2>/dev/null &
elif command -v xdg-open  >/dev/null 2>&1; then xdg-open  "$URL" 2>/dev/null &
elif command -v wslview   >/dev/null 2>&1; then wslview   "$URL" 2>/dev/null &
fi

exec python3 "$(dirname "$0")/bb-server.py" "$PORT"
