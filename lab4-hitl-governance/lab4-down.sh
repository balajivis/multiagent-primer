#!/usr/bin/env bash
set -eu
tmux kill-session -t lab4 2>/dev/null && echo "lab4 session killed." || echo "no lab4 session running."
rm -f "$(dirname "$0")/.hitl.lock"
