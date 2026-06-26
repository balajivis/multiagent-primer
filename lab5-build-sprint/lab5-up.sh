#!/usr/bin/env bash
# lab5-up.sh — open the tmux layout for the Lab 5 build sprint and reset state.
#
# usage:  ./lab5-up.sh
#   Resets blackboard.md, tasks.json, and project/ from their templates, then
#   opens 4 tmux panes: a live mirror + three role-specialist agents
#   (frontend · backend · tests). Each agent reads its own role file from
#   .claude/agents/<role>.md (named in the kickoff) plus the shared CLAUDE.md.
#
# model:  defaults to haiku (three parallel agents for ~60 min keeps a Pro
#   budget alive). Override for richer code:  LAB5_MODEL=sonnet ./lab5-up.sh
#
# tear down:  ./lab5-down.sh

set -eu
cd "$(dirname "$0")"

MODEL="${LAB5_MODEL:-haiku}"

command -v tmux >/dev/null 2>&1 || { echo "tmux not found. See ../lab1-blackboard/README.md prereqs." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "node not found. Install Node.js v18+ and retry." >&2; exit 1; }

if tmux has-session -t lab5 2>/dev/null; then
  echo "▶ existing lab5 session — attaching (no reset). Run ./lab5-down.sh to reset."
  exec tmux attach -t lab5
fi

# archive previous run
if [ -f tasks.json ] && ! cmp -s tasks.json tasks.template.json; then
  mkdir -p runs
  ts=$(date -u +%Y%m%d-%H%M%SZ)
  cp tasks.json "runs/${ts}-tasks.json"
  [ -f blackboard.md ] && cp blackboard.md "runs/${ts}-blackboard.md"
  echo "▶ archived previous run → runs/${ts}-*"
fi

# reset state from templates
rm -f tasks.json.lock
cp tasks.template.json tasks.json
cp blackboard.template.md blackboard.md
rm -rf project && cp -R project.template project
echo "▶ tasks.json + blackboard.md + project/ reset from templates"

# kickoffs — name the role + point at the role file; CLAUDE.md (auto-loaded) has the protocol
K_FE='You are the FRONTEND specialist. Read .claude/agents/frontend.md, CLAUDE.md, and task.md. Register on the roster, then begin. Claim only frontend/docs tasks via ./task-cli/task. Post performative-tagged entries to blackboard.md.'
K_BE='You are the BACKEND specialist. Read .claude/agents/backend.md, CLAUDE.md, and task.md. Register on the roster, then begin. Claim only backend/db/devops tasks via ./task-cli/task. Post performative-tagged entries to blackboard.md.'
K_TE='You are the TESTS specialist. Read .claude/agents/tests.md, CLAUDE.md, and task.md. Register on the roster, then begin. Claim only tests tasks via ./task-cli/task. Post performative-tagged entries to blackboard.md.'

# window 0 — mirror + 3 agents (tiled); capture stable pane IDs for auto-kickoff
tmux new-session -d -s lab5 -n team './bb-watch.sh'
tmux set-option -t lab5 remain-on-exit on
PANE_BE=$(tmux split-window -h -t lab5:0   -P -F '#{pane_id}' "claude --model $MODEL")
PANE_FE=$(tmux split-window -v -t lab5:0.0 -P -F '#{pane_id}' "claude --model $MODEL")
PANE_TE=$(tmux split-window -v -t "$PANE_BE" -P -F '#{pane_id}' "claude --model $MODEL")
tmux select-layout -t lab5:0 tiled

# auto-kickoff (stagger 5s so roster slots don't collide)
(
  sleep 8
  for pair in "$PANE_FE|$K_FE" "$PANE_BE|$K_BE" "$PANE_TE|$K_TE"; do
    pane="${pair%%|*}"; msg="${pair#*|}"
    tmux send-keys -t "$pane" "$msg"; sleep 0.5; tmux send-keys -t "$pane" Enter; sleep 5
  done
) >/dev/null 2>&1 &

tmux select-window -t lab5:0
tmux select-pane -t lab5:0.1
echo
echo "▶ Build sprint launched (model: $MODEL)."
echo "▶ Attach: tmux attach -t lab5   ·   Detach: Ctrl-b d   ·   Tear down: ./lab5-down.sh"
echo "▶ Debrief after ~60 min:  ./eval-self.sh"
echo
exec tmux attach -t lab5
