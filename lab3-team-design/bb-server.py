#!/usr/bin/env python3
"""bb-server.py — Lab 3 Team-Design server.

Replaces `python3 -m http.server` with a tiny dynamic server so the live
mirror at /bb-mirror.html can:

  * accept a custom problem via POST /api/problem (rewrites task.md +
    resets the active board and clears any prior per-round snapshots)
  * reset just the active blackboard via POST /api/reset
  * read current state via GET /api/state — returns problem, the active
    round (from `.current-round` left by lab3-up.sh), per-round status,
    and a side-by-side comparison once two or more rounds have output.

Static files (bb-mirror.html, blackboard.md, task.md, runs/*) keep
working unchanged — the GET path falls through to SimpleHTTPRequestHandler.

usage:  python3 bb-server.py [round] [port]
        # round is informational only (kept for arg-compat with the
        # old `bb-serve.sh ROUND PORT` shape); default port: 8767
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
RUNS = HERE / "runs"
CURRENT_ROUND_FILE = HERE / ".current-round"

# Sections every round must cover. Names match the partitions in
# bb-mirror.html and the SECTIONS constant in its JS.
SECTIONS = ["Transport", "Lodging", "Activities", "Budget"]

ROUND_NAMES = {
    1: "Supervisor",
    2: "Pipeline",
    3: "Swarm",
}

TASK_TEMPLATE = """# The Brief

The team produces a single coherent output on the blackboard for the
following problem. **Same brief across all three rounds; only the team
topology changes.**

> {problem}

## Required sections (each with at least one substantive entry)

1. **Transport** — how people / things move; logistics; sequencing
2. **Lodging** — where they stay / live / land · cost · rationale
3. **Activities** — the day-by-day or step-by-step plan
4. **Budget** — running totals · final figure · margin vs the cap (if any)

(These four section names are kept generic so every round shares the
same partitions. Re-interpret each section for your specific problem —
e.g. for a launch plan, "Transport" = comms channels, "Lodging" =
where users land, "Activities" = the launch-day plan, "Budget" =
spend / effort.)

## Acceptance

- All four sections have entries
- A clear "this is the chosen plan" output (not 5 alternatives — pick one)
- Each entry cites a source or explicit assumption (no hand-waving)

## Time budget

10 min per round. The brief is identical across topologies. The lesson
is in *how* the three teams reach (or fail to reach) an answer.
"""


def reset_blackboard() -> None:
    """Restore blackboard.md from blackboard.template.md."""
    if BLACKBOARD_TEMPLATE.exists():
        BLACKBOARD.write_text(BLACKBOARD_TEMPLATE.read_text())
    else:
        BLACKBOARD.write_text(
            "# Blackboard\n\n## Roster\n\n---\n\n## Directives\n\n---\n\n## Entries\n\n---\n"
        )


def clear_round_snapshots() -> None:
    """Remove runs/round-{1,2,3}.md so old comparisons don't leak across problems."""
    if not RUNS.exists():
        return
    for n in (1, 2, 3):
        p = RUNS / f"round-{n}.md"
        if p.exists():
            try:
                p.unlink()
            except OSError:
                pass


def write_task(problem: str) -> None:
    problem = problem.strip()
    if not problem:
        raise ValueError("empty problem")
    TASK.write_text(TASK_TEMPLATE.format(problem=problem))


def current_problem() -> str | None:
    if not TASK.exists():
        return None
    txt = TASK.read_text()
    m = re.search(r"^>\s*(.+)$", txt, re.MULTILINE)
    return m.group(1).strip() if m else None


def current_round() -> int | None:
    if not CURRENT_ROUND_FILE.exists():
        return None
    try:
        n = int(CURRENT_ROUND_FILE.read_text().strip())
        return n if n in (1, 2, 3) else None
    except (ValueError, OSError):
        return None


def itinerary_block(md: str) -> str | None:
    """Return the markdown of the ## ITINERARY section, or None."""
    m = re.search(
        r"^## ITINERARY[^\n]*\n([\s\S]*?)(?:\n---\s*\n|\Z)", md, re.MULTILINE
    )
    return m.group(0).strip() if m else None


