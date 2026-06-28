#!/usr/bin/env python3
"""bb-server.py — Lab 1 Deep-Research server.

Replaces `python3 -m http.server` with a tiny dynamic server so the live
mirror at /bb-mirror.html can:

  * accept a custom research question via POST /api/topic
  * reset the blackboard via POST /api/reset
  * read current state via GET /api/state

Static files (bb-mirror.html, blackboard.md, task.md, etc.) keep working
unchanged — the GET path falls through to SimpleHTTPRequestHandler.

usage:  python3 bb-server.py [port]   # default 8765
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLACKBOARD = HERE / "blackboard.md"
BLACKBOARD_TEMPLATE = HERE / "blackboard.template.md"
TASK = HERE / "task.md"

# Generic four-section research template. Section names match the
# partitions in bb-mirror.html and the SECTIONS constant in its JS.
SECTIONS = ["Background", "Findings", "Caveats", "Implications"]

TASK_TEMPLATE = """# The Brief

Produce a **~400-word brief** on the following research question:

> {topic}

## Required sections (each must have at least 2 findings on the blackboard before you synthesise)

1. **Background** — What is the context? Who/what are the key entities, dates, prior work, and definitions a reader needs before the findings make sense?
2. **Findings** — The two or three most important concrete facts answering the question. Each one cited and as specific as possible.
3. **Caveats** — What's contested, uncertain, out-of-date, or known to be wrong about the popular answer? Be specific — "it's complicated" is not specific.
4. **Implications** — What does this mean for someone acting on this in 2026? Be skeptical: which conclusions follow from the evidence and which are still speculation?

## Acceptance criteria

- Each section has at least two findings on the board, each with a source
- Final synthesis is ~400 words total
- Inline attribution to which agent contributed which finding
- No section is empty or padded

## Time budget

15 minutes. Do not optimise for completeness — optimise for *not duplicating each other's work*. A brief with 3 strong, distinct findings per section is better than 6 overlapping ones.
"""


def reset_blackboard() -> None:
    """Restore blackboard.md from blackboard.template.md."""
    if BLACKBOARD_TEMPLATE.exists():
        BLACKBOARD.write_text(BLACKBOARD_TEMPLATE.read_text())
    else:
        BLACKBOARD.write_text("# Blackboard\n\n## Roster\n\n---\n\n## Findings\n\n---\n")


def write_task(topic: str) -> None:
    topic = topic.strip()
    if not topic:
        raise ValueError("empty topic")
    TASK.write_text(TASK_TEMPLATE.format(topic=topic))


def current_topic() -> str | None:
    if not TASK.exists():
        return None
    txt = TASK.read_text()
    m = re.search(r"^>\s*(.+)$", txt, re.MULTILINE)
    return m.group(1).strip() if m else None


def synthesis_block() -> str | None:
    """Return the markdown of the ## SYNTHESIS section in blackboard.md, or None."""
    if not BLACKBOARD.exists():
        return None
    md = BLACKBOARD.read_text()
    m = re.search(r"^## SYNTHESIS[^\n]*\n([\s\S]*?)(?:\n---\s*\n|\Z)", md, re.MULTILINE)
    return m.group(0).strip() if m else None


class Handler(SimpleHTTPRequestHandler):
    # Serve relative to HERE, not the launch CWD
    def translate_path(self, path: str) -> str:
        # Strip query / hash, route under HERE
        path = path.split("?", 1)[0].split("#", 1)[0]
        if path in ("/", ""):
            path = "/bb-mirror.html"
        rel = path.lstrip("/")
        full = (HERE / rel).resolve()
        # Block path traversal outside HERE
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

        if self.path == "/api/topic":
            topic = (data.get("topic") or "").strip()
            if not topic:
                return self._json(400, {"error": "topic is required"})
            try:
                write_task(topic)
                reset_blackboard()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"ok": True, "topic": topic, "sections": SECTIONS})

        if self.path == "/api/reset":
            try:
                reset_blackboard()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"ok": True})

        return self._json(404, {"error": "unknown endpoint"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/state"):
            return self._json(200, {
                "topic": current_topic(),
                "sections": SECTIONS,
                "synthesis": synthesis_block(),
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
        # Quieter logs — one line per request, no client IP noise
        sys.stderr.write(f"  · {fmt % args}\n")


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    os.chdir(HERE)  # so any leftover relative paths still resolve
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
