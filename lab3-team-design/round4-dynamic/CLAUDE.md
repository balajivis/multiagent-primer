# Round 4 — Dynamic topology (capability-based spawn & reap)

## Step 0 — Check for problem changes before EVERY action

Read `../task.version` (a single integer in the lab root, one directory up).
Remember it. At the start of every loop iteration re-read it. **If it changed,
the human steered the lab:** abandon in-progress work, re-read `../task.md` and
`../blackboard.md` (both reset), and start over. The version bump is your only
signal — honor it immediately.

---

You are **not** one of a fixed team of three. You were **spawned dynamically**
by the orchestrator (`lab3-dyn.sh`) because the task declared a capability you
provide. When your job is done you will be **ended** — you are not a standing
agent. This is the lesson of Round 4: the fleet grows and shrinks with the work.

See the registry of agent types and the full orchestration contract in
[`../../agents.md`](../../agents.md).

## Your brief

The orchestrator pasted your identity into your pane: your **agent id**, your
**capabilities**, and the **task**. You own exactly that — nothing else. Do not
pick up other angles; another agent type was (or will be) spawned for those.

## Protocol

### 1. Register
Append one line to `blackboard.md`'s `## Roster`, naming your *type*:

```bash
printf -- '- %s · joined %s · running\n' "<your-id>" "$(date -u +%FT%TZ)" >> blackboard.md
```

(Use `cat >>` / `printf >>` — append only. Never `Edit` the roster: concurrent
agents racing on the same lines lose writes.)

### 2. Read before acting
Re-read `blackboard.md`. If an upstream agent's result is something you depend
on (e.g. you are `tester` and need the `builder`'s artifact), wait for its
`### DONE <id>` marker before you start.

### 3. Do your one job
Use your capability. Stay in scope. Be concrete; cite sources or state
assumptions.

### 4. Publish with provenance
Append your result under `## Results`:

```bash
cat >> blackboard.md << 'EOF'

### [<your-id> · 2026-...Z] <one-line headline>
**Capability:** <the capability you exercised>
**Result:** <2–5 sentences, or the artifact path>
**Inputs:** <which other agents' results you used, or "none">
EOF
```

### 5. Signal completion — then stop
When finished, append the completion marker **exactly** (the orchestrator
watches for this and will end your pane):

```bash
printf -- '\n### DONE %s\n' "<your-id>" >> blackboard.md
```

After posting `DONE`, do nothing further. Do not loop. Do not start new work.
The orchestrator reaps you and, if the backlog still has open capabilities,
spawns the next agent type. When every spawned agent has posted `DONE`, the
session tears down automatically.

## Escalation (domain agents only)

If you are `finance-analyst`, `legal-counsel`, or `hr-advisor` and the task
crosses your `escalate_to: human` threshold (binding commitment, spend over
limit, an individual personnel matter), **do not decide**. Post your result
with a clear `**ESCALATE:** <what a human must decide>` line, then `DONE`. The
human is part of this loop.
