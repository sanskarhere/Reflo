"""
Standalone script: generates a synthetic batch, runs each case through the
full pipeline against a real DB session, and persists a BatchRun summary —
this is what produces the actual pitch numbers, not hand-typed ones.

Usage:
    cd backend && python -m scripts.run_batch --n 50

IMPORTANT — read before trusting the recovered-₹ number this produces:
process_case() never returns RESOLVED directly (see pipeline.py docstring)
— that only happens later, when a real payment_link.paid or
payment.captured webhook arrives after a customer actually completes a
payment. Running this script alone will correctly show cases landing in
EXECUTING/STOPPED/ESCALATED, with recovered_amount at or near zero. To get
a genuine non-zero recovered-₹ number: run this script against real
Razorpay test-mode keys, then actually complete a few of the generated
payment links using Razorpay's test-mode checkout (test cards work fine in
test mode), which fires the real outcome webhook and moves those cases to
RESOLVED. Reporting a recovered-₹ number without doing this would be
exactly the invented metric the "honest metrics" bar exists to catch.
"""
import argparse
import uuid

from app.audit.metrics import compute_batch_metrics
from app.db import Base, SessionLocal, engine
from app.models import BatchRun, RecoveryCase
from app.pipeline import process_case
from data.synthetic_batch_generator import generate_batch


def run(n: int = 50) -> str:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    records = generate_batch(n)

    # Create all cases first so build_case_context() can see prior cases
    # for the SAME subscription within this batch, matching how real
    # webhook-driven ingestion would build up history over time.
    cases = []
    for rec in records:
        case = RecoveryCase(
            id=str(uuid.uuid4()), subscription_id=rec["subscription_id"],
            customer_id=rec["customer_id"], amount=rec["amount_paise"],
            error_code=rec["error_code"], error_reason=rec["error_reason"],
            mandate_status=rec["mandate_status"], status="DETECTED",
        )
        db.add(case)
        cases.append((case, rec))
    db.commit()

    result_dicts = []
    for case, rec in cases:
        prior = [
            {"subscription_id": c.subscription_id,
             "created_at": c.created_at.isoformat() if c.created_at else None,
             "root_cause": c.root_cause}
            for c, _ in cases if c.id != case.id and c.subscription_id == case.subscription_id
        ]
        case_input = {
            "id": case.id, "subscription_id": case.subscription_id, "customer_id": case.customer_id,
            "amount_paise": case.amount, "mandate_status": case.mandate_status,
            "error_code": case.error_code, "error_reason": case.error_reason,
        }

        # NOTE: no decision_client/execution_client passed here — real runs
        # need your XAI_API_KEY and Razorpay test-mode keys wired via the
        # normal env-based lazy client construction in decision.py /
        # razorpay_client.py. This script intentionally doesn't stub them,
        # so a dry run without real keys will raise, which is correct —
        # better a loud failure than a batch of fabricated results.
        result = process_case(case_input, prior)

        case.root_cause = result["root_cause"]
        case.status = result["status"]
        db.commit()

        # naive baseline for comparison: "always retry_now blindly" — a
        # revoked mandate never recovers under blind retry either, so that's
        # the one honest exclusion; everything else is optimistically
        # counted as recoverable under the baseline (upper bound, not a
        # real simulation of Razorpay's own retry success rate).
        baseline_status = "STOPPED" if rec["mandate_status"] == "revoked" else "RESOLVED"

        result_dicts.append({
            "amount_paise": case.amount,
            "final_status": case.status,
            "baseline_status": baseline_status,
            "gate_blocked": bool(result["gate_result"] and not result["gate_result"].approved),
        })

    metrics = compute_batch_metrics(result_dicts)

    batch = BatchRun(
        id=str(uuid.uuid4()), batch_size=n,
        recovered_amount=metrics["recovered_amount_paise"],
        recovery_rate=metrics["recovery_rate"],
        baseline_rate=metrics["baseline_recovery_rate"],
        blocked_count=metrics["guardrail_blocked_count"],
    )
    db.add(batch)
    db.commit()

    print(f"Batch {batch.id}")
    print(f"  size: {metrics['batch_size']}")
    print(f"  recovered so far: {metrics['recovered_amount_paise']} paise")
    print(f"  recovery rate: {metrics['recovery_rate']:.2%} (real, not yet including pending EXECUTING cases)")
    print(f"  baseline rate: {metrics['baseline_recovery_rate']:.2%} (optimistic upper bound, see script docstring)")
    print(f"  guardrail blocked: {metrics['guardrail_blocked_count']}/{n}")

    return batch.id


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=50)
    args = parser.parse_args()
    run(args.n)
