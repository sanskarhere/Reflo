"""
Runs the classifier + guardrail gate against a synthetic batch and prints
honest metrics — classification precision/recall per class, plus guardrail
block counts. This is the script whose output belongs in the pitch deck;
run it, don't hand-write the numbers.

Note: this exercises classification + gating only. Full recovery-rate vs.
baseline (section 6.3) requires the execution layer (Razorpay test-mode
calls) to produce a real final_status, so that comparison is wired in once
execution/razorpay_client.py is implemented.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.synthetic_batch_generator import generate_batch
from app.classifier.rules import classify_by_rule
from app.guardrails.gate import gate
from app.audit.metrics import compute_classification_metrics


def run(n: int = 50):
    batch = generate_batch(n)

    for case in batch:
        predicted = classify_by_rule(case["error_code"], case["error_reason"])
        case["predicted_root_cause"] = predicted if predicted is not None else "unknown"

        # naive proposed action for gate-testing purposes; real agent wires in later
        gate_result = gate(case, proposed_action="retry_now")
        case["gate_approved"] = gate_result.approved
        case["gate_action"] = gate_result.action
        case["gate_rule_fired"] = gate_result.rule_fired

    cls_metrics = compute_classification_metrics(batch)

    print(f"Batch size: {len(batch)}\n")
    print(f"Classifier accuracy: {cls_metrics['accuracy']:.2%}\n")
    print("Per-class precision / recall / support:")
    for cls, m in sorted(cls_metrics["per_class"].items()):
        p = f"{m['precision']:.2f}" if m["precision"] is not None else "n/a"
        r = f"{m['recall']:.2f}" if m["recall"] is not None else "n/a"
        print(f"  {cls:<20} precision={p:<6} recall={r:<6} support={m['support']}")

    blocked = sum(1 for c in batch if not c["gate_approved"])
    print(f"\nGuardrail: {blocked}/{len(batch)} cases blocked from naive retry_now")
    rule_counts: dict[str, int] = {}
    for c in batch:
        if c["gate_rule_fired"]:
            rule_counts[c["gate_rule_fired"]] = rule_counts.get(c["gate_rule_fired"], 0) + 1
    for rule, count in sorted(rule_counts.items(), key=lambda x: -x[1]):
        print(f"  {rule:<25} fired {count}x")

    return batch, cls_metrics


if __name__ == "__main__":
    run(50)
