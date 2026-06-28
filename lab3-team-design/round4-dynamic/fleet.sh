#!/usr/bin/env bash
# fleet.sh — live view of dynamically spawned agents for Lab 3 Round 4.
#
# Reads ../.dyn-state (written by lab3-dyn.sh) and shows each agent's
# status as it is spawned (running) and reaped (done). Also tails the
# board's Results. This pane IS the mirror — you watch the fleet grow
# and shrink.
#
# usage: ./fleet.sh   (run from the lab root; state file is ./.dyn-state)

set -u
STATE="${1:-.dyn-state}"
BOARD="${2:-blackboard.md}"
INTERVAL="${REFRESH:-1}"

R=$'\033[0m'; B=$'\033[1m'; D=$'\033[2m'
G=$'\033[32m'; Y=$'\033[33m'; C=$'\033[36m'

render() {
  local hr running=0 done=0
  hr=$(date -u +%TZ)
  printf '%sLAB 3 · ROUND 4 — DYNAMIC FLEET%s   %s%s%s\n' "$B" "$R" "$D" "$hr" "$R"
  printf '%s──────────────────────────────────────────────%s\n' "$D" "$R"

  if [ ! -f "$STATE" ] || [ ! -s "$STATE" ]; then
    printf '  %sno agents spawned yet%s\n' "$D" "$R"
  else
    while IFS=$'\t' read -r id st model pane; do
      [ -z "${id:-}" ] && continue
      if [ "$st" = done ]; then
        printf '  %s✓%s %-16s %s[%s]%s %sended%s\n' "$G" "$R" "$id" "$D" "$model" "$R" "$G" "$R"
        done=$((done+1))
      else
        printf '  %s●%s %-16s %s[%s]%s %srunning%s\n' "$C" "$R" "$id" "$D" "$model" "$R" "$Y" "$R"
        running=$((running+1))
      fi
    done < "$STATE"
    printf '%s──────────────────────────────────────────────%s\n' "$D" "$R"
    printf '  %d running · %d ended\n' "$running" "$done"
    if [ -f .dyn-alldone ]; then
      printf '  %sALL DONE%s — results below · run %s./lab3-dyn.sh down%s to exit\n' "$G" "$R" "$B" "$R"
    fi
  fi

  printf '\n%sRecent results%s\n' "$D" "$R"
  if [ -f "$BOARD" ]; then
    grep -E '^### \[' "$BOARD" 2>/dev/null | tail -6 | sed 's/^### //' | while IFS= read -r line; do
      printf '  %s\n' "${line:0:64}"
    done
  fi
}

trap 'tput cnorm 2>/dev/null; printf "\033[?1049l"; exit 0' INT TERM
tput civis 2>/dev/null || true
printf '\033[?1049h'; clear
while true; do
  frame=$(render)
  printf '\033[H%s\033[J' "$frame"
  sleep "$INTERVAL"
done
