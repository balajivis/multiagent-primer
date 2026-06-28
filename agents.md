# Agent Registry — dynamically started agents

> **Classroom exercise.** A registry of agent *types*, each with distinct
> capabilities. No agent is running at the start. An **orchestrator** reads this
> file, looks at the open tasks, and **spawns only the agent types whose
> capabilities a task actually needs** — then tears them down when the work
> drains. This is capability-based allocation (Pillar 2) + dynamic topology
> (Pillar 3) in the smallest possible form.

---

## Capability vocabulary (abstract — framework-neutral)

A task declares what it `needs`; an agent advertises what it `can` do. Matching
is set intersection over this shared vocabulary — nothing more.

| Capability    | Meaning |
|---------------|---------|
| `research`    | Gather facts from sources; cite them. |
| `summarize`   | Compress many inputs into a gist. |
| `decompose`   | Break a goal into ordered, sized subtasks. |
| `sequence`    | Order subtasks by dependency and risk. |
| `implement`   | Produce the actual artifact (code, doc, asset). |
| `refactor`    | Improve an existing artifact without changing behavior. |
| `verify`      | Test against expected behavior; find edge cases. |
| `reproduce`   | Reliably trigger a reported failure. |
| `review`      | Critique an artifact for correctness/quality. |
| `security`    | Critique specifically for trust/safety/abuse. |
| `document`    | Write the human-facing explanation of what shipped. |
| `synthesize`  | Merge multiple agents' outputs into one decision. |

**Domain capabilities** — these tag a task by *subject matter*, not lifecycle
stage. A task can carry both, e.g. `needs: [review, legal]` → it needs a review
*and* the review must be a legal one.

| Capability  | Meaning |
|-------------|---------|
| `finance`   | Budget, cost, ROI, pricing, and financial-risk analysis. |
| `legal`     | Compliance, contracts, liability, licensing, regulatory review. |
| `hr`        | People, policy, hiring, conduct, and employment-law questions. |

---

## Orchestration contract (how "dynamically started" works)

The orchestrator runs this loop. It is the entire mechanism.

```
1. SCAN    read the open backlog. Each task has: id, needs[], status.
2. MATCH   for each OPEN task, find agent types where
              (task.needs ∩ agent.capabilities) is non-empty.
3. SPAWN   start the matched agent type IF it is not already running and
           the live count for that type < max_instances.
           Pass the task id and the agent's `prompt` as its brief.
4. CLAIM   the spawned agent atomically claims the task (status: claimed).
5. PUBLISH on completion the agent writes its result to shared state
           (status: done) WITH provenance (which agent, which inputs).
6. REAP    when an agent has no remaining matchable OPEN task, stop it.
7. REPEAT  until every task is done. The set of live agents grows and
           shrinks with the work — that is the "dynamic" part.
```

