#!/usr/bin/env bash
# bb-serve.sh — serve the Lab 3 Team-Design live mirror in a browser
#
# Boots bb-server.py (a tiny python3 stdlib server) that:
#   - serves bb-mirror.html and the live blackboard.md
#   - accepts POST /api/problem to set a custom team-design problem
#   - accepts POST /api/reset to clear the active board
#   - serves GET /api/state with per-round comparison data
#
# usage:  ./bb-serve.sh [round] [port]
# default port: 8767  (lab1 = 8765, lab2 = 8766, lab3 = 8767 — no collisions)

set -eu
cd "$(dirname "$0")"

ROUND="${1:-}"
PORT="${2:-8767}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Ask Claude to install it, or use ./bb-watch.sh (terminal mirror) instead." >&2
  exit 1
fi

URL="http://localhost:${PORT}/bb-mirror.html"
[ -n "$ROUND" ] && URL="${URL}?round=${ROUND}"

# open browser (best-effort, platform-specific)
if   command -v open      >/dev/null 2>&1; then open      "$URL" 2>/dev/null &
elif command -v xdg-open  >/dev/null 2>&1; then xdg-open  "$URL" 2>/dev/null &
elif command -v wslview   >/dev/null 2>&1; then wslview   "$URL" 2>/dev/null &
fi

# bb-server.py accepts (PORT) or (ROUND PORT). We pass both through so
# the round shows up in the server's startup log.
if [ -n "$ROUND" ]; then
  exec python3 "$(dirname "$0")/bb-server.py" "$ROUND" "$PORT"
else
  exec python3 "$(dirname "$0")/bb-server.py" "$PORT"
fi