def parse_board(md: str) -> dict:
    """Lightweight parse of a blackboard for per-round stats."""
    roster = []
    seen = set()
    for m in re.finditer(
        r"^- (agent-\d+) · joined ([0-9T:Z\-]+)(?:\s*·\s*(.+?))?\s*$",
        md,
        re.MULTILINE,
    ):
        name = m.group(1)
        if name in seen:
            continue
        seen.add(name)
        roster.append(
            {"name": name, "joined": m.group(2), "role": (m.group(3) or "").strip()}
        )

    entries = []
    by_section = {s: 0 for s in SECTIONS}
    by_agent: dict[str, int] = {}
    lines = md.split("\n")
    for i, line in enumerate(lines):
        hm = re.match(r"^### \[(agent-\d+) · ([^\]]+?)(?: · (?:DONE|done))?\] (.+)$", line)
        if not hm:
            continue
        agent, ts, headline = hm.group(1), hm.group(2), hm.group(3)
        section = None
        for j in range(i + 1, min(i + 6, len(lines))):
            sm = re.match(r"^\*\*Section:\*\*\s*(.+?)\s*$", lines[j])
            if sm:
                raw = sm.group(1)
                section = next(
                    (s for s in SECTIONS if raw.lower().startswith(s.lower())),
                    raw.split()[0] if raw else None,
                )
                break
        entries.append({"agent": agent, "section": section, "headline": headline, "ts": ts})
        if section in by_section:
            by_section[section] += 1
        by_agent[agent] = by_agent.get(agent, 0) + 1

    directives = len(re.findall(r"DIRECTIVE\]", md))
    dones = len(re.findall(r"· (?:DONE|done)\]", md))
    itinerary = itinerary_block(md)

    return {
        "roster": roster,
        "entries": entries,
        "entry_count": len(entries),
        "by_section": by_section,
        "by_agent": by_agent,
        "directives": directives,
        "dones": dones,
        "has_itinerary": itinerary is not None,
        "itinerary": itinerary,
    }


def round_files() -> dict[int, Path]:
    """Map round number → archived board path (runs/round-N.md), if present."""
    out: dict[int, Path] = {}
    if not RUNS.exists():
        return out
    for n in (1, 2, 3):
        p = RUNS / f"round-{n}.md"
        if p.exists():
            out[n] = p
    return out


def round_summaries() -> list[dict]:
    """Build per-round summaries for the comparison panel."""
    summaries = []
    active = current_round()
    archives = round_files()
    for n in (1, 2, 3):
        item: dict = {
            "round": n,
            "name": ROUND_NAMES[n],
            "active": (n == active),
            "has_output": False,
        }
        source: Path | None = None
        # If this round is currently active, use the live blackboard
        if n == active and BLACKBOARD.exists():
            source = BLACKBOARD
            item["source"] = "live"
        elif n in archives:
            source = archives[n]
            item["source"] = "archive"
        if source is not None:
            md = source.read_text()
            parsed = parse_board(md)
            item["has_output"] = parsed["entry_count"] > 0
            item["stats"] = {
                "entries": parsed["entry_count"],
                "agents": len(parsed["roster"]),
                "directives": parsed["directives"],
                "dones": parsed["dones"],
                "has_itinerary": parsed["has_itinerary"],
                "by_section": parsed["by_section"],
                "roles": sorted({r["role"] for r in parsed["roster"] if r["role"]}),
            }
            item["itinerary"] = parsed["itinerary"]
        summaries.append(item)
    return summaries


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
    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8") if length else ""
            data = json.loads(body) if body else {}
        except Exception as exc:  # noqa: BLE001
            return self._json(400, {"error": f"bad request: {exc}"})

        if self.path == "/api/problem":
            problem = (data.get("problem") or "").strip()
            if not problem:
                return self._json(400, {"error": "problem is required"})
            try:
                write_task(problem)
                reset_blackboard()
                clear_round_snapshots()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(
                200, {"ok": True, "problem": problem, "sections": SECTIONS}
            )

        if self.path == "/api/reset":
            try:
                reset_blackboard()
            except Exception as exc:  # noqa: BLE001
                return self._json(500, {"error": str(exc)})
            return self._json(200, {"ok": True})

        return self._json(404, {"error": "unknown endpoint"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/state"):
            return self._json(
                200,
                {
                    "problem": current_problem(),
                    "sections": SECTIONS,
                    "active_round": current_round(),
                    "round_names": ROUND_NAMES,
                    "rounds": round_summaries(),
                },
            )
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
    # Support both `bb-server.py PORT` and `bb-server.py ROUND PORT` (the
    # latter is what the legacy bb-serve.sh wrapper passes). The round
    # arg is informational; the active round is read from .current-round.
    argv = sys.argv[1:]
    port = 8767
    if len(argv) == 1:
        try:
            port = int(argv[0])
        except ValueError:
            pass  # treat as round, ignore
    elif len(argv) >= 2:
        try:
            port = int(argv[1])
        except ValueError:
            try:
                port = int(argv[0])
            except ValueError:
                pass
    os.chdir(HERE)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"▶ serving {HERE} on port {port}")
    print(f"▶ live mirror: http://localhost:{port}/bb-mirror.html")
    active = current_round()
    if active:
        print(f"▶ active round: {active} · {ROUND_NAMES[active]}")
    print("▶ press Ctrl-C to stop")
    print()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n▶ stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
