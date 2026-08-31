# Reflo
### Reflowing revenue that almost got stuck.

A bounded, auditable agent that detects failed subscription payments, classifies
the root cause, decides a recovery action within a fixed action set, gates it
against explicit guardrails, executes it against Razorpay test-mode APIs, and
logs a complete audit trail.

Built for Razorpay's AI Buildathon — Track: AI Revenue Recovery.

See `docs/ARCHITECTURE.md` for the full SRS/SDD.

## Repo layout
- `backend/` — FastAPI service. Deploy target: **Render**.
- `frontend/` — Next.js dashboard (Recovery Queue, Case Detail, Batch Metrics, Guardrail Config). Deploy target: **Vercel**.
- `docs/` — architecture and design documentation.

## Local dev
```
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev
```

## Deploying to Render (free tier)
Free Render web services have **no shell/SSH access and can't run one-off
jobs** — everything has to go through the running app itself. Steps:

1. Push this repo to GitHub.
2. In Render, **New → Blueprint**, point it at the repo. `render.yaml`
   provisions both the web service and a free Postgres database, and wires
   `DATABASE_URL` between them automatically.
3. Set the real secret env vars in the Render dashboard (never commit
   these): `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`,
   `RAZORPAY_WEBHOOK_SECRET`, `XAI_API_KEY`, `ADMIN_SECRET` (any random
   string — protects the batch-run endpoint below).
4. In Razorpay's test-mode dashboard, add **one webhook** pointing at
   `https://<your-render-url>/webhooks/razorpay`, subscribed to
   `subscription.charge.failed`, `payment_link.paid`, `payment.captured`.
5. Trigger a batch run over HTTP (no shell needed):
   ```
   curl -X POST "https://<your-render-url>/admin/run-batch?n=50" \
        -H "X-Admin-Secret: <your ADMIN_SECRET>"
   ```
6. To get a real (non-zero) recovered-₹ number: go complete a few of the
   generated payment links in Razorpay's test-mode checkout with a test
   card. That fires `payment_link.paid` back to your webhook and moves
   those cases from `EXECUTING` to genuinely `RESOLVED`.
7. Check `GET /batch/{batch_id}/metrics` (the batch ID prints from step 5)
   for the real numbers.

Note: free web services spin down after 15 minutes idle and take ~1 minute
to wake on the next request — ping the service before a live demo so the
first webhook isn't lost to a cold start.
