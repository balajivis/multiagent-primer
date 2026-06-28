# The Scenario — SDRAuto Support Ops

You are agents running the **support-ops desk** for *SDRAuto*, a small SaaS. A
queue of inbound customer requests lands in `requests.json`. Your team turns
each request into one concrete **action** against the company's systems
(the mock world in `world-state.json`).

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
