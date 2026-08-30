# Reflo
### Reflowing revenue that almost got stuck.
### Software Requirements Specification & System Design Document — v1
**Track:** AI Revenue Recovery | **Status:** Baseline for hackathon submission | **Owner:** [you]

---

## 0. Document Scope

This document covers one bounded loop: **failed subscription/mandate payments → root-cause detection → gated recovery action → measured outcome.** It intentionally excludes checkout-abandonment and B2B receivables (v2 backlog) to keep v1 provably correct rather than broadly shallow.

---

## 1. PLAN — Product Framing

### 1.1 Problem statement
Merchants on recurring billing lose revenue silently: a payment fails, nothing intelligent retries it, and the customer churns without anyone diagnosing *why* it failed. Generic "retry immediately" logic wastes attempts on unrecoverable failures (revoked mandate) and under-serves recoverable ones (insufficient funds needs a *timed* retry, not an instant one).

### 1.2 Vision statement
*A bounded agent that looks at every failed payment, decides the one correct next action within explicit limits, executes it, and proves — with numbers, not vibes — that it recovered more revenue than doing nothing or retrying naively.*

### 1.3 Primary persona
| Persona | Need | Definition of success |
|---|---|---|
| Merchant ops lead (the buyer) | Stop losing MRR to failed renewals without hiring a collections team | Recovery rate ↑, no customer complaints from over-retrying |
| Razorpay reviewer (the actual v1 audience) | Judge engineering judgment under a bounded, auditable system | Can trace any single ₹ recovered back to a reason, a rule, and a log line |

### 1.4 Jobs-to-be-done
- "When a renewal fails, tell me *why* before you try again."
- "When you act on my behalf, show me you'll stop, not just retry forever."
- "When I ask 'did this actually work,' give me one number I can trust."

### 1.5 Scope — v1
**In:** subscription/mandate payment failures → classify → decide → gate → execute (retry / payment link / stop) → audit → batch metrics.
**Out (v2 backlog):** checkout drop-off recovery, B2B receivables chasing, voice/Hinglish outreach, promise-to-pay tracking, live merchant dashboard auth/multi-tenant.

### 1.6 Success metrics (v1, demo-measurable)
| Metric | Target | Why it matters |
|---|---|---|
| Recovery rate vs. naive-retry baseline | Agent > baseline on same batch | Proves the agent adds value, not just an API wrapper |
| Guardrail violation rate | 0 across test batch | Proves "bounded" isn't just a slide claim |
| Root-cause classification precision | Reported honestly, incl. confusion matrix | Matches Track 3/2 "honest metrics" bar |
| Audit completeness | 100% of actions traceable to rule + reasoning | This *is* the deliverable the panel scores |
| Median decision latency | < 3s per case | Believability of "agent," not batch script |

### 1.7 Assumptions & constraints
- Razorpay **test mode** only; no real money, real PII replaced with synthetic data.
- Time-boxed build (~5–6 days) — v1 optimizes for **one flow done rigorously** over breadth.
- Agent is **advisory-executor**, not autonomous-unbounded: every action passes a deterministic gate before any API call fires.

---

## 2. ANALYSIS — Requirements

### 2.1 Functional requirements
| ID | Requirement |
|---|---|
| FR-1 | System shall ingest a failed-payment/subscription event (webhook or batch replay) and persist it as a `RecoveryCase`. |
| FR-2 | System shall classify the failure into a fixed taxonomy (insufficient funds, expired instrument, mandate revoked, bank timeout, issuer decline, unknown). |
| FR-3 | System shall generate a recommended action from a fixed action set: `retry_now`, `retry_scheduled(t)`, `send_payment_link`, `escalate_human`, `stop`. |
| FR-4 | Every recommended action shall pass a guardrail gate before execution; a blocked action shall be logged with the specific rule that blocked it. |
| FR-5 | System shall execute approved actions against Razorpay test-mode APIs (Subscriptions, Payment Links). |
| FR-6 | System shall record an immutable audit entry per case: input → root cause → decision → gate result → execution result → final outcome. |
| FR-7 | System shall compute and report batch-level metrics: ₹ recovered, recovery rate, comparison to a naive-retry baseline, guardrail-block count. |
| FR-8 | System shall expose a case-level view showing the full reasoning trail for any single `RecoveryCase`. |

