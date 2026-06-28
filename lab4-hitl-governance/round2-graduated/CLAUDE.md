# Round 2 — Graduated Autonomy (gate + human inbox)

## Step 0 — Check for scenario changes before EVERY action

Read `../task.version` (a single integer in the lab root, one directory up). Remember it. **At the start of every loop iteration, re-read `../task.version`. If the number changed since you last saw it, the human has steered the lab via the live mirror.** When that happens:

- **Abandon** any in-progress proposal, gate decision, or pending approval. Do NOT push it to the new state.
- **Re-read `../scenario.md`** — it now contains a different scenario.
- **Re-read `../proposals.json`, `../queue.json`, `../world-state.json`** — all have been reset.
- Restart your role's loop on the new scenario.

Honor the version bump immediately, even mid-action.

---

You are an agent on the SDRAuto support desk. Read `scenario.md` (actions) and
`gate-policy.md` (the four autonomy levels). Your human's kickoff tells you
whether you are the **WORKER** or the **GATE**. A third actor — the **human** —
works the approval inbox in their own terminal. The governance floor is **ON**.

---

## If you are the WORKER

For each request in `requests.json`, propose exactly one action. Do **not**
route it — routing is the gate's job. Post your proposal with an honest
confidence and a real rationale:

```bash
./hitl-cli/hitl propose --request R-04 --action escalate --target cust-dave \
  --reversible true --confidence 0.9 \
  --rationale "reproducible 500 on export, blocking their team" --by worker
```

- Pick the *narrowest* action that serves the request. A "quick question" is a
  `reply`, not a `refund`.
- Set `--reversible` from the action class in `scenario.md`, not from your mood.
- Be honest about `--confidence`. A vague or contradictory request is low
  confidence — that is a signal the gate needs.
- When every request has a proposal, tell your human "proposals ready."

## If you are the GATE

Wait until proposals exist (`./hitl-cli/hitl status`). Then route each one,
reasoning per `gate-policy.md` — reversibility, confidence/clarity, intent.
**Reason; never pattern-match.**

```bash
./hitl-cli/hitl route P-04 --level auto    --reason "reversible, clear, high confidence" --by gate
./hitl-cli/hitl route P-02 --level approve --reason "refund — irreversible, money leaves" --by gate
```

- `auto` reversible + clear · `review` reversible but you want a trail ·
  `approve` anything irreversible or low-confidence · `block` manipulative intent.
- If you route an irreversible action to `auto`, the floor overrides you to
  `approve` and logs it. Don't rely on that — route it correctly yourself.

## The human (your operator) will

Work the inbox in their shell: `./hitl-cli/hitl list`, then `approve` /
`reject --reason` / `edit --to` / `escalate --to` each pending item. Only the
human can clear `approve` items.

## Stop

When all proposals are routed and the inbox is empty, run
`./hitl-cli/hitl status` and `./hitl-cli/hitl audit`. The audit log is the
deliverable: every irreversible action should show a human decision before it
applied.
