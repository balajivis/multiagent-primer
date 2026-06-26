#!/usr/bin/env node
// tiny-crm-cli — entry point (STARTER STUB).
//
// The 3-agent team fills in routing + the commands during the sprint.
// Target behaviour (see ../task.md):
//   tiny-crm add-lead "Alice Smith" alice@example.com
//   tiny-crm list [--status new|qualified|customer]
//   tiny-crm convert <lead-id>
//   tiny-crm report
//   tiny-crm tag <lead-id> <tag>
//
// Storage lives in project/data/leads.json (created on first write).
// Backend owns this file + src/storage.ts + src/commands/*.ts.
// Frontend owns src/format.ts + src/help.ts. Tests own test/*.

const COMMANDS = ["add-lead", "list", "convert", "report", "tag"];

function usage(): void {
  console.log("tiny-crm — lead management CLI\n");
  console.log("usage: tiny-crm <command> [args]\n");
  console.log("commands:");
  for (const c of COMMANDS) console.log("  " + c);
  console.log("\n(starter stub — commands not implemented yet; claim a task in tasks.json)");
}

function main(argv: string[]): number {
  const [cmd, ...args] = argv;
  if (!cmd || cmd === "--help" || cmd === "-h") {
    usage();
    return cmd ? 0 : 1;
  }
  if (!COMMANDS.includes(cmd)) {
    console.error("unknown command: " + cmd);
    usage();
    return 2;
  }
  // TODO(team): route to src/commands/<cmd>.ts once implemented.
  void args;
  console.error("'" + cmd + "' not implemented yet — claim its task and build it.");
  return 3;
}

process.exit(main(process.argv.slice(2)));