### 2.2 Non-functional requirements
| Category | Requirement |
|---|---|
| Explainability | Every action must cite the rule/reasoning that produced it — no unexplained state transitions. |
| Boundedness | Action space is fixed and enumerable; agent cannot invoke arbitrary API calls. |
| Auditability | Audit log is append-only; no action is executed without a preceding log entry. |
| Idempotency | Re-processing the same event must not double-execute (dedupe key = `subscription_id + attempt_number`). |
| Compliance | Retry cadence respects NPCI/RBI recurring-payment retry norms (no more than N attempts in a rolling window); revoked mandates are never retried. |
| Latency | Case processing < 3s p50 in test batch. |
| Security | Synthetic data only in v1; no real cardholder data touches the system. |

### 2.3 Actors & use cases
- **Merchant system (event source):** emits failed-payment/subscription webhooks.
- **Recovery Agent:** classifies, decides, executes.
- **Ops reviewer (human-in-the-loop):** receives escalations the agent explicitly refuses to auto-resolve.
- **Panel/evaluator:** consumes the audit trail and metrics dashboard as the primary "proof of work" artifact.

### 2.4 Data entities (conceptual)
`Merchant`, `Customer`, `Subscription`, `PaymentAttempt`, `RecoveryCase`, `GuardrailRule`, `Action`, `AuditLogEntry`, `BatchRun`.

### 2.5 Risk analysis
| Risk | Impact | Mitigation |
|---|---|---|
| Agent retries a customer into annoyance/churn | Reputational, real merchant harm | Hard retry cap + cooldown, enforced in code not in the prompt |
| Root-cause misclassification drives wrong action | Wasted recovery attempts | Deterministic rules first, LLM fallback only for ambiguous cases; both logged with confidence |
| Retrying a revoked mandate | Compliance violation (NPCI norms) | Explicit `stop` rule keyed on mandate status — non-negotiable, checked pre-execution |
| Cherry-picked demo numbers | Loses all credibility with panel | Report full batch results incl. failures, plus baseline comparison, in the audit dashboard itself |

### 2.6 Out of scope v1
Multi-tenant auth, live production billing, non-English/Hinglish voice channel, receivables/B2B invoicing.

---

## 3. DESIGN — Blueprint

### 3.1 High-level architecture
```
Merchant events (Razorpay test-mode webhooks)
        │
        ▼
[Ingestion] → RecoveryCase created (status: DETECTED)
        │
        ▼
[Root-Cause Classifier]  (rules engine + LLM fallback)
        │  status: CLASSIFIED
        ▼
[Decision Agent]  (Claude, fixed tool/action schema)
        │  status: DECIDED
        ▼
[Guardrail Gate]  (deterministic, config-driven rules)
   ├── BLOCKED → status: STOPPED (audit reason logged)
   └── APPROVED → status: GATED
        │
        ▼
[Execution Layer]  (Razorpay test-mode API client)
        │  status: EXECUTING → RESOLVED / ESCALATED / FAILED
        ▼
[Audit Log + Metrics Store] → Dashboard (case view + batch view)
```

### 3.2 Recovery case state machine
```
DETECTED → CLASSIFIED → DECIDED → GATED → EXECUTING → RESOLVED
                                     │                    │
                                     └──→ STOPPED          └──→ ESCALATED
```
Terminal states: `RESOLVED`, `STOPPED`, `ESCALATED`, `FAILED`. No transition skips a state — this is what makes the audit trail complete rather than a log of outcomes only.

### 3.3 Sequence — one case, happy path
1. Webhook: `subscription.charge.failed` → Ingestion creates `RecoveryCase(status=DETECTED)`.
2. Classifier reads Razorpay `error_code`/`error_reason` → assigns `root_cause=insufficient_funds`, confidence 0.94, `status=CLASSIFIED`.
3. Decision Agent receives case + customer history (attempt count, prior outcomes) → tool-call returns `retry_scheduled(t=+36h)` with rationale text.
4. Guardrail Gate checks: attempt_count < max(3)? cooldown elapsed? mandate active? → all pass → `status=GATED`.
5. Execution Layer schedules the retry via Razorpay test-mode Subscriptions API.
6. Outcome webhook arrives → `status=RESOLVED`, audit entry closed with recovered amount.
7. Metrics store increments batch counters.

### 3.4 Guardrail rule table (v1 baseline — config-driven, not hardcoded)
| Rule | Condition | Action |
|---|---|---|
| Max attempts | attempt_count ≥ 3 | Force `stop`, escalate |
| Cooldown | last_attempt < 12h ago | Block `retry_now`, force `retry_scheduled` |
| Mandate revoked | mandate.status == revoked | Force `stop` — non-overridable |
| High-value case | amount > ₹50,000 | Force `escalate_human` regardless of agent recommendation |
| Repeat unknown cause | root_cause == unknown twice | Force `escalate_human` |

