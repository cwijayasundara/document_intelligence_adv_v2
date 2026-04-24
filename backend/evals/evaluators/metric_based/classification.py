"""Classification metric evaluators — accuracy, confidence-in-range, ECE."""

from __future__ import annotations

from typing import Any

from ._helpers import HasOutputs, extract_numeric, get, norm_loose


def classification_accuracy(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Exact match between predicted `category_name` and `expected_category`."""
    predicted = norm_loose(get(run.outputs, "category_name"))
    expected = norm_loose(get(example.outputs, "expected_category"))
    matched = predicted == expected and predicted != ""
    return {
        "key": "classification_accuracy",
        "score": 1.0 if matched else 0.0,
        "comment": f"predicted={predicted!r} expected={expected!r}",
    }


def classification_confidence_in_range(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Checks `confidence` against `expected_min_confidence` / `expected_max_confidence`."""
    confidence = extract_numeric(get(run.outputs, "confidence"))
    lo = extract_numeric(get(example.outputs, "expected_min_confidence"))
    hi = extract_numeric(get(example.outputs, "expected_max_confidence"))

    if confidence is None:
        return {
            "key": "classification_confidence_in_range",
            "score": 0.0,
            "comment": "no confidence reported",
        }

    ok_lo = lo is None or confidence >= lo
    ok_hi = hi is None or confidence <= hi
    score = 1.0 if ok_lo and ok_hi else 0.0
    return {
        "key": "classification_confidence_in_range",
        "score": score,
        "comment": f"confidence={confidence} lo={lo} hi={hi} ok_lo={ok_lo} ok_hi={ok_hi}",
    }


def calibration_error(runs: list[HasOutputs], examples: list[HasOutputs]) -> dict[str, Any]:
    """Expected Calibration Error (ECE) across a whole experiment.

    Buckets predicted confidence in [0,100] into deciles; ECE is the weighted
    sum of |mean_confidence_in_bucket - accuracy_in_bucket|. Registered as a
    **summary** evaluator that receives the full list of runs.
    """
    if not runs:
        return {"key": "calibration_ece", "score": 0.0, "comment": "no runs"}

    buckets: list[list[tuple[float, bool]]] = [[] for _ in range(10)]
    for run, example in zip(runs, examples):
        confidence = extract_numeric(get(run.outputs, "confidence"))
        if confidence is None:
            continue
        predicted = norm_loose(get(run.outputs, "category_name"))
        expected = norm_loose(get(example.outputs, "expected_category"))
        correct = predicted == expected and predicted != ""
        idx = min(9, max(0, int(confidence // 10)))
        buckets[idx].append((confidence, correct))

    total = sum(len(b) for b in buckets)
    if total == 0:
        return {"key": "calibration_ece", "score": 0.0, "comment": "no valid samples"}

    ece = 0.0
    for bucket in buckets:
        if not bucket:
            continue
        mean_conf = sum(conf for conf, _ in bucket) / len(bucket) / 100.0
        accuracy = sum(1 for _, ok in bucket if ok) / len(bucket)
        weight = len(bucket) / total
        ece += weight * abs(mean_conf - accuracy)

    return {
        "key": "calibration_ece",
        "score": round(ece, 4),
        "comment": f"n={total} lower_is_better",
    }
