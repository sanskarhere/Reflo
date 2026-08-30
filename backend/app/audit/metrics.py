"""
Batch metrics — docs/ARCHITECTURE.md section 6.3. Computed exactly as
specified there so the pitch numbers and the design doc never drift apart.
"""
from collections import defaultdict


def compute_classification_metrics(cases: list[dict], predicted_key: str = "predicted_root_cause",
                                     true_key: str = "true_root_cause") -> dict:
    """
    Precision/recall/confusion matrix per root-cause class. Requires both
    predicted and true labels on each case (true label is eval-only, never
    fed to the classifier itself).
    """
    classes = sorted({c[true_key] for c in cases} | {c[predicted_key] for c in cases})
    confusion = {t: defaultdict(int) for t in classes}
    for c in cases:
        confusion[c[true_key]][c[predicted_key]] += 1

    per_class = {}
    for cls in classes:
        tp = confusion[cls][cls]
        fp = sum(confusion[other][cls] for other in classes if other != cls)
        fn = sum(v for k, v in confusion[cls].items() if k != cls)
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        per_class[cls] = {"precision": precision, "recall": recall, "support": sum(confusion[cls].values())}

    accuracy = sum(confusion[c][c] for c in classes) / len(cases) if cases else None
    return {
        "accuracy": accuracy,
        "per_class": per_class,
        "confusion_matrix": {t: dict(preds) for t, preds in confusion.items()},
    }


def compute_batch_metrics(cases: list[dict]) -> dict:
    """
    Each case dict is expected to carry, after running through the full
    pipeline: amount_paise, final_status ('RESOLVED' | 'STOPPED' |
    'ESCALATED' | 'FAILED'), baseline_status (same field computed by the
    naive-retry-immediately baseline on the same case), gate_blocked (bool).
    """
    total = len(cases)
    if total == 0:
        return {"batch_size": 0}

    recovered_amount = sum(c["amount_paise"] for c in cases if c["final_status"] == "RESOLVED")
    recovery_rate = sum(1 for c in cases if c["final_status"] == "RESOLVED") / total
    baseline_rate = sum(1 for c in cases if c.get("baseline_status") == "RESOLVED") / total
    blocked_count = sum(1 for c in cases if c.get("gate_blocked"))

    return {
        "batch_size": total,
        "recovered_amount_paise": recovered_amount,
        "recovery_rate": recovery_rate,
        "baseline_recovery_rate": baseline_rate,
        "uplift_vs_baseline": recovery_rate - baseline_rate,
        "guardrail_blocked_count": blocked_count,
    }
