# Multi-Agent Primer

A **6-lab, ~4-hour primer** that teaches the *primitives* of multi-agent systems by having students feel them — duplication, races, staleness, allocation bias, topology mismatch, real-channel friction — using nothing but markdown files, a tiny task-cli, and a few Claude Code sessions per laptop.

For the design rationale, the 16-pillar mapping, and what NOT to do here, read [`PROJECT.md`](./PROJECT.md). This README is the student-and-instructor entry point.

---

## The labs

Run them in order. Each lab's own README has setup, prompts, and a post-mortem.

| Lab | Time | Pain it teaches | Pillars |
|---|---|---|---|
| [**0 — Workflow Rhythm**](./lab0-workflow/) | 45 min | *(no pain — sets the baseline)* a single agent + good roles already ships real work | sets up §2, §16 |
| [**1 — The Blackboard**](./lab1-blackboard/) | 25 min | Three peers, one shared file, no roles → duplication, races, synthesis bottleneck | §1, §4 |
| [**2 — Task Allocation**](./lab2-task-allocation/) | 25 min | Same agents through two rounds (first-claim → contract-net) — Lab 1 already covered free-for-all | §12, surfaces §6 |
| [**3 — Team Design**](./lab3-team-design/) | 35 min | Same task, three topologies (supervisor / pipeline / swarm) — what changes? | §3, surfaces §7, §15 |
| [**4 — HITL & Governance**](./lab4-hitl-governance/) | 40 min | Worker proposes → a gate agent routes by autonomy level → you work the approval inbox; then governance under attack (injection, wire-fraud, rubber-stamp) | §10, §13, surfaces §5, §15 |
| [**5 — Build Sprint** *(capstone)*](./lab5-build-sprint/) | 75 min | Three role-specialized agents (frontend / backend / tests) ship real working code with typed performatives, atomic claims, and a 3-tier eval | §1, 2, 3, 4, 5, 9, 15 |
| [**Bonus — Real Channel** *(optional)*](./lab4-openclaw-optional/) | 45 min | One agent on a real Telegram bot — HITL/governance on a live channel | §10, §13 (live channel) |

**Total core (Labs 0 → 1 → 2 → 3 → 4 → 5):** ~245 min (~4 hr). **Plus the optional openclaw bonus:** +45 min.

> Labs now run in natural order: `0 → 1 → 2 → 3 → 4 → 5`. Lab 4 (HITL & Governance) lands the §10/§13 pillars hands-on before the Lab 5 capstone. The earlier real-channel Telegram exercise is preserved as an optional bonus in [`lab4-openclaw-optional/`](./lab4-openclaw-optional/).

---

## Why this order matters

```
Lab 0          Lab 1            Labs 2–3            Lab 4             Lab 5
single        coordination      patches for        HITL &            role-specialists
agent     →   crisis        →   the chaos      →   governance    →   shipping real
ships         appears           (allocation,       (graduated        code with a
clean         (the ceiling)     topology)          autonomy)         3-tier eval
```

Lab 0 establishes the *baseline* — what one agent with good roles already gets you. Without that baseline, Lab 1's coordination crisis looks contrived. With it, Lab 1 lands as the *next* problem you'd hit on Monday.

Labs 2 and 3 add the patches: atomic task allocation and topology choice. Lab 4 then puts a human in the loop — §10 (graduated autonomy) and §13 (governance) — the one pillar set you cannot read your way into. Lab 5 is the capstone: *can these patches actually ship code in 60 minutes?* That's the §15 (three-tier evaluation) lesson made flesh — the eval script reads straight from the blackboard.

The optional openclaw bonus revisits §10/§13 on a *real* channel (a Telegram bot) for anyone who wants to feel auth, rate limits, and a human in their actual DMs.

Skip Labs 0 or 1 at your peril — Labs 2, 3, and 5 don't make sense without them.

---

## Prereqs

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed and logged in
- An Anthropic Pro/Max subscription or API key
- macOS / Linux / WSL — `bash`, `git`, `tmux`
- Node.js 18+ (for Lab 2 and Lab 5's `task-cli`)
- Bun v1.0+ (for Lab 0's gstack toolkit)
- A Groq account (free) — *only* if you do the optional openclaw bonus

The only network requirement is outbound HTTPS to `api.anthropic.com` (and Groq + Telegram for the openclaw bonus). Lab 4 (HITL & Governance) is fully local — no channel, no accounts.

---

## Audience

Senior professionals — engineers, tech leads, technical founders. The labs assume you already ship code with single-agent Claude Code / Cursor / similar. The point is to give you *judgment* about when multi-agent helps, when it hurts, and what failure modes to expect — not to teach you what an agent is.

---

## Bundled toolkits and sandboxes

**Lab 0** bundles three things students need but shouldn't have to install separately:

- [`lab0-workflow/gstack/`](./lab0-workflow/gstack/) — Garry Tan's [gstack](https://github.com/garrytan/gstack) (MIT) — single-agent slash-command toolkit
- [`lab0-workflow/docvault-legacy/`](./lab0-workflow/docvault-legacy/) — sandbox: fake legacy Spring/Java app with a graded bug list (`REVIEW.yaml`, `TODO.md`)
- [`lab0-workflow/SDRAuto/`](./lab0-workflow/SDRAuto/) — alt sandbox: a real Node/TS BDR product

**The openclaw bonus** bundles [`lab4-openclaw-optional/openclaw/`](./lab4-openclaw-optional/openclaw/) — a self-hosted agent gateway connecting Claude/Groq agents to chat channels.

**Labs 2 and 5** ship a tiny in-tree `task-cli/` (~60 LOC Node) so atomic claims don't get masked by file-edit races. **Lab 4** ships `hitl-cli/` — the approval-queue + governance engine, same atomic-lock pattern.

---

## After the primer

Students who finish here will have **personally implemented ~7 of 16 pillars** and **felt the absence of another ~6**. That's enough fluency to read framework docs (LangGraph, CrewAI, AutoGen) critically — and to know which problems they actually solve.

The next step is the **blackboard-classroom big exercise** (separate repo, separate session): 5 teams × 7 students, real coding projects, contract-net allocation, stigmergic learning, scaled across a server. Without this primer, students don't survive that exercise. With it, they do.

---

## Status

| Lab | State |
|---|---|
| Lab 0 | ✅ Built (gstack + docvault-legacy + SDRAuto bundled) |
| Lab 1 | ✅ Built and smoke-tested |
| Lab 2 | ✅ Built (CLAUDE.md + `task-cli/` + 2 rounds) |
| Lab 3 | ✅ Built (3 round folders, each with CLAUDE.md) |
| Lab 4 — HITL & Governance | ✅ Built (`hitl-cli` + 3 rounds + graduated-autonomy gate + governance floor; smoke-tested) |
| Lab 5 *(capstone)* | ✅ Built (`lab5-up/down.sh`, `project.template/` starter, local role-specialist agents, `task-cli` + `eval-self.sh`; smoke-tested) |
| Bonus — openclaw *(optional)* | ✅ Built (real-channel Telegram HITL; was the former Lab 4) |

Last updated: 2026-05-09.
