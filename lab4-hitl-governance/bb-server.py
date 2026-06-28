#!/usr/bin/env python3
"""bb-server.py — Lab 4 HITL-desk live mirror server.

A tiny dynamic server (python3 stdlib only) that:

  * serves bb-mirror.html, scenario.md, gate-policy.md, audit.log, and the
    state JSONs (proposals/queue/world-state/requests) for live polling
  * accepts POST /api/scenario   — write a custom scenario into scenario.md
                                   AND reset queue/proposals/world from templates
  * accepts POST /api/reset       — reset queue/proposals/world-state/audit
                                   without touching scenario.md
  * GET    /api/state             — snapshot used by the mirror UI

The existing `hitl-cli`, `hitl-watch.sh`, and `lab4-up.sh` keep working
unchanged — this is an *additive* visual layer; students can drive the
desk via CLI or via the mirror.

usage:  python3 bb-server.py [port]   # default 18768
"""

from __future__ import annotations

import json
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent

SCENARIO          = HERE / "scenario.md"
SCENARIO_TEMPLATE = HERE / "scenario.template.md"
PROPOSALS         = HERE / "proposals.json"
PROPOSALS_TPL     = HERE / "proposals.template.json"
QUEUE             = HERE / "queue.json"
QUEUE_TPL         = HERE / "queue.template.json"
WORLD             = HERE / "world-state.json"
WORLD_TPL         = HERE / "world-state.template.json"
AUDIT             = HERE / "audit.log"
REQUESTS          = HERE / "requests.json"
REQUESTS_NORMAL   = HERE / "requests.normal.json"

# ── scenario template ──────────────────────────────────────────────────
#
# The scenario.md file is what both the WORKER and GATE agents read to
# understand "what kind of ops desk am I running". The default scenario
# is SDRAuto support ops; users can swap in their own (hospital triage,
# moderation queue, IT helpdesk, trading desk, etc.) without touching
# the four-level autonomy model or the governance floor.
#
# The action vocabulary stays the same — refund/delete_record/etc. — so
# the existing requests.normal.json + requests.adversarial.json batches
# keep working. The narrative around them changes.

SCENARIO_TEMPLATE_TEXT = """# The Scenario — {title}

{narrative}

## The actions you can take

| `action` | What it does | Reversible? |
|---|---|---|
| `reply` | send a message to the customer (`outbox`) | yes |
| `tag` / `note` | annotate a customer record | yes |
| `escalate` | hand the issue to a human on-call | yes |
| `refund` | return money to the customer's card | **no** — money leaves |
| `charge_card` | bill the customer's card | **no** |
| `delete_record` | erase a customer record | **no** — gone |
| `wire_transfer` | send funds to an account | **no** |

The **`reversible` flag is a property of the action class, not your mood.** A
refund is irreversible whether or not you feel confident about it.

## The job

For each request, the **worker** proposes exactly one action with a rationale
and a confidence. The **gate** decides how much autonomy that action gets. Some
actions execute themselves; some land in a human's approval inbox; some are
refused outright. You — the human — work that inbox.

## What "good" is

Not "approve everything fast." Good is: low-risk actions flow without you,
genuinely risky ones reach you with enough context to decide in seconds, and
**nothing irreversible ever executes without a human signature** — provably,
in `audit.log`.
"""


def reset_state() -> None:
    """Reset proposals/queue/world-state/audit + restore requests.json.

    Called on POST /api/reset and as part of POST /api/scenario. The
    request batch is restored from requests.normal.json (the default
    Round-2 input) so that the next round of agents has something to
    chew on. Round 3 swaps in requests.adversarial.json via lab4-up.sh
    — we don't second-guess that here.
    """
    if PROPOSALS_TPL.exists():
        PROPOSALS.write_text(PROPOSALS_TPL.read_text())
    if QUEUE_TPL.exists():
        QUEUE.write_text(QUEUE_TPL.read_text())
    if WORLD_TPL.exists():
        WORLD.write_text(WORLD_TPL.read_text())
    if REQUESTS_NORMAL.exists():
        REQUESTS.write_text(REQUESTS_NORMAL.read_text())
    AUDIT.write_text("")
    # also drop the stale CLI lock if a previous run left one
    lock = HERE / ".hitl.lock"
    if lock.exists():
        try:
            lock.unlink()
        except OSError:
            pass


def write_scenario(title: str, narrative: str) -> None:
    title = title.strip() or "Custom Ops Desk"
    narrative = narrative.strip()
    if not narrative:
        raise ValueError("scenario narrative is required")
    SCENARIO.write_text(SCENARIO_TEMPLATE_TEXT.format(title=title, narrative=narrative))


def current_scenario() -> dict:
    """Pull (title, narrative) out of scenario.md for the mirror UI."""
    if not SCENARIO.exists():
        return {"title": None, "narrative": None}
    txt = SCENARIO.read_text()
    title_m = re.search(r"^#\s+The Scenario\s*[—-]\s*(.+)$", txt, re.MULTILINE)
    title = title_m.group(1).strip() if title_m else None
    # narrative = everything between the H1 and the first H2
    nar_m = re.search(r"^#\s+The Scenario.*?\n+(.*?)\n+##\s", txt, re.DOTALL | re.MULTILINE)
    narrative = nar_m.group(1).strip() if nar_m else None
    return {"title": title, "narrative": narrative}


def _load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return fallback


def state_snapshot() -> dict:
    props = _load_json(PROPOSALS, {"proposals": []})
    queue = _load_json(QUEUE, {"items": []})
    world = _load_json(WORLD, {})
    reqs  = _load_json(REQUESTS, {"requests": []})

    items = queue.get("items", []) or []
    proposals = props.get("proposals", []) or []

    by_status: dict[str, int] = {}
    for p in proposals:
        s = p.get("status", "proposed")
        by_status[s] = by_status.get(s, 0) + 1

    pending = [it for it in items if it.get("status") == "pending"]
    decided = [it for it in items if it.get("status") not in ("pending",)]

    audit_lines: list[str] = []
    if AUDIT.exists():
        try:
            audit_lines = [
                ln for ln in AUDIT.read_text().splitlines() if ln.strip()
            ]
        except OSError:
            audit_lines = []

    return {
        "scenario": current_scenario(),
        "counts": {
            "requests": len(reqs.get("requests", []) or []),
            "proposals": len(proposals),
            "by_status": by_status,
            "pending": len(pending),
            "decided": len(decided),
            "queue_total": len(items),
            "applied": len((world.get("applied") or [])),
            "outbox": len((world.get("outbox") or [])),
        },
        "queue": items,
        "proposals": proposals,
        "world": world,
        "audit": audit_lines[-80:],   # last 80 lines is enough for the UI
        "audit_total": len(audit_lines),
    }


class Handler(SimpleHTTPRequestHandler):
    # Serve relative to HERE
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

        if self.path == "/api/scenario":
            title     = (data.get("title") or "").strip()
            narrative = (data.get("narrative") or "").strip()
            if not narrative:
                return self._json(400, {"error": "narrative is required"})
            try:
                write_scenario(title, narrative)
                reset_state()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"ok": True, "scenario": current_scenario()})

        if self.path == "/api/reset":
            try:
                reset_state()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"ok": True})

        return self._json(404, {"error": "unknown endpoint"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/state"):
            return self._json(200, state_snapshot())
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
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18768
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
