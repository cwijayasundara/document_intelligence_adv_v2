"""Shared helpers for metric-based evaluators."""

from __future__ import annotations

import re
from typing import Any, Protocol


class HasOutputs(Protocol):
    outputs: dict[str, Any] | None


def norm(value: Any) -> str:
    """Whitespace-normalise a stringified value for text comparisons."""
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def norm_loose(value: Any) -> str:
    """Normalisation for loose string match — lowercases, strips punctuation."""
    return re.sub(r"[^\w\s]", "", norm(value)).lower()


def extract_numeric(value: Any) -> float | None:
    """Pull the first numeric value out of a string (strips '%', '$', commas)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value).replace(",", ""))
    if match is None:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def get(obj: Any, key: str, default: Any = None) -> Any:
    """Look up a key on either a dict or an attribute, with a default."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
