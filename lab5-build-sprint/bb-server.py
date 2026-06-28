#!/usr/bin/env python3
"""bb-server.py — Lab 5 Build-Sprint server.

Replaces `python3 -m http.server` with a tiny dynamic server so the live
mirror at /bb-mirror.html can:

  * accept a custom feature spec via POST /api/spec
  * reset blackboard + tasks + project/ via POST /api/reset
  * read current state via GET /api/state
      → roster, per-role status, task counts, performative mix,
        files shipped under project/, final eval verdict (if present)

Static files (bb-mirror.html, blackboard.md, tasks.json, project.md, etc.)
keep working unchanged — the GET path falls through to SimpleHTTPRequestHandler.

usage:  python3 bb-server.py [port]   # default 8769
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLACKBOARD = HERE / "blackboard.md"
BLACKBOARD_TEMPLATE = HERE / "blackboard.template.md"
TASKS = HERE / "tasks.json"
TASKS_TEMPLATE = HERE / "tasks.template.json"
PROJECT_MD = HERE / "project.md"
PROJECT_MD_TEMPLATE = HERE / "project.template.md"
PROJECT_DIR = HERE / "project"
PROJECT_TEMPLATE_DIR = HERE / "project.template"
EVAL_SCRIPT = HERE / "eval-self.sh"

ROLES = ["frontend", "backend", "tests"]
PERFORMATIVES = ["INFORM", "REQUEST", "COMMIT", "BLOCK", "ESCALATE", "LESSON"]


# ── reset helpers ────────────────────────────────────────────────────────

def reset_blackboard() -> None:
    if BLACKBOARD_TEMPLATE.exists():
        BLACKBOARD.write_text(BLACKBOARD_TEMPLATE.read_text())
    else:
        BLACKBOARD.write_text("# Blackboard\n\n## Roster\n\n---\n\n## Performative log\n\n---\n")


def reset_tasks() -> None:
    if not TASKS_TEMPLATE.exists():
        raise FileNotFoundError("tasks.template.json missing")
    TASKS.write_text(TASKS_TEMPLATE.read_text())


def reset_project_dir() -> None:
    if PROJECT_TEMPLATE_DIR.exists():
        if PROJECT_DIR.exists():
            shutil.rmtree(PROJECT_DIR)
        shutil.copytree(PROJECT_TEMPLATE_DIR, PROJECT_DIR)


def write_spec(description: str) -> None:
    description = description.strip()
    if not description:
        raise ValueError("empty description")
    if PROJECT_MD_TEMPLATE.exists():
        body = PROJECT_MD_TEMPLATE.read_text().replace("{description}", description)
    else:
        body = f"# Build Sprint — feature brief\n\n> {description}\n"
    PROJECT_MD.write_text(body)


def current_spec() -> str | None:
    if not PROJECT_MD.exists():
        return None
    txt = PROJECT_MD.read_text()
    m = re.search(r"^>\s*(.+)$", txt, re.MULTILINE)
    return m.group(1).strip() if m else None


# ── state derivation ─────────────────────────────────────────────────────

def parse_blackboard() -> dict:
    """Pull roster, performative tallies, recent entries, lessons."""
    if not BLACKBOARD.exists():
        return {"roster": [], "events": [], "perfMix": {}, "lessons": []}

    md = BLACKBOARD.read_text()

    # roster: "- agent-N · <role> · joined <ts>"
    roster = []
    seen = set()
    for m in re.finditer(r"^- (agent-\d+)(?:\s*·\s*([a-zA-Z][a-zA-Z0-9_-]*))?\s*·\s*joined\s+(\S+)", md, re.MULTILINE):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        roster.append({"name": name, "role": (m.group(2) or "").lower(), "joined": m.group(3)})

    # performative entries: "### [agent-N · TS · PERFORMATIVE] headline"
    events = []
    perf_mix: dict[str, int] = {p.lower(): 0 for p in PERFORMATIVES}
    entry_re = re.compile(
        r"^### \[(agent-\d+)\s*·\s*([0-9T:Z\-]+)\s*·\s*([A-Z]+)\]\s*(.+)$",
        re.MULTILINE,
    )
    for m in entry_re.finditer(md):
        perf = m.group(3).upper()
        events.append({
            "agent": m.group(1),
            "ts": m.group(2),
            "perf": perf,
            "headline": m.group(4).strip(),
        })
        if perf.lower() in perf_mix:
            perf_mix[perf.lower()] += 1

    # lessons specifically — body of LESSON entries
    lessons = []
    lines = md.split("\n")
    i = 0
    while i < len(lines):
        em = re.match(r"^### \[(agent-\d+)\s*·\s*([0-9T:Z\-]+)\s*·\s*LESSON\]\s*(.+)$", lines[i])
        if em:
            body = None
            for j in range(i + 1, min(i + 8, len(lines))):
                bm = re.match(r"^\*\*Lesson:\*\*\s*(.+)$", lines[j])
                if bm:
                    body = bm.group(1).strip()
                    break
            lessons.append({
                "agent": em.group(1),
                "ts": em.group(2),
                "headline": em.group(3).strip(),
                "lesson": body or "",
            })
        i += 1

    return {
        "roster": roster,
        "events": events,
        "perfMix": perf_mix,
        "lessons": lessons,
    }


def parse_tasks() -> dict:
    if not TASKS.exists():
        return {"total": 0, "counts": {}, "tasks": []}
    try:
        data = json.loads(TASKS.read_text())
    except json.JSONDecodeError:
        return {"total": 0, "counts": {}, "tasks": []}
    tasks = data.get("tasks", [])
    counts = {"open": 0, "claimed": 0, "done": 0, "failed": 0}
    role_status: dict[str, dict[str, int]] = {r: {"open": 0, "claimed": 0, "done": 0, "failed": 0} for r in ROLES}
    role_status["other"] = {"open": 0, "claimed": 0, "done": 0, "failed": 0}

    summary = []
    for t in tasks:
        status = t.get("status", "open")
        counts[status] = counts.get(status, 0) + 1
        # bucket by primary tag → role
        tags = [str(x).lower() for x in (t.get("requires") or [])]
        role = "other"
        if any(x in tags for x in ("frontend", "docs")):
            role = "frontend"
        elif any(x in tags for x in ("backend", "db", "devops")):
            role = "backend"
        elif "tests" in tags:
            role = "tests"
        role_status[role][status] = role_status[role].get(status, 0) + 1

        summary.append({
            "id": t.get("id"),
            "title": t.get("title"),
            "requires": tags,
            "role": role,
            "status": status,
            "claimed_by": t.get("claimed_by"),
            "result": (t.get("result") or "").strip() or None,
            "output": t.get("output"),
            "has_lesson": bool(t.get("lessons")),
        })

    return {
        "total": len(tasks),
        "counts": counts,
        "roleStatus": role_status,
        "tasks": summary,
        "brief": data.get("brief"),
    }


def project_files() -> list[dict]:
    """List files under project/ with size + age, capped at 80 entries."""
    if not PROJECT_DIR.exists():
        return []
    out = []
    for root, dirs, files in os.walk(PROJECT_DIR):
        # skip noisy dirs
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "dist", "build", ".next")]
        for fn in files:
            p = Path(root) / fn
            try:
                st = p.stat()
            except OSError:
                continue
            rel = p.relative_to(PROJECT_DIR).as_posix()
            out.append({
                "path": rel,
                "bytes": st.st_size,
                "mtime": int(st.st_mtime),
            })
            if len(out) >= 80:
                return out
    return out


def eval_verdict() -> dict | None:
    """If `./eval-self.sh` runs cleanly, capture the L2 + verdict lines.

    We don't gate the mirror on this — it only renders once the eval has
    been triggered (we cache it as runs/<run>-eval.txt if produced
    out-of-band, but the simplest path is: run it on-demand when at least
    one task is done, with NO_COLOR=1 so the output is stripped."""
    if not EVAL_SCRIPT.exists() or not TASKS.exists() or not BLACKBOARD.exists():
        return None
    try:
        tdata = json.loads(TASKS.read_text())
    except json.JSONDecodeError:
        return None
    # only invoke eval once anything has moved
    has_movement = any(t.get("status") in ("done", "failed", "claimed") for t in tdata.get("tasks", []))
    if not has_movement:
        return None
    try:
        proc = subprocess.run(
            ["bash", str(EVAL_SCRIPT)],
            cwd=str(HERE),
            env={**os.environ, "NO_COLOR": "1"},
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    out = proc.stdout
    if not out:
        return None
    # Parse a few lines of interest: completion rate, verdict bullets
    completion = None
    m = re.search(r"completion rate:\s*([0-9]+|—)%?", out)
    if m:
        completion = m.group(1)
    verdict_lines = []
    in_verdict = False
    for line in out.splitlines():
        if line.strip().startswith("=== Verdict"):
            in_verdict = True
            continue
        if in_verdict:
            if line.strip().startswith("==="):
                break
            stripped = line.strip()
            if stripped and not stripped.startswith("eval-self.sh"):
                verdict_lines.append(stripped)
    return {
        "completion": completion,
        "verdict": verdict_lines,
        "raw": out,
    }


# ── HTTP ─────────────────────────────────────────────────────────────────

class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path in ("/", ""):
            path = "/bb-mirror.html"
        rel = path.lstrip("/")
        full = (HERE / rel).resolve()
        if HERE not in full.parents and full != HERE:
            return str(HERE / "bb-mirror.html")
        return str(full)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    # ── API ──────────────────────────────────────────────────────────
    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            data = json.loads(body) if body else {}
        except Exception as exc:  # noqa: BLE001
            return self._json(400, {"error": f"bad request: {exc}"})

        if self.path == "/api/spec":
            spec = (data.get("spec") or "").strip()
            if not spec:
                return self._json(400, {"error": "spec is required"})
            try:
                write_spec(spec)
                reset_blackboard()
                reset_tasks()
                reset_project_dir()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"ok": True, "spec": spec, "roles": ROLES})

        if self.path == "/api/reset":
            try:
                reset_blackboard()
                reset_tasks()
                reset_project_dir()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"ok": True})

        return self._json(404, {"error": "unknown endpoint"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/state"):
            bb = parse_blackboard()
            tk = parse_tasks()
            files = project_files()
            verdict = eval_verdict()
            return self._json(200, {
                "spec": current_spec(),
                "roles": ROLES,
                "performatives": [p.lower() for p in PERFORMATIVES],
                "roster": bb["roster"],
                "events": bb["events"][-40:],
                "eventTotal": len(bb["events"]),
                "perfMix": bb["perfMix"],
                "lessons": bb["lessons"],
                "tasks": tk,
                "files": files,
                "verdict": verdict,
            })
        return super().do_GET()

    # ── helpers ──────────────────────────────────────────────────────
    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        sys.stderr.write(f"  · {fmt % args}\n")


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8769
    os.chdir(HERE)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"▶ serving {HERE} on port {port}")
    print(f"▶ live mirror: http://localhost:{port}/bb-mirror.html")
    print("▶ press Ctrl-C to stop")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n▶ stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
