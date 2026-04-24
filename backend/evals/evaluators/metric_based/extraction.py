"""Extraction metric evaluators — exact match, numeric tolerance, source substring."""

from __future__ import annotations

from typing import Any

from ._helpers import HasOutputs, extract_numeric, get, norm_loose


def _prediction_for_field(run: HasOutputs, field_name: str) -> dict[str, Any]:
    """Pull (value, source_text) for `field_name` out of an ExtractionResult."""
    outputs = run.outputs or {}
    fields = outputs.get("fields") if isinstance(outputs, dict) else getattr(outputs, "fields", [])
    for field in fields or []:
        if get(field, "field_name") == field_name:
            return {
                "value": get(field, "extracted_value"),
                "source_text": get(field, "source_text"),
            }
    return {"value": None, "source_text": None}


def _field_name(example: HasOutputs) -> str:
    return get(example.outputs, "field_name") or get(example, "inputs", {}).get("field_name") or ""


def extraction_exact_match(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Strict string match (whitespace-normalised) against `expected_value`.

    Honours `expected_accepted_values` (list) as an allowlist when present.
    Honours `expected_empty=True` — predictions must be empty/None/blank.
    """
    expected = example.outputs or {}
    predicted = _prediction_for_field(run, _field_name(example))
    expected_value = expected.get("expected_value")
    accepted = expected.get("expected_accepted_values") or (
        [expected_value] if expected_value else []
    )
    expected_empty = bool(expected.get("expected_empty"))
    pred_norm = norm_loose(predicted["value"])

    if expected_empty:
        matched = pred_norm in ("", "none", "null", "n/a")
        return {
            "key": "extraction_exact_match",
            "score": 1.0 if matched else 0.0,
            "comment": f"expected_empty=True predicted={predicted['value']!r}",
        }

    accepted_norm = {norm_loose(v) for v in accepted if v is not None}
    matched = pred_norm in accepted_norm and pred_norm != ""
    return {
        "key": "extraction_exact_match",
        "score": 1.0 if matched else 0.0,
        "comment": f"predicted={predicted['value']!r} accepted={sorted(accepted_norm)!r}",
    }


def extraction_numeric_tolerance(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Numeric match within `expected_tolerance` (absolute)."""
    expected = example.outputs or {}
    expected_num = expected.get("expected_numeric_value")
    tol = expected.get("expected_tolerance", 0.0) or 0.0

    if expected_num is None:
        return {"key": "extraction_numeric_tolerance", "score": None, "comment": "n/a"}

    predicted = _prediction_for_field(run, _field_name(example))
    pred_num = extract_numeric(predicted["value"])

    if pred_num is None:
        return {
            "key": "extraction_numeric_tolerance",
            "score": 0.0,
            "comment": f"predicted={predicted['value']!r} expected={expected_num}",
        }

    ok = abs(pred_num - float(expected_num)) <= float(tol)
    return {
        "key": "extraction_numeric_tolerance",
        "score": 1.0 if ok else 0.0,
        "comment": f"predicted={pred_num} expected={expected_num} tol={tol}",
    }


def extraction_source_substring(run: HasOutputs, example: HasOutputs) -> dict[str, Any]:
    """Verifies that `source_text` appears (case-insensitively) in the source doc.

    When `expected_source_substring` is set, ALSO checks the substring is
    actually inside the predicted source_text — catching plausible-but-wrong
    hallucinated sources.
    """
    expected = example.outputs or {}
    required_substring = expected.get("expected_source_substring")
    inputs = get(example, "inputs", {}) or {}
    source_doc = inputs.get("parsed_content") or inputs.get("inline_content") or ""

    predicted = _prediction_for_field(run, _field_name(example))
    pred_source = predicted["source_text"] or ""

    if not pred_source and expected.get("expected_empty"):
        return {
            "key": "extraction_source_substring",
            "score": 1.0,
            "comment": "empty value, empty source (expected)",
        }

    in_doc = pred_source.strip() != "" and pred_source.strip().lower() in source_doc.lower()
    if required_substring:
        has_substring = required_substring.lower() in pred_source.lower()
        ok = in_doc and has_substring
        comment = f"in_doc={in_doc} has_required={has_substring}"
    else:
        ok = in_doc
        comment = f"in_doc={in_doc}"

    return {"key": "extraction_source_substring", "score": 1.0 if ok else 0.0, "comment": comment}
