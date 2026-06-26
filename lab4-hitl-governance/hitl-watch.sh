#!/usr/bin/env bash
# hitl-watch.sh — compact terminal mirror for the HITL desk.
# Shows the approval queue, the autonomy routing, the mock world, and the tail
# of the audit log. Refreshes once per second.

set -u
INTERVAL="${REFRESH:-1}"
cd "$(dirname "$0")"

trap 'tput cnorm; printf "\033[?1049l"; exit 0' INT TERM
tput civis 2>/dev/null || true
printf '\033[?1049h'; clear

while true; do
  frame=$(node -e '
    const fs = require("fs");
    const C = { r:"\x1b[0m", d:"\x1b[2m", b:"\x1b[1m",
      pending:"\x1b[33m", approved:"\x1b[32m", rejected:"\x1b[31m", edited:"\x1b[35m",
      escalated:"\x1b[36m", expired:"\x1b[2m", logged:"\x1b[2m",
      auto:"\x1b[32m", review:"\x1b[36m", approve:"\x1b[33m", blocked:"\x1b[31m",
      applied:"\x1b[32m", "applied-review":"\x1b[36m", queued:"\x1b[33m", proposed:"\x1b[2m" };
    const j = (f, fb) => { try { return JSON.parse(fs.readFileSync(f,"utf8")); } catch { return fb; } };
    const props = j("proposals.json", {proposals:[]});
    const q = j("queue.json", {items:[]});
    const w = j("world-state.json", {});
    const out = [];
    out.push(`${C.b}LAB 4 · HITL DESK${C.r}  ${C.d}${new Date().toISOString().slice(11,19)}Z${C.r}`);
    out.push("─".repeat(60));

    const ps = {}; for (const p of props.proposals) ps[p.status]=(ps[p.status]||0)+1;
    out.push(`  ${C.b}proposals${C.r}  ` + (Object.entries(ps).map(([k,v])=>`${C[k]||""}${v} ${k}${C.r}`).join(" · ")||C.d+"none"+C.r));

    const pend = q.items.filter(i=>i.status==="pending");
    out.push(`  ${C.b}inbox${C.r}      ${C.pending}${pend.length} pending${C.r} · ${q.items.length} total`);
    for (const it of q.items.slice(-8)) {
      const flag = it.governance_override ? `${C.approve} ⚠floor${C.r}` : "";
      out.push(`    ${C.d}${it.id}${C.r} ${(C[it.status]||"")}${it.status.padEnd(9)}${C.r} ${(it.summary||"").slice(0,34)}${flag}`);
    }

    out.push("");
    out.push(`  ${C.b}world${C.r}  ${Object.keys(w.records||{}).length} records · ${(w.outbox||[]).length} sent · ${(w.applied||[]).length} applied`);
    const bal = Object.entries(w.balances||{}).filter(([,v])=>v!==0);
    if (bal.length) out.push("  " + C.rejected + "  money moved: " + bal.map(([k,v])=>`${k} ${v}`).join(" · ") + C.r);

    out.push("");
    out.push(`  ${C.b}audit (tail)${C.r}`);
    let log = ""; try { log = fs.readFileSync("audit.log","utf8").trimEnd(); } catch {}
    const lines = log ? log.split("\n").slice(-7) : [];
    for (const l of lines) {
      const hot = /FLOOR-OVERRIDE|BLOCK|APPLY .*(refund|delete_record|wire_transfer|charge_card)/.test(l);
      out.push("    " + (hot?C.approve:C.d) + l.slice(0,72) + C.r);
    }
    if (!lines.length) out.push("    " + C.d + "(empty)" + C.r);
    console.log(out.join("\n"));
  ' 2>/dev/null)
  printf '\033[H%s\033[J' "$frame"
  sleep "$INTERVAL"
done