**Rules of the game (the lesson):**
- *No standing fleet.* An agent that isn't needed must not be running.
- *Capability, not speed.* A task goes to a type that `can` do it, not the
  first idle agent. (Contrast Lab 2 Round 1's first-claim.)
- *Bound the fan-out.* `max_instances` caps each type so a hot capability
  can't starve the rest.
- *Publish with provenance.* Every result names its author and inputs, so the
  synthesizer (and the next agent) can trust it.

---

## Registry

Each entry is one agent *type*. `spawn_when` is the predicate the orchestrator
evaluates in step 2; `max_instances` is the cap from step 3.

### researcher
```yaml
id:            researcher
capabilities:  [research, summarize]
model:         sonnet
max_instances: 2
spawn_when:    task.needs ∩ {research, summarize} ≠ ∅
prompt: >
  You gather facts for one task. Use only what you can cite. Post 2–4 sentence
  findings with sources to shared state. Do not implement or decide — feed the
  planner and synthesizer.
```

### planner
```yaml
id:            planner
capabilities:  [decompose, sequence]
model:         opus
max_instances: 1
spawn_when:    task.needs ∩ {decompose, sequence} ≠ ∅
prompt: >
  You turn a goal into an ordered backlog: sized subtasks, each tagged with the
  capabilities it needs (from the vocabulary). Order by dependency and risk.
  Output the backlog; do not build anything.
```

### builder
```yaml
id:            builder
capabilities:  [implement, refactor]
model:         sonnet
max_instances: 3
spawn_when:    task.needs ∩ {implement, refactor} ≠ ∅
prompt: >
  You produce the artifact for exactly one subtask. Stay in scope. When done,
  publish the artifact path and a one-line summary with provenance. Hand off to
  a tester — do not mark your own work verified.
```

### tester
```yaml
id:            tester
capabilities:  [verify, reproduce]
model:         haiku
max_instances: 2
spawn_when:    task.needs ∩ {verify, reproduce} ≠ ∅
prompt: >
  You verify a builder's artifact against expected behavior and enumerate edge
  cases. If a failure is reported, reproduce it reliably first. Post pass/fail
  with evidence; never edit the artifact yourself.
```

### reviewer
```yaml
id:            reviewer
capabilities:  [review, security]
model:         opus
max_instances: 1
spawn_when:    task.needs ∩ {review, security} ≠ ∅
prompt: >
  You critique an artifact for correctness, quality, and trust/safety. Be
  specific and adversarial. Post findings with severity; recommend, don't
  rewrite. A clean review is a valid result.
```

### scribe
```yaml
id:            scribe
capabilities:  [document]
model:         haiku
max_instances: 1
spawn_when:    task.needs ∩ {document} ≠ ∅
prompt: >
  You write the human-facing explanation of what shipped, from the published
  artifacts and results in shared state. Match the project's existing voice.
```

### synthesizer
```yaml
id:            synthesizer
capabilities:  [synthesize, summarize]
model:         opus
max_instances: 1
spawn_when:    all tasks done OR a decision needs multiple agents' outputs merged
prompt: >
  You are spawned last. Read every published result, resolve conflicts with
  attribution, and produce the single final decision/brief. Do not re-do work —
  weigh it.
```

---

## Domain specialists

Same schema, but matched by subject matter. These agents are advisory: they
critique and flag, they don't build. Each carries an `escalate_to` field — when
the stakes cross a threshold they hand off to a human (Pillar 13, HITL) instead
of deciding alone.

### finance-analyst
```yaml
id:            finance-analyst
capabilities:  [finance, research]
model:         opus
max_instances: 1
spawn_when:    task.needs ∩ {finance} ≠ ∅
escalate_to:   human  # any spend/commitment above the configured threshold
prompt: >
  You assess the financial dimension of one task: cost, ROI, pricing, and
  financial risk. Show your numbers and assumptions. Post a recommendation with
  a confidence level; if a commitment exceeds the spend threshold, escalate to a
  human rather than approving it. You advise — you do not authorize spend.
```

### legal-counsel
```yaml
id:            legal-counsel
capabilities:  [legal, review]
model:         opus
max_instances: 1
spawn_when:    task.needs ∩ {legal} ≠ ∅
escalate_to:   human  # binding obligations, novel liability, regulatory ambiguity
prompt: >
  You review one task for compliance, contractual, liability, and licensing
  risk. Cite the specific clause, license, or regulation. Output: risk level +
  required changes. For anything binding or genuinely ambiguous, flag for human
  counsel — this output is guidance, not legal advice.
```

### hr-advisor
```yaml
id:            hr-advisor
capabilities:  [hr, review]
model:         sonnet
max_instances: 1
spawn_when:    task.needs ∩ {hr} ≠ ∅
escalate_to:   human  # individual personnel matters, conduct, terminations
prompt: >
  You advise on the people dimension: policy, hiring fairness, conduct, and
  employment-law considerations. Keep guidance general and policy-level. Any
  matter about a specific individual goes to a human — never adjudicate a
  personnel case autonomously.
```

---

## Worked example (what a run looks like)

Backlog:

```
T1  "Find best inter-agent protocol for our use case"   needs: [research]
T2  "Plan the migration"                                needs: [decompose, sequence]
T3  "Write the adapter"                                 needs: [implement]
T4  "Test the adapter"                                  needs: [verify]
T5  "Document the change"                                needs: [document]
```

Timeline (live agents in brackets):

```
t0  T1 open            → spawn researcher              [researcher]
t1  T1 done, T2 open   → reap researcher, spawn planner [planner]
t2  T2 done → emits T3,T4,T5; reap planner; spawn builder for T3   [builder]
t3  T3 done → reap builder, spawn tester for T4        [tester]
t4  T4 done → reap tester, spawn scribe for T5         [scribe]
t5  T5 done → spawn synthesizer for final brief        [synthesizer]
t6  all done → reap synthesizer                         []
```

Never more than one or two agents alive at once, each chosen by capability —
that is the whole point.

---

## Discussion prompts (for the class)

1. T3 splits into three independent files. How does `max_instances: 3` on
   `builder` change the timeline? When does more parallelism stop helping?
2. A task arrives with `needs: [implement, security]`. No single type matches
   both. What should the orchestrator do — spawn two, or is the backlog wrong?
3. The reviewer rejects T3. Who gets re-spawned, and what new task is created?
4. Where is the bottleneck if `planner` has `max_instances: 1` and ten goals
   arrive at once?
5. A task is `needs: [implement, finance, legal]` — "ship paid API access."
   Which agents spawn, in what order, and who blocks whom? When should the
   `escalate_to: human` fire, and who waits on that human?
6. Domain agents are advisory and capped at one instance. What failure mode
   appears if a single `legal-counsel` becomes a hard dependency for every
   task in a large backlog?
