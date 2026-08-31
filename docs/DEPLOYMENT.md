# Deploying Reflo's Backend

Complete instructions for taking `backend/` from repo to a live, testable
Render deployment. Follow in order — later steps assume earlier ones are done.

---

## 0. Prerequisites

Have these ready before you start:
- A GitHub account with this repo pushed (see step 1)
- A Render account (render.com) — free tier is enough for the hackathon
- Razorpay **test-mode** API keys (Key ID + Key Secret) from the Razorpay dashboard
- An xAI account (console.x.ai) with an `XAI_API_KEY` — free trial credits apply
- **Before you deploy:** confirm `grok-4.6` (the model slug hardcoded in
  `backend/app/agent/decision.py`) is still current at docs.x.ai/console.x.ai.
  xAI renames/retires model slugs fairly often — if it's changed, update the
  `MODEL` constant in that file before pushing, since a stale slug will make
  every decision-agent call fail at runtime, not at build time.
- A random string of your own choosing for `ADMIN_SECRET` (protects the batch-run endpoint)

---

## 1. Push to GitHub

```bash
cd reflo
git init                      # if not already a repo
git add .
git commit -m "initial backend, ready for deployment"
git branch -M main
git remote add origin https://github.com/<you>/reflo.git
git push -u origin main
```

---

## 2. Deploy via Render Blueprint

`backend/render.yaml` already defines both the web service and a free
Postgres database, wired together automatically — you don't configure
these by hand.

1. Render dashboard → **New → Blueprint**.
2. Connect the `reflo` GitHub repo.
3. Render detects `backend/render.yaml` and shows you two resources to
   create: `reflo-backend` (web service) and `reflo-db` (Postgres). Confirm.
4. Click **Apply** — Render provisions both and links `DATABASE_URL`
   between them automatically. First build takes a few minutes.

---

## 3. Set environment variables

In the Render dashboard, open `reflo-backend` → **Environment**, and set
these five (they're `sync: false` in `render.yaml`, meaning Render expects
you to fill them in — they're intentionally not committed to the repo):

| Variable | Where to get it |
|---|---|
| `RAZORPAY_KEY_ID` | Razorpay Dashboard → Settings → API Keys (test mode) |
| `RAZORPAY_KEY_SECRET` | Same screen, shown once at generation — save it |
| `RAZORPAY_WEBHOOK_SECRET` | You set this yourself when creating the webhook in step 5 below |
| `XAI_API_KEY` | console.x.ai → API Keys |
| `ADMIN_SECRET` | Any random string you choose — this is your own password for `/admin/run-batch` |

`DATABASE_URL` is already set automatically by the Blueprint — don't touch it.
`ALLOWED_ORIGIN` defaults to `*`; come back and set it to your real Vercel
URL once the frontend is deployed (tighter CORS).

Save changes — Render redeploys automatically when env vars change.

---

## 4. Verify the deployment actually booted

```bash
curl https://<your-render-url>/health
```
Expect `{"status": "ok"}`. If this fails, check the Render **Logs** tab —
the most common first-deploy failure is a bad `DATABASE_URL`, which would
show as a SQLAlchemy connection error on startup.

Also open `https://<your-render-url>/docs` — you should see the Swagger UI
with all 6 routes listed (`/webhooks/razorpay`, `/cases/{id}`,
`/cases/{id}/audit`, `/batch/{id}/metrics`, `/rules`, `/admin/run-batch`).

---

## 5. Configure the Razorpay webhook

1. Razorpay Dashboard (test mode) → **Settings → Webhooks → Add New Webhook**.
2. Webhook URL: `https://<your-render-url>/webhooks/razorpay`
3. Secret: choose a value **and use this exact same value** as
   `RAZORPAY_WEBHOOK_SECRET` in step 3 above (set it in Render before or
   after — just make sure they match).
4. Active events — check these three:
   - `subscription.charge.failed`
   - `payment_link.paid`
   - `payment.captured`
5. Save.

---

## 6. Smoke-test the webhook route directly

`/docs` can't sign requests for you (see below), so use the included script:

```bash
cd backend
python -m scripts.send_test_webhook \
  --url https://<your-render-url>/webhooks/razorpay \
  --secret <your RAZORPAY_WEBHOOK_SECRET> \
  --event subscription.charge.failed
```
Expect a 200 response with a `case_id`. If you get a 401, your
`RAZORPAY_WEBHOOK_SECRET` in Render doesn't match what you passed to the
script — check for typos/whitespace on both sides.

Why not just use `/docs` for this one route: it reads the raw request body
directly rather than a declared schema, and it requires an HMAC-SHA256
signature header that Swagger UI has no way to compute. Every other route
works fine through `/docs`.

---

## 7. Run a real batch

```bash
curl -X POST "https://<your-render-url>/admin/run-batch?n=50" \
     -H "X-Admin-Secret: <your ADMIN_SECRET>"
```
This generates 50 synthetic failed-payment cases and runs each through the
full pipeline (classify → decide via Grok → gate → execute against real
Razorpay test-mode APIs). Prints and returns a `batch_id`.

Check the result:
```bash
curl https://<your-render-url>/batch/<batch_id>/metrics
```
or via `/docs`.

At this point, expect `recovered_amount_paise` to be **near zero** — that's
correct, not a bug. See the next step.

---

## 8. Get a real (non-zero) recovered-₹ number

`RESOLVED` only happens when a real payment actually succeeds and Razorpay
sends the outcome webhook back. To trigger that for real:

1. Pull a `short_url` from one of the batch's `send_payment_link` cases
   (check `GET /cases/{id}/audit` for cases where the execution result
   includes a payment link, or check your Razorpay test-mode dashboard
   under Payment Links directly).
2. Open it and complete payment using a Razorpay test card
   (test-mode checkout accepts these without moving real money).
3. This fires `payment_link.paid` back to your webhook, which resolves the
   matching case. Re-check `/batch/{batch_id}/metrics` — recovered amount
   should now reflect it.

---

## 9. Ongoing debugging

- **Case looks wrong (wrong root cause, wrong mandate_status):** check
  `GET /cases/{id}/audit` — the `DETECTED` stage's `input_snapshot` shows
  the raw webhook payload Razorpay actually sent. Compare it against the
  field-mapping assumptions documented in `ingestion/webhooks.py`'s
  docstring — those were inferred from docs, not a captured payload, so
  this is the most likely source of a real bug.
- **Cold starts:** free Render web services spin down after 15 minutes
  idle and take about a minute to wake. Hit `/health` before a live demo.
- **Re-running tests for real** (never executed with real `pytest` yet,
  only verified with manual assertion scripts during the build):
  ```bash
  pip install -r requirements-dev.txt
  pytest
  ```

---

## Deployment checklist

- [ ] Repo pushed to GitHub
- [ ] Render Blueprint applied (web service + Postgres both created)
- [ ] All 5 env vars set in Render dashboard
- [ ] `/health` returns `{"status": "ok"}`
- [ ] `/docs` loads and shows all 6 routes
- [ ] Razorpay webhook configured, secret matches `RAZORPAY_WEBHOOK_SECRET`
- [ ] `send_test_webhook.py` gets a 200 response
- [ ] `/admin/run-batch` runs successfully
- [ ] At least one payment link manually completed → real recovered ₹ confirmed
- [ ] `pytest` run for real at least once
