# Lab 4 — Human-in-the-Loop & Governance

**Time:** 40 min (5 setup · 30 work across 3 rounds · 5 reflect)
**Lessons it lands:** §10 Human-in-the-Loop · §13 Governance — with §5 (intent, not tokens) and §15 (evaluation) as felt gaps.
**Where this fits:** the fourth lab of the [multi-agent primer](../). Comes after Labs 0–3. **Not optional** — HITL is the one pillar you cannot read your way into. (The earlier real-channel Telegram exercise is now a bonus in [`../lab4-openclaw-optional/`](../lab4-openclaw-optional/).)

---

## What you are about to do

Run a small support-ops desk staffed by agents. Inbound customer requests
become **actions** against a mock company world. Some actions are reversible
(reply, tag); some are not (refund, delete, wire). You will run three rounds
and feel autonomy go from *too much* to *graduated* to *under attack*:

| Round | Setup | What you feel |
|---|---|---|
| 1 · No gate | worker auto-executes everything, **floor off** | the damage of "just trust the agent" — money and records gone, unreviewed |
| 2 · Graduated | worker proposes → **gate** routes by autonomy level → **you** work the approval inbox | low-risk flows without you; risky reaches you with context |
| 3 · Governance stress | 20-item batch with an injection, a wire-fraud, a cross-account delete, a 10× refund | rubber-stamp HITL fails; the floor + audit trail hold |

The lesson is the contrast between the three rounds — and the `audit.log` at the end.

---

## The four autonomy levels (Sheridan / Verplank)

| Level | Who's in the loop | Effect |
|---|---|---|
| `auto` | out of the loop | executes immediately |
| `review` | on the loop | executes **and** logs for post-hoc review |
| `approve` | in the loop | **blocks** until a human decides |
| `block` | — | refused, with a reason |

Two things decide the level. The **gate agent** judges the fuzzy part —
confidence, ambiguity, manipulative intent — **with reasoning, never a keyword
list** (that's the portfolio rule, lived). The **governance floor**, built into
`hitl-cli`, enforces the non-negotiable part on the *typed action class*:
irreversible actions can never auto-execute, no matter what the gate says.
Semantics from the model; hard rules from code.

---

## Prereqs

Same as Lab 1: POSIX shell, `claude`, `tmux`, Node.js v18+. If Lab 1 ran on your
machine, Lab 4 will too. See [Lab 1's README](../lab1-blackboard/README.md#prereqs)
for the macOS / Linux / Windows-via-WSL paths.

---

## Setup (5 min)

Each round is one command:

```
./lab4-up.sh 1     # no gate (floor off)
./lab4-up.sh 2     # graduated autonomy
./lab4-up.sh 3     # governance stress
```

Between rounds: `./lab4-down.sh && ./lab4-up.sh 2`

Each up-call lays out a tmux window:
- **pane 0** — live mirror (`hitl-watch.sh`): queue, routing, world, audit tail
- **pane 1** — the **WORKER** agent
- **pane 2** — the **GATE** agent (rounds 2 & 3)
- **last pane** — your **HUMAN inbox** shell (a cheat-sheet prints there)

tmux survival kit — same as Lab 1: `Ctrl-b` then arrow / `z` (zoom) / `d` (detach).

---

## During each round

Watch the mirror; work the inbox in your shell pane:

```
./hitl-cli/hitl list                       # pending approvals
./hitl-cli/hitl show <Q-id>                # the item + the request that triggered it
./hitl-cli/hitl approve  <Q-id> --by you
./hitl-cli/hitl reject   <Q-id> --reason "..." --by you
./hitl-cli/hitl edit     <Q-id> --to "18"  --by you   # e.g. correct a refund amount, then apply
./hitl-cli/hitl escalate <Q-id> --to senior --by you
./hitl-cli/hitl audit                      # the governance record
```

**Round 1:** there is no inbox to work — just watch the world change. Open
`world-state.json` and `audit.log` after. **Rounds 2–3:** do not rubber-stamp.
Open each item before you decide.

---

## After all three rounds (5 min)

1. **Round 1 vs 2 — what reached you?** Which irreversible actions executed
   unreviewed in Round 1 that Round 2 put in your hands?
2. **Round 3 traps** — which did the *gate* catch, which reached *you*, did any
   get approved? Gate miss or human miss?
3. **The floor** — grep `audit.log` for `FLOOR-OVERRIDE`. What did code catch
   that judgement didn't?
4. **The audit trail** — could a regulator reconstruct every irreversible action
   and its human signature from `audit.log`? *That* is governance, not the
   approvals themselves.

Hold onto answer 4 — it maps directly to the blackboard-classroom big exercise,
where governance and trust become structural.

---

## What good looks like

- Round 1 leaves visible damage in `world-state.json` (negative balances,
  deleted records) with no human in any audit line.
- Round 2: every irreversible action shows an `APPROVE`/`EDIT`/`REJECT` by a
  human *before* it applied; reversible low-risk actions ran `auto`.
- Round 3: the injection is `block`ed, the wire-fraud and cross-account delete
  never apply, and you can point to the exact audit lines that prove it.

---

## Files

```
lab4-hitl-governance/
├── README.md                     ← this file
├── scenario.md                   ← the support-ops world + action vocabulary
├── gate-policy.md                ← the four autonomy levels + how to judge (gate reads this)
├── hitl-cli/hitl                 ← approval-queue + governance engine (Node)
├── requests.normal.json          ← rounds 1 & 2 inbound batch
├── requests.adversarial.json     ← round 3 batch (the traps)
├── world-state.template.json     ← mock company world (reset target)
├── proposals.template.json       ← empty (reset target)
├── queue.template.json           ← empty (reset target)
├── round1-autoexecute/CLAUDE.md  ← round protocols (symlinked active as CLAUDE.md)
├── round2-graduated/CLAUDE.md
├── round3-governance/CLAUDE.md
├── hitl-watch.sh                 ← live terminal mirror
├── lab4-up.sh / lab4-down.sh
└── runs/                         ← auto-archive of each round (proposals/queue/world/audit)
```

---

## Then proceed to Lab 5 (the build sprint).
