# Reflo: Payment Recovery

Build a fintech dashboard called "Reflo" — an AI agent that recovers failed

subscription payments for merchants, with every action bounded, gated, and

logged to an audit trail.

DESIGN DIRECTION

Clean, precise SaaS fintech aesthetic — closer to Stripe Dashboard or Linear

than a flashy consumer app. This tool exists to be trusted, so the visual

language should feel transparent and data-forward, not decorative.

- One clean sans-serif for both UI chrome and numbers — legibility over style

- Flat surfaces only: no gradients, no neon, no drop shadows, no glassmorphism

- Generous whitespace, clear grouping, calm information density

- Color is functional, never decorative. Fixed meaning across every screen:

  - teal = resolved / recovered

  - coral = stopped / blocked by a guardrail

  - amber = pending / escalated to a human

  - gray = neutral / structural

- Status always shown as a small colored badge/pill, consistent everywhere

DATA MODEL (use structured mock data, but isolate it behind a small

data-fetching layer/hook so real API calls can replace it later)

- RecoveryCase: id, customer_name, amount, root_cause (insufficient_funds |

  expired_instrument | mandate_revoked | bank_timeout | issuer_decline |

  unknown), proposed_action, status (DETECTED | CLASSIFIED | DECIDED | GATED

  | EXECUTING | RESOLVED | STOPPED | ESCALATED), created_at

- AuditLogEntry: case_id, stage, input_snapshot, output, rule_fired, timestamp

- BatchRun: batch_size, recovered_amount, recovery_rate, baseline_rate,

  blocked_count

SCREENS

1. Recovery Queue (main/landing screen)

   Table of RecoveryCases: customer, amount, root cause, proposed action,

   status badge, created time. Filterable by status and root cause, sortable

   by amount and time. Clicking a row opens Case Detail.

2. Case Detail (the most important screen — build this with the most care)

   A vertical timeline matching the state machine: Detected → Classified →

   Decided → Gated → Executing → terminal (Resolved / Stopped / Escalated).

   Each step shows what happened and, critically, WHICH RULE OR MODEL OUTPUT

   caused it — this is an audit trail, not just a status tracker. At the top,

   one plain-language sentence explaining why the system did what it did.

3. Batch Metrics

   One hero number: total ₹ recovered. A comparison bar/chart: this agent's

   recovery rate vs. a "naive retry immediately" baseline on the same batch.

   A breakdown of cases by root cause. A guardrail-block count with the

   reasons those actions were blocked.

4. Guardrail Rules (read-only policy view)

   A table of the active rules: name, plain-language condition, forced

   action if it fires. Presented like a governance/policy page — this screen

   exists to prove the agent's boundaries are explicit, not hidden in a

   prompt.

NAVIGATION

Simple persistent sidebar or top nav across all 4 screens. Keep it minimal —

this is an internal ops tool, not a marketing site.

NON-NEGOTIABLES

- No decorative dark/colored page backgrounds — light, neutral base

- Every status badge uses the fixed color meaning above, nowhere else

- Case Detail must visually read as a trustworthy audit trail first, a

  pretty timeline second

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/ef5a1c82-a108-42a7-9b88-0b0acce50ff6).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
