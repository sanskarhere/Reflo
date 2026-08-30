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