### 3.5 Data model (entity sketch)
```
RecoveryCase(id, subscription_id, customer_id, amount, root_cause, confidence,
             decision, gate_result, status, created_at)
AuditLogEntry(id, case_id, stage, input_snapshot, output, rule_fired, timestamp)
GuardrailRule(id, name, condition_expr, forced_action, active)
BatchRun(id, batch_size, recovered_amount, recovery_rate, baseline_rate, blocked_count)
```

### 3.6 API design (internal service)
| Endpoint | Method | Purpose |
|---|---|---|
| `/events/payment-failed` | POST | Ingest a failure event, create case |
| `/cases/{id}` | GET | Full reasoning trail for one case |
| `/cases/{id}/audit` | GET | Raw audit log entries |
| `/batch/{id}/metrics` | GET | Aggregate recovery metrics vs. baseline |
| `/rules` | GET/PUT | Inspect/update guardrail config |

### 3.7 UI/UX — dashboard (the panel's actual window into the system)
**Design intent:** the dashboard *is* the audit trail made legible — not a decoration bolted on after the backend. Every screen should answer "why did the agent do that" in under 5 seconds of looking.

**Screens:**
1. **Recovery Queue** — list of cases, color-coded by state (amber = decided/gated, teal = resolved, coral = stopped, gray = escalated). Sortable by amount, root cause, state.
2. **Case Detail** — vertical timeline matching the state machine (3.2), each step showing the exact rule or model output that fired. This is the single most important screen for the demo.
3. **Batch Metrics** — one hero number (₹ recovered), a bar comparing agent vs. naive-retry baseline, a breakdown by root cause, and a guardrail-block count with reasons.
4. **Guardrail Config** — read-only in v1 (editable in v2) view of the rule table in 3.4, so the panel can see the bounds are explicit, not buried in a prompt.

**Visual system:**
- Typography: one grotesk for UI chrome/data (numbers need to be legible at a glance), one serif/voice face reserved for the single narrative line per case ("why we did this") — mirrors how the audit trail itself has a machine layer and a human-readable layer.
- Color encodes **state**, never brand decoration: teal = resolved/recovered, coral = stopped/blocked, amber = pending/escalated, gray = neutral/structural. Consistent across queue, case detail, and metrics — a reviewer should learn the palette once.
- Motion: none decorative. The only animation worth building is the state-machine timeline stepping forward on the case detail screen — it's the one place motion clarifies rather than distracts.

---

## 4. IMPLEMENTATION

### 4.1 Stack decisions
| Layer | Choice | Rationale |
|---|---|---|
| Backend | Python + FastAPI | Fast to scaffold, good typing for a state-machine-shaped domain |
| Decision agent | Claude API, fixed tool schema (5 tools = 5 allowed actions) | Bounded by construction — the model literally cannot call anything outside the action set |
| Storage | SQLite (v1) → Postgres-ready schema | Zero-ops for hackathon, same schema scales later |
| Frontend | React + Tailwind, single dashboard | Matches the three screens above, nothing speculative |
| Payments | Razorpay test-mode SDK (Subscriptions, Payment Links, Webhooks) | Required by the track brief |

### 4.2 Repo structure
```
/recovery-agent
  /app
    /ingestion         webhook handlers, event normalization
    /classifier         rules engine + LLM fallback
    /agent               Claude tool schema + decision logic
    /guardrails          rule config (YAML) + gate function
    /execution           Razorpay test-mode client wrapper
    /audit               append-only log writer, metrics aggregator
    /api                 FastAPI routes (section 3.6)
  /dashboard             React app (3 screens)
  /data                  synthetic batch generator, seed scripts
  /tests                 unit, integration, batch-eval
  ARCHITECTURE.md         (this document, trimmed for the repo)
  README.md
```

### 4.3 Guardrail gate — illustrative skeleton
```python
def gate(case: RecoveryCase, rules: list[GuardrailRule]) -> GateResult:
    for rule in rules:
        if rule.active and rule.condition(case):
            return GateResult(approved=False, forced_action=rule.forced_action,
                               rule_fired=rule.name)
    return GateResult(approved=True, forced_action=case.agent_decision,
                       rule_fired=None)
```
Rules are data (YAML/DB rows), not buried in the agent prompt — this is what makes "bounded" auditable rather than aspirational.

### 4.4 Decision agent — tool schema shape
```json
{
  "name": "recommend_action",
  "input_schema": {
    "action": {"enum": ["retry_now", "retry_scheduled", "send_payment_link",
                          "escalate_human", "stop"]},
    "scheduled_for": "ISO8601 | null",
    "rationale": "string, one sentence"
  }
}
```
The model can only return one of five enum values — this closes off the "agent went rogue" failure mode by construction, not by hoping the prompt holds.

