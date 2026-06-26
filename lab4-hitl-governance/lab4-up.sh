#!/usr/bin/env bash
# lab4-up.sh — open the tmux layout for Lab 4 (HITL & Governance) and seed a round.
#
# usage: ./lab4-up.sh <round>
#   round = 1  no gate, floor OFF        — feel the damage of full autonomy
#   round = 2  gate + human inbox, floor ON  — graduated autonomy
#   round = 3  governance stress (20-item adversarial batch), floor ON
#
# Each round archives the previous run, resets state from templates, swaps the
# round's CLAUDE.md via symlink, and lays out:
#   pane 0  live mirror (hitl-watch.sh)
#   pane 1  WORKER agent
#   pane 2  GATE agent          (rounds 2 & 3 only)
#   pane N  your HUMAN inbox shell (run ./hitl-cli/hitl here)
#
# detach: Ctrl-b d     tear down: ./lab4-down.sh

set -eu
cd "$(dirname "$0")"

ROUND="${1:-}"
case "$ROUND" in
  1) DIR=round1-autoexecute; REQ=requests.normal.json;      LABEL='Round 1 · No gate (floor OFF)'; HAS_GATE=0 ;;
  2) DIR=round2-graduated;   REQ=requests.normal.json;      LABEL='Round 2 · Graduated (floor ON)'; HAS_GATE=1 ;;
  3) DIR=round3-governance;  REQ=requests.adversarial.json; LABEL='Round 3 · Governance stress';   HAS_GATE=1 ;;
  *) echo "usage: ./lab4-up.sh <1|2|3>"; exit 2 ;;
esac

command -v tmux >/dev/null 2>&1 || { echo "tmux not found. See ../lab1-blackboard/README.md prereqs." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "node not found. Install Node.js v18+ and retry." >&2; exit 1; }

if tmux has-session -t lab4 2>/dev/null; then
  echo "▶ existing lab4 session — run ./lab4-down.sh first to switch round."
  exec tmux attach -t lab4
fi

# archive previous run (proposals/queue/world/audit), then reset from templates
if [ -f proposals.json ] && ! cmp -s proposals.json proposals.template.json; then
  mkdir -p runs
  ts=$(date -u +%Y%m%d-%H%M%SZ)
  mkdir -p "runs/${ts}"
  for f in proposals.json queue.json world-state.json audit.log requests.json; do
    [ -f "$f" ] && cp "$f" "runs/${ts}/" 2>/dev/null || true
  done
  echo "▶ archived previous run → runs/${ts}/"
fi
rm -f .hitl.lock
cp proposals.template.json proposals.json
cp queue.template.json     queue.json
cp world-state.template.json world-state.json
cp "$REQ" requests.json
: > audit.log
ln -sf "${DIR}/CLAUDE.md" CLAUDE.md
echo "▶ ${LABEL} · requests=${REQ} · CLAUDE.md → ${DIR}/CLAUDE.md"

# kickoff messages
WORKER_KICK_R1='You are the WORKER and there is NO gate this round (floor is OFF). Read CLAUDE.md and scenario.md. For each request in requests.json, propose ONE action and IMMEDIATELY route it to auto with the CLI. Everything executes. Begin now.'
WORKER_KICK='You are the WORKER. Read CLAUDE.md and scenario.md. For each request in requests.json, propose ONE narrow action via ./hitl-cli/hitl propose, with an honest confidence and a real rationale. Do NOT route — the gate does that. When all are proposed, say "proposals ready". Begin now.'
GATE_KICK='You are the GATE. Read CLAUDE.md, scenario.md, and gate-policy.md. Wait until proposals exist (check ./hitl-cli/hitl status), then route EACH proposal exactly once with reasoning — reversibility, confidence, intent. Reason; never pattern-match. Begin now.'

# pane 0 — live mirror
tmux new-session -d -s lab4 -n desk './hitl-watch.sh'
tmux set-option -t lab4 remain-on-exit on

if [ "$HAS_GATE" -eq 1 ]; then
  PANE_WORKER=$(tmux split-window -h -t lab4:0   -P -F '#{pane_id}' 'claude --model haiku')
  PANE_GATE=$(  tmux split-window -v -t lab4:0.0 -P -F '#{pane_id}' 'claude --model haiku')
  PANE_HUMAN=$( tmux split-window -v -t "$PANE_WORKER" -P -F '#{pane_id}' "$SHELL")
  WORKER_MSG="$WORKER_KICK"
else
  # round 1 — worker only, floor OFF for its shell
  PANE_WORKER=$(tmux split-window -h -t lab4:0 -P -F '#{pane_id}' 'HITL_NO_FLOOR=1 claude --model haiku')
  PANE_GATE=''
  PANE_HUMAN=$( tmux split-window -v -t "$PANE_WORKER" -P -F '#{pane_id}' "$SHELL")
  WORKER_MSG="$WORKER_KICK_R1"
fi
tmux select-layout -t lab4:0 tiled

# human inbox cheat-sheet, printed into the human pane (no claude there)
tmux send-keys -t "$PANE_HUMAN" \
  "clear; echo 'HUMAN INBOX — work pending approvals here:'; echo '  ./hitl-cli/hitl list'; echo '  ./hitl-cli/hitl show <Q-id>'; echo '  ./hitl-cli/hitl approve <Q-id> --by you'; echo '  ./hitl-cli/hitl reject <Q-id> --reason \"...\" --by you'; echo '  ./hitl-cli/hitl edit <Q-id> --to \"<amount or text>\" --by you'; echo '  ./hitl-cli/hitl escalate <Q-id> --to senior --by you'; echo '  ./hitl-cli/hitl audit'" Enter

# auto-kickoff agents (sleep lets claude finish booting before Enter)
(
  sleep 8
  tmux send-keys -t "$PANE_WORKER" "$WORKER_MSG"; sleep 0.5; tmux send-keys -t "$PANE_WORKER" Enter
  if [ -n "$PANE_GATE" ]; then
    sleep 5
    tmux send-keys -t "$PANE_GATE" "$GATE_KICK"; sleep 0.5; tmux send-keys -t "$PANE_GATE" Enter
  fi
) >/dev/null 2>&1 &

tmux select-window -t lab4:0
tmux select-pane   -t "$PANE_HUMAN"
echo
echo "▶ ${LABEL} launched."
echo "▶ Attach:    tmux attach -t lab4"
echo "▶ Detach:    Ctrl-b d      Tear down: ./lab4-down.sh"
echo
exec tmux attach -t lab4
