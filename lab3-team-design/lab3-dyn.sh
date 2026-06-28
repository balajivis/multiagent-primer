#!/usr/bin/env bash
# lab3-dyn.sh — Lab 3, Round 4: DYNAMIC capability-based agent startup.
#
# Instead of a fixed 3-agent topology, you describe a task and the
# capabilities it needs. The orchestrator spawns ONLY the matching
# agent types, each in its own tmux pane, and ENDS each one the moment
# it posts "### DONE <id>" to the board. The fleet grows and shrinks
# with the work — that is the lesson of Round 4.
#
# usage:
#   ./lab3-dyn.sh "Ship paid API access" implement,finance,legal,review
#   ./lab3-dyn.sh "Plan a product launch"            # interactive: asks for needs
#   ./lab3-dyn.sh --dry-run "task" needs             # show the spawn plan, don't launch
#   ./lab3-dyn.sh down                               # tear the session down
#   ./lab3-dyn.sh caps                               # list capabilities & agents
#
# The agent registry below mirrors ../agents.md (single source of truth
# is that file; this is its runnable form). Edit both together.

set -eu
cd "$(dirname "$0")"
SESSION=lab3dyn
STATE=.dyn-state
BOARD=blackboard.md
TEMPLATE=round4-dynamic/board.template.md

# ── Registry: id <TAB> caps(comma) <TAB> triggers(comma) <TAB> model <TAB> role ──
# caps     = everything the agent can do (documented for matching/handoff)
# triggers = the caps that actually cause this agent to be SPAWNED. Domain
#            specialists trigger only on their domain tag, so a generic
#            "review"/"research" request won't drag legal/finance/hr in.
# (keep in sync with ../agents.md)
REGISTRY=$(printf '%s\n' \
'researcher	research,summarize	research,summarize	sonnet	Gather facts you can cite; post 2-4 sentence findings with sources. Do not implement or decide.' \
'planner	decompose,sequence	decompose,sequence	opus	Turn the goal into an ordered backlog of sized subtasks, each tagged with the capabilities it needs.' \
'builder	implement,refactor	implement,refactor	sonnet	Produce the artifact for this task. Stay in scope. Publish the artifact path + one-line summary.' \
'tester	verify,reproduce	verify,reproduce	haiku	Verify the artifact against expected behavior; enumerate edge cases. Post pass/fail with evidence.' \
'reviewer	review,security	review,security	opus	Critique the artifact for correctness, quality, and trust/safety. Post findings with severity; recommend, do not rewrite.' \
'scribe	document	document	haiku	Write the human-facing explanation of what shipped, from published results. Match existing voice.' \
'synthesizer	synthesize,summarize	synthesize	opus	Read every published result, resolve conflicts with attribution, produce the single final decision. Spawned last.' \
'finance-analyst	finance,research	finance	opus	Assess cost, ROI, pricing, financial risk. Show numbers + assumptions. ESCALATE any spend over threshold to a human.' \
'legal-counsel	legal,review	legal	opus	Review for compliance/contract/liability/licensing risk; cite the clause or regulation. ESCALATE anything binding to a human.' \
'hr-advisor	hr,review	hr	sonnet	Advise on policy, hiring fairness, conduct, employment-law. ESCALATE any individual personnel matter to a human.')

reg_line()    { printf '%s\n' "$REGISTRY" | awk -F'\t' -v id="$1" '$1==id{print;exit}'; }
reg_caps()    { reg_line "$1" | cut -f2; }
reg_trigger() { reg_line "$1" | cut -f3; }
reg_model()   { reg_line "$1" | cut -f4; }
reg_prompt()  { reg_line "$1" | cut -f5; }
all_ids()     { printf '%s\n' "$REGISTRY" | cut -f1; }

# alias friendly words -> canonical capability tokens
canon() {
  case "$1" in
    plan|decompose) echo "decompose sequence" ;;
    build|code|implement) echo "implement" ;;
    test|qa|verify) echo "verify" ;;
    repro|reproduce) echo "reproduce" ;;
    doc|docs|document) echo "document" ;;
    synth|synthesize) echo "synthesize" ;;
    sec|security) echo "security" ;;
    *) echo "$1" ;;
  esac
}

usage() { sed -n '2,20p' "$0"; exit "${1:-0}"; }

# ── subcommands ──────────────────────────────────────────────────────
case "${1:-}" in
  ''|-h|--help) usage 0 ;;
  caps)
    echo "Agents · capabilities (spawn triggers in [brackets]):"
    while IFS=$'\t' read -r id caps trig model _; do
      printf '  %-16s %-22s spawns on [%s]\n' "$id" "$caps" "$trig"
    done <<EOF
$REGISTRY
EOF
    exit 0 ;;
  down)
    if [ -f .current-round ] && [ -s "$BOARD" ] && ! cmp -s "$BOARD" "$TEMPLATE"; then
      mkdir -p runs; cp "$BOARD" runs/round-4.md; echo "▶ snapshot → runs/round-4.md"
    fi
    rm -f "$STATE" .dyn-alldone
    tmux kill-session -t "$SESSION" 2>/dev/null && echo "$SESSION killed." || echo "no $SESSION session."
    exit 0 ;;
esac

DRY=0
if [ "${1:-}" = "--dry-run" ]; then DRY=1; shift; fi

