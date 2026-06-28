#!/usr/bin/env python3
"""bb-server.py — Lab 2 Task-Allocation server.

Replaces `python3 -m http.server` with a tiny dynamic server so the live
mirror at /bb-mirror.html can:

  * accept a custom project description via POST /api/project
  * reset tasks.json via POST /api/reset
  * read current state via GET /api/state

Static files (bb-mirror.html, tasks.json, project.md, etc.) keep working
unchanged — the GET path falls through to SimpleHTTPRequestHandler.

usage:  python3 bb-server.py [port]   # default 8766
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = HERE / "tasks.json"
TASKS_TEMPLATE = HERE / "tasks.template.json"
PROJECT = HERE / "project.md"
PROJECT_TEMPLATE = HERE / "project.template.md"
TASK_VERSION = HERE / "task.version"  # monotonic int; agents poll this to detect topic changes


def bump_version() -> int:
    """Increment task.version; agents poll this each loop and hard-reset on change."""
    try:
        cur = int(TASK_VERSION.read_text().strip()) if TASK_VERSION.exists() else 0
    except Exception:
        cur = 0
    nxt = cur + 1
    TASK_VERSION.write_text(str(nxt))
    return nxt


def current_version() -> int:
    try:
        return int(TASK_VERSION.read_text().strip()) if TASK_VERSION.exists() else 0
    except Exception:
        return 0
OUTPUTS_DIR = HERE / "outputs"


def reset_tasks(project_desc: str | None = None) -> None:
    """Restore tasks.json from tasks.template.json. If project_desc is
    provided, update the 'brief' field to mention the project."""
    if not TASKS_TEMPLATE.exists():
        raise FileNotFoundError("tasks.template.json missing")
    data = json.loads(TASKS_TEMPLATE.read_text())
    if project_desc:
        short = project_desc.strip()
        if len(short) > 200:
            short = short[:200].rsplit(" ", 1)[0] + "…"
        data["brief"] = (
            f"Sprint backlog for: {short} — 8-task scaffold "
            f"(review · investigate · plan · QA · release · retro). "
            f"Round 1 = first-claim; Round 2 = contract-net."
        )
    TASKS.write_text(json.dumps(data, indent=2) + "\n")
    # Clear outputs too — fresh project, fresh artifacts.
    if OUTPUTS_DIR.exists():
        for p in OUTPUTS_DIR.iterdir():
            if p.is_file():
                try:
                    p.unlink()
                except OSError:
                    pass


def write_project(description: str) -> None:
    description = description.strip()
    if not description:
        raise ValueError("empty description")
    if PROJECT_TEMPLATE.exists():
        body = PROJECT_TEMPLATE.read_text().replace("{description}", description)
    else:
        body = f"# Project brief\n\n> {description}\n"
    PROJECT.write_text(body)


def current_project() -> str | None:
    if not PROJECT.exists():
        return None
    txt = PROJECT.read_text()
    m = re.search(r"^>\s*(.+)$", txt, re.MULTILINE)
    return m.group(1).strip() if m else None


def tasks_state() -> dict:
    """Return parsed tasks.json or a safe empty shape."""
    if not TASKS.exists():
        return {"version": 0, "brief": "", "tasks": []}
    try:
        return json.loads(TASKS.read_text())
    except json.JSONDecodeError:
        return {"version": 0, "brief": "", "tasks": []}


class Handler(SimpleHTTPRequestHandler):
    # Serve relative to HERE, not the launch CWD
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
    def do_POST(self) -> None:  # noqa: N802 (stdlib API)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            data = json.loads(body) if body else {}
        except Exception as exc:  # noqa: BLE001
            return self._json(400, {"error": f"bad request: {exc}"})

        if self.path == "/api/project":
            description = (data.get("description") or "").strip()
            if not description:
                return self._json(400, {"error": "description is required"})
            try:
                write_project(description)
                reset_tasks(description)
                bump_version()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"ok": True, "description": description, "version": current_version()})

        if self.path == "/api/reset":
            try:
                reset_tasks(current_project())
                bump_version()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"ok": True, "version": current_version()})

        return self._json(404, {"error": "unknown endpoint"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/state"):
            t = tasks_state()
            counts = {"open": 0, "claimed": 0, "done": 0}
            for task in t.get("tasks", []):
                s = task.get("status")
                if s in counts:
                    counts[s] += 1
            done_tasks = [
                {
                    "id": task.get("id"),
                    "title": task.get("title"),
                    "needs": task.get("needs") or [],
                    "claimed_by": task.get("claimed_by"),
                    "completed_at": task.get("completed_at"),
                    "result": task.get("result"),
                    "output": task.get("output"),
                }
                for task in t.get("tasks", [])
                if task.get("status") == "done"
            ]
            return self._json(200, {
                "project": current_project(),
                "brief": t.get("brief"),
                "total": len(t.get("tasks", [])),
                "counts": counts,
                "done_tasks": done_tasks,
                "all_done": counts["done"] == len(t.get("tasks", [])) and len(t.get("tasks", [])) > 0,
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
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
