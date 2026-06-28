#!/usr/bin/env bash
# lab3-down.sh — kill the Lab 3 tmux session
#
# Also snapshots the current board to runs/round-N.md (if a round is
# active) so the bb-server.py comparison panel can show its output
# even before the next round starts.

set -eu
cd "$(dirname "$0")"

if [ -f .current-round ] && [ -s blackboard.md ] && ! cmp -s blackboard.md blackboard.template.md; then
  CUR=$(cat .current-round 2>/dev/null || true)
  if [ -n "$CUR" ]; then
    mkdir -p runs
    cp blackboard.md "runs/round-${CUR}.md"
    echo "▶ snapshot → runs/round-${CUR}.md"
  fi
fi

tmux kill-session -t lab3 2>/dev/null && echo "lab3 session killed." || echo "no lab3 session running."
