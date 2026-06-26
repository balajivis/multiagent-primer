#!/usr/bin/env bash
set -eu
tmux kill-session -t lab5 2>/dev/null && echo "lab5 session killed." || echo "no lab5 session running."
rm -f "$(dirname "$0")/tasks.json.lock"
