# Build Sprint — feature brief

> {description}

## How this brief frames the sprint

The 12 starter tasks in `tasks.json` are a generic CLI scaffold (dispatcher · storage · commands · formatter · help · tests · smoke · README · package.json). They were originally written for **`tiny-crm-cli`** (a JSON-backed lead manager — see `task.md`), but they map cleanly to any small command-line tool with a few subcommands and a JSON store.

When you do the work, frame each task in the context of the feature described above. For example:

- if the user asked for a **"link shortener CLI"**, T-01 is still "CLI dispatcher" but the subcommands are `shorten`, `expand`, `list`, `stats`
- if the user asked for a **"pomodoro tracker"**, T-03 ("add-lead command") becomes "start-session command" and storage is `data/sessions.json`
- the task pattern is what's being practiced — not the specific domain

If the feature genuinely needs work the 12-task scaffold doesn't cover, agents can extend the backlog:

```
./task-cli/task add "<title>" --requires <tag,tag> [--estimate N]
```

New tasks join the same role-claim rules as the rest.

## What the live mirror watches

- **roster** — which roles have joined (`agent-N · <role>`)
- **task table** — open / claimed / done / failed across all 12+ tasks
- **performative mix** — INFORM · REQUEST · COMMIT · BLOCK · ESCALATE · LESSON
- **lessons** — stigmergic traces from failed claims
- **final delivery** — files shipped under `project/` + the L1/L2/L3 verdict once you run `./eval-self.sh`

---

> **Customising the brief:** open the live mirror at `http://localhost:8769/bb-mirror.html` and type a feature description into the input at the top. The server rewrites this file and resets `tasks.json` + `project/` from templates so your agents pick up the new framing on their next read. The hardcoded `tiny-crm-cli` default still works if you skip the input.
