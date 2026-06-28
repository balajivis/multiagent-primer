# Project brief

> {description}

## How this scaffolds the sprint backlog

The eight tasks in `tasks.json` are a generic dev-sprint scaffold (review · investigate · plan · QA · release notes · retro). Frame each one in the context of **this project** when you do the work: the artifact a `/review` produces for *your* project's auth code is different from a generic review, even though the task name is the same.

The two sample files in `sandbox/` are stand-ins for the project's real code. If your project is something completely different (e.g. a content site, a research artifact, a process), treat the sandbox files as illustrative — the *task pattern* is what's being practiced, not the specific code.

## Adding tasks

If your project needs work that the scaffold doesn't cover, agents can extend the backlog:

```
./task-cli/task add "<title>" --needs /skill[,/skill] [--estimate N]
```

New tasks join the same first-claim or contract-net rules as the rest.

---

> **Customising the project:** open the live mirror at `http://localhost:8766/bb-mirror.html` and type a project description into the input at the top. The server rewrites this file and resets `tasks.json` so your agents pick up the new framing on their next read.