TASK="${1:-}"
[ -z "$TASK" ] && { echo "error: no task given." >&2; usage 2; }
NEEDS="${2:-}"
if [ -z "$NEEDS" ]; then
  printf 'Capabilities this task needs (comma-separated)\n  e.g. research,plan,build,verify,review,document,finance,legal,hr\n> '
  read -r NEEDS
fi
[ -z "$NEEDS" ] && { echo "error: no capabilities given." >&2; exit 2; }

# ── expand needs -> canonical set ────────────────────────────────────
WANT=""
OLDIFS=$IFS; IFS=','
for raw in $NEEDS; do
  raw=$(printf '%s' "$raw" | tr -d ' ')
  [ -z "$raw" ] && continue
  for c in $(canon "$raw"); do WANT="$WANT $c"; done
done
IFS=$OLDIFS

# ── match: an agent is spawned if any of its TRIGGER caps is wanted ───
MATCHED=""
for id in $(all_ids); do
  trig=$(reg_trigger "$id")
  hit=0
  OLDIFS=$IFS; IFS=,
  for cap in $trig; do
    case " $WANT " in *" $cap "*) hit=1 ;; esac
  done
  IFS=$OLDIFS
  [ "$hit" = 1 ] && MATCHED="$MATCHED $id"
done
MATCHED=$(printf '%s' "$MATCHED" | tr ' ' '\n' | sed '/^$/d')

if [ -z "$MATCHED" ]; then
  echo "No agent provides any of:$WANT" >&2
  echo "Run './lab3-dyn.sh caps' to see what's available." >&2
  exit 1
fi

echo "▶ Task:  $TASK"
echo "▶ Needs:$WANT"
echo "▶ Will spawn:"
for id in $MATCHED; do printf '    %-16s [%s]  caps: %s\n' "$id" "$(reg_model "$id")" "$(reg_caps "$id")"; done

if [ "$DRY" = 1 ]; then echo "(dry run — nothing launched)"; exit 0; fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found — showed the spawn plan above. Install tmux to launch agents." >&2
  exit 1
fi
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "▶ existing $SESSION — attaching (run ./lab3-dyn.sh down to start over)"
  exec tmux attach -t "$SESSION"
fi

# ── reset board + task, swap CLAUDE.md, bump version ─────────────────
if [ -s "$BOARD" ] && ! cmp -s "$BOARD" "$TEMPLATE" 2>/dev/null; then
  mkdir -p runs; ts=$(date -u +%Y%m%d-%H%M%SZ)
  cp "$BOARD" "runs/${ts}-prev.md"; echo "▶ archived previous board → runs/${ts}-prev.md"
fi
cp "$TEMPLATE" "$BOARD"
printf '%s\n' "$TASK" > task.md
[ -f task.version ] && v=$(cat task.version 2>/dev/null || echo 0) || v=0
echo $((v + 1)) > task.version
ln -sf round4-dynamic/CLAUDE.md CLAUDE.md
printf '4\n' > .current-round
rm -f .dyn-alldone; : > "$STATE"

# ── spawn: fleet view in pane 0, one pane per matched agent ──────────
tmux new-session -d -s "$SESSION" -n fleet "./round4-dynamic/fleet.sh"
for id in $MATCHED; do
  model=$(reg_model "$id")
  pane=$(tmux split-window -t "${SESSION}:0" -P -F '#{pane_id}' "claude --model ${model}")
  printf '%s\t%s\t%s\t%s\n' "$id" running "$model" "$pane" >> "$STATE"
  tmux select-layout -t "${SESSION}:0" tiled >/dev/null
done

# ── kickoff: anchor each agent in its identity + the task ────────────
(
  sleep 8
  while IFS=$'\t' read -r id st model pane; do
    [ -z "$id" ] && continue
    caps=$(reg_caps "$id"); role=$(reg_prompt "$id")
    msg="You are the '${id}' agent, spawned dynamically for ONE job. Read round4-dynamic/CLAUDE.md and task.md. Your capabilities: ${caps}. Role: ${role} TASK: ${TASK}. Register on the roster, do the job, append your result under ## Results with provenance, then append exactly the line '### DONE ${id}' and STOP."
    tmux send-keys -t "$pane" "$msg"; sleep 0.5
    tmux send-keys -t "$pane" Enter; sleep 5
  done < "$STATE"
) >/dev/null 2>&1 &

# ── reaper: end each agent when it posts DONE; tear down when all done ─
(
  while true; do
    sleep 2
    [ -f "$STATE" ] || break
    lines=""; alldone=1
    while IFS=$'\t' read -r id st model pane; do
      [ -z "$id" ] && continue
      if [ "$st" = running ] && grep -q "^### DONE ${id}\$" "$BOARD" 2>/dev/null; then
        tmux kill-pane -t "$pane" 2>/dev/null || true
        tmux select-layout -t "${SESSION}:0" tiled >/dev/null 2>&1 || true
        st=done
      fi
      [ "$st" = running ] && alldone=0
      lines="${lines}${id}	${st}	${model}	${pane}
"
    done < "$STATE"
    printf '%s' "$lines" > "$STATE"
    if [ "$alldone" = 1 ]; then
      touch .dyn-alldone
      mkdir -p runs; cp "$BOARD" runs/round-4.md
      break
    fi
  done
) >/dev/null 2>&1 &

tmux select-window -t "${SESSION}:0"
exec tmux attach -t "$SESSION"
