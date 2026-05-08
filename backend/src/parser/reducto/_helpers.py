"""Internal helpers for the Reducto Cloud API client."""

from __future__ import annotations

import logging
from typing import Any

from src.parser.reducto.types import (
    BlockConfidence,
    ParseResult,
    ReductoCitation,
    ReductoExtractedField,
    ReductoParseError,
)

logger = logging.getLogger(__name__)


def build_parse_result(data: dict[str, Any]) -> ParseResult:
    """Convert a raw /parse response into a ParseResult with confidence."""
    job_id = data.get("job_id", "unknown")
    usage = data.get("usage", {})
    logger.info(
        "Parse complete job_id=%s pages=%s credits=%s",
        job_id,
        usage.get("num_pages", "?"),
        usage.get("credits", "?"),
    )

    result = data.get("result", {})
    chunks = result.get("chunks", [])
    if not chunks:
        raise ReductoParseError(
            f"Parse returned no chunks for job_id={job_id}: "
            f"result_type={result.get('type', 'unknown')}"
        )

    content = "\n\n".join(chunk.get("content", "") for chunk in chunks)

    block_confidences: list[BlockConfidence] = []
    for chunk in chunks:
        for block in chunk.get("blocks", []):
            block_confidences.append(
                BlockConfidence(
                    block_type=block.get("type", "Unknown"),
                    confidence=block.get("confidence", "high"),
                )
            )

    if block_confidences:
        high_count = sum(1 for b in block_confidences if b.confidence == "high")
        confidence_pct = (high_count / len(block_confidences)) * 100
    else:
        confidence_pct = 100.0

    has_low = any(b.confidence == "low" for b in block_confidences)
    logger.info(
        "Parse confidence for job_id=%s: %.1f%% (%d blocks, %s low-confidence)",
        job_id,
        confidence_pct,
        len(block_confidences),
        "has" if has_low else "no",
    )
    return ParseResult(
        content=content,
        confidence_pct=round(confidence_pct, 1),
        block_confidences=block_confidences,
        has_low_confidence=has_low,
        job_id=job_id,
    )


def criteria_list(criteria: Any) -> list[str]:
    if isinstance(criteria, list):
        return [str(item) for item in criteria if str(item).strip()]
    if isinstance(criteria, str) and criteria.strip():
        return [line.strip(" -") for line in criteria.splitlines() if line.strip(" -")]
    return ["matches this category"]


def classification_confidence(data: dict[str, Any], category_name: str) -> int:
    categories = data.get("response_confidence", {}).get("categories", [])
    for item in categories:
        if item.get("category") == category_name:
            return round(float(item.get("confidence", 0.0)) * 100)
    return 50 if category_name else 0


def classification_reasoning(data: dict[str, Any], category_name: str) -> str:
    categories = data.get("response_confidence", {}).get("categories", [])
    for item in categories:
        if item.get("category") != category_name:
            continue
        criteria = item.get("criteria_confidence", [])
        if not criteria:
            return "Reducto selected the best matching category."
        parts = [
            f"{c.get('criterion', 'criterion')}: {c.get('confidence', 'unknown')}" for c in criteria
        ]
        return "Reducto criteria confidence: " + "; ".join(parts)
    return "Reducto selected the best matching category."


def extraction_schema(fields: list[dict[str, Any]]) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    type_map = {
        "string": "string",
        "number": "number",
        "date": "string",
        "currency": "string",
        "percentage": "string",
    }
    for field_def in fields:
        name = field_def["field_name"]
        properties[name] = {
            "type": type_map.get(field_def.get("data_type", "string"), "string"),
            "description": field_def.get("description") or field_def.get("display_name", ""),
        }
        if field_def.get("required"):
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def extract_fields_from_response(
    data: dict[str, Any],
    extraction_fields: list[dict[str, Any]],
) -> list[ReductoExtractedField]:
    raw_result = data.get("result", {})
    if isinstance(raw_result, list):
        result_obj = raw_result[0] if raw_result and isinstance(raw_result[0], dict) else {}
    elif isinstance(raw_result, dict):
        result_obj = raw_result
    else:
        result_obj = {}

    fields: list[ReductoExtractedField] = []
    for field_def in extraction_fields:
        name = field_def["field_name"]
        raw_value = result_obj.get(name)
        value, source, confidence, citations = _unwrap_extracted_value(raw_value)
        fields.append(
            ReductoExtractedField(
                field_name=name,
                extracted_value=value,
                source_text=source,
                confidence=confidence,
                citations=citations,
            )
        )
    return fields


def _unwrap_extracted_value(
    raw_value: Any,
) -> tuple[str, str, str, list[ReductoCitation]]:
    if isinstance(raw_value, dict) and "value" in raw_value:
        raw_citations = raw_value.get("citations") or []
        citations = [_to_citation(c) for c in raw_citations if isinstance(c, dict)]
        first = citations[0] if citations else None
        value = raw_value.get("value")
        return (
            "" if value is None else str(value),
            first.content if first else "",
            first.confidence if first else "medium",
            citations,
        )
    if raw_value is None:
        return "", "", "low", []
    return str(raw_value), "", "medium", []


def _to_citation(raw: dict[str, Any]) -> ReductoCitation:
    bbox = raw.get("bbox", {}) if isinstance(raw.get("bbox"), dict) else {}
    return ReductoCitation(
        page=int(bbox.get("page", 0) or 0),
        left=float(bbox.get("left", 0.0) or 0.0),
        top=float(bbox.get("top", 0.0) or 0.0),
        width=float(bbox.get("width", 0.0) or 0.0),
        height=float(bbox.get("height", 0.0) or 0.0),
        content=str(raw.get("content", "")),
        confidence=str(raw.get("confidence", "medium")),
    )


def chunk_metadata(chunk: dict[str, Any]) -> dict[str, str]:
    metadata: dict[str, str] = {}
    blocks = chunk.get("blocks", [])
    if blocks and isinstance(blocks[0], dict):
        block = blocks[0]
        bbox = block.get("bbox", {})
        if isinstance(bbox, dict) and bbox.get("page") is not None:
            metadata["page"] = str(bbox["page"])
        if block.get("type") is not None:
            metadata["block_type"] = str(block["type"])
    return metadata