---

## 5. DEBUG — Observability & Failure Handling

### 5.1 Logging strategy
Every stage transition writes one structured audit entry (`stage`, `input_snapshot`, `output`, `rule_fired`, `timestamp`) — this doubles as both debug log and product feature (Case Detail screen reads directly from it).

### 5.2 Anticipated failure modes and mitigations
| Failure mode | Detection | Mitigation |
|---|---|---|
| Classifier defaults everything to `unknown` | Confusion matrix shows unknown-heavy skew | Rules-first fallback order; escalate on repeat unknown (guardrail 3.4) |
| Agent recommends an action guardrails always override | Batch metrics show high block rate for one action type | Signal to tighten the agent's context (give it the rule table so it stops proposing dead-on-arrival actions) |
| Duplicate webhook delivery double-executes | Dedupe key collision check on ingest | Idempotency key = `subscription_id + attempt_number`, enforced at ingestion, not execution |
| Silent execution failure against Razorpay API | Non-2xx response without matching outcome webhook | Explicit `FAILED` terminal state, not left `EXECUTING` forever |

### 5.3 "What broke" narrative (fill in as you build — this is what the panel interview asks for)
> _Example shape: "V1 retried `insufficient_funds` failures immediately, and the batch recovery rate was near zero. Instrumenting the audit trail showed most declines recurred within minutes because the customer hadn't been paid yet. Switching to `retry_scheduled` with a 36h window changed recovery rate from X% to Y% on the same batch."_
Replace with your real failure once you run the actual batch — a true number beats this template.

---

## 6. TEST — Test Plan

### 6.1 Test pyramid
- **Unit:** classifier rule matching, guardrail rule evaluation, state machine transition legality.
- **Integration:** real Razorpay test-mode calls (create failing payment → observe webhook → confirm case created).
- **Scenario/batch evaluation:** run ≥50 synthetic failed-payment records (mirroring Track 4's own bar for batch size) through the full pipeline; compare against a naive-retry baseline.

### 6.2 Guardrail adversarial test cases (must all pass before demo)
| Case | Expected result |
|---|---|
| Mandate revoked, agent recommends retry | Gate forces `stop`, logs rule `mandate_revoked` |
| 4th consecutive attempt | Gate forces `stop`/escalate, never a 4th retry |
| ₹75,000 case, agent recommends auto-retry | Gate forces `escalate_human` regardless |
| Retry attempted 2h after prior attempt | Gate blocks, forces scheduled retry respecting cooldown |
| Duplicate webhook for same attempt | Second event does not create a second execution |

### 6.3 Metrics computation (report exactly this, honestly, in the pitch)
- **Recovered amount** = Σ amount where `status=RESOLVED`.
- **Recovery rate** = resolved cases / total cases in batch.
- **Baseline recovery rate** = same batch run through "always retry immediately" logic — this comparison is the credibility anchor.
- **Guardrail block rate** = blocked actions / total decisions, with reason breakdown.
- **Classification precision/recall** per root-cause class, confusion matrix included — not just an aggregate accuracy number.

### 6.4 v1 acceptance criteria
- [ ] 100% of executed actions have a complete audit trail (input → cause → decision → gate → outcome).
- [ ] Zero guardrail violations across the full test batch.
- [ ] Agent recovery rate reported alongside, and ideally above, naive-retry baseline on the same batch.
- [ ] Case Detail screen reproduces the exact reasoning for any case a reviewer clicks into.
- [ ] One real "what broke" story replaces the template in 5.3.

---

## 7. Traceability (sample)
| Requirement | Design element | Test |
|---|---|---|
| FR-4 (guardrail gate) | §3.4 rule table, §4.3 gate function | §6.2 adversarial cases |
| FR-6 (audit log) | §3.5 AuditLogEntry, §5.1 logging | §6.4 acceptance criterion 1 |
| FR-7 (batch metrics) | §3.6 `/batch/{id}/metrics` | §6.3 metrics computation |

---

## 8. Appendix

**Glossary:** *Mandate* — NPCI/UPI Autopay or eNACH standing instruction. *Recovery case* — one failed-payment lifecycle tracked end-to-end. *Naive-retry baseline* — control logic that retries every failure immediately, used to prove the agent adds value.

**Open questions for v2:** multi-merchant auth model, real payment-link deep-linking into WhatsApp/SMS, extending the guardrail config to be merchant-editable via the dashboard rather than read-only.
