"""Provider adapters for Reducto-first document processing."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.config.settings import ProcessingSettings
from src.graph_nodes.schemas.classification import ClassificationResult
from src.parser.reducto import ReductoClient

logger = logging.getLogger(__name__)

CONFIDENCE_LOW = "low"

class ReductoClassificationProvider:
    """Classify documents with Reducto Classify."""

    def __init__(self, reducto: ReductoClient) -> None:
        self._reducto = reducto

    async def classify(
        self,
        *,
        file_name: str,
        content: str,
        categories: list[dict[str, Any]],
        summary: str | None = None,
        original_path: str | None = None,
    ) -> ClassificationResult:
        if not original_path:
            raise ValueError("Reducto classification requires original_path")
        logger.info(
            "Classifying %s with Reducto Classify API against %d categories",
            file_name,
            len(categories),
        )
        reducto_result = await self._reducto.classify(original_path, categories)
        category = _match_category(categories, reducto_result.category_name)
        logger.info(
            "Reducto Classify API returned category '%s' with confidence=%d%%",
            reducto_result.category_name,
            reducto_result.confidence,
        )
        return ClassificationResult(
            category_id=category["id"],
            category_name=category["name"],
            confidence=reducto_result.confidence,
            reasoning=reducto_result.reasoning,
        )


class LangGraphClassificationProvider:
    """Classify documents with the existing LangGraph/LangChain implementation."""

    async def classify(
        self,
        *,
        file_name: str,
        content: str,
        categories: list[dict[str, Any]],
        summary: str | None = None,
        original_path: str | None = None,
    ) -> ClassificationResult:
        from src.graph_nodes.classifier import classify_document

        return await classify_document(
            file_name=file_name,
            content=content,
            categories=categories,
            summary=summary,
        )


class ReductoExtractionProvider:
    """Extract fields with Reducto Extract."""

    def __init__(self, reducto: ReductoClient) -> None:
        self._reducto = reducto

    async def extract_and_judge(
        self,
        *,
        doc_id: uuid.UUID,
        parsed_content: str,
        extraction_fields: list[dict[str, Any]],
        original_path: str | None = None,
        force: bool = False,
    ) -> list[dict[str, Any]]:
        if not original_path:
            raise ValueError("Reducto extraction requires original_path")
        logger.info(
            "Extracting %d fields with Reducto Extract API",
            len(extraction_fields),
        )
        extraction = await self._reducto.extract(original_path, extraction_fields)
        logger.info(
            "Reducto Extract API returned %d fields",
            len(extraction.fields),
        )
        by_name = {field.field_name: field for field in extraction.fields}
        results: list[dict[str, Any]] = []
        for field_def in extraction_fields:
            field = by_name.get(field_def["field_name"])
            value = field.extracted_value if field else ""
            confidence = field.confidence if field else CONFIDENCE_LOW
            is_required = field_def.get("required", False)
            results.append(
                {
                    "field_id": str(field_def["field_id"]),
                    "field_name": field_def["field_name"],
                    "display_name": field_def.get("display_name", ""),
                    "extracted_value": value,
                    "source_text": field.source_text if field else "",
                    "confidence": confidence,
                    "confidence_reasoning": "Reducto citation confidence.",
                    "requires_review": confidence == CONFIDENCE_LOW or (is_required and not value),
                }
            )
        return results


class LangGraphExtractionProvider:
    """Extract fields with the existing LangGraph/LangChain implementation."""

    async def extract_and_judge(
        self,
        *,
        doc_id: uuid.UUID,
        parsed_content: str,
        extraction_fields: list[dict[str, Any]],
        original_path: str | None = None,
        force: bool = False,
    ) -> list[dict[str, Any]]:
        from src.graph_nodes.extractor import extract_fields
        from src.graph_nodes.judge import judge_extraction

        extraction_result = await extract_fields(parsed_content, extraction_fields)
        judge_result = await judge_extraction(
            extraction_result.fields,
            parsed_content,
            field_metadata=extraction_fields,
        )
        eval_map = {e.field_name: e for e in judge_result.evaluations}
        results: list[dict[str, Any]] = []
        for i, field_def in enumerate(extraction_fields):
            extracted = extraction_result.fields[i] if i < len(extraction_result.fields) else None
            evaluation = eval_map.get(field_def["field_name"])
            confidence = evaluation.confidence if evaluation else "medium"
            value = extracted.extracted_value if extracted else ""
            is_required = field_def.get("required", False)
            results.append(
                {
                    "field_id": str(field_def["field_id"]),
                    "field_name": field_def["field_name"],
                    "display_name": field_def.get("display_name", ""),
                    "extracted_value": value,
                    "source_text": extracted.source_text if extracted else "",
                    "confidence": confidence,
                    "confidence_reasoning": evaluation.reasoning if evaluation else "",
                    "requires_review": (
                        confidence == CONFIDENCE_LOW
                        or (confidence == "medium" and not value)
                        or (is_required and not value)
                    ),
                }
            )
        return results


class ReductoChunkProvider:
    """Create RAG chunks with Reducto retrieval chunking."""

    def __init__(self, reducto: ReductoClient) -> None:
        self._reducto = reducto

    async def chunk_from_file(self, original_path: str, *, chunk_size: int) -> list[Any]:
        result = await self._reducto.parse_with_retrieval_chunks(
            original_path,
            chunk_size=chunk_size,
        )
        from src.rag.chunker import Chunk

        return [
            Chunk(text=chunk.text, index=chunk.index, metadata=chunk.metadata)
            for chunk in result.chunks
        ]


class LangChainChunkProvider:
    """Marker provider for the existing LangChain chunker."""


def get_classification_provider(
    settings: ProcessingSettings,
    reducto: ReductoClient,
) -> ReductoClassificationProvider | LangGraphClassificationProvider:
    if settings.classification_provider == "langgraph":
        return LangGraphClassificationProvider()
    return ReductoClassificationProvider(reducto)


def get_extraction_provider(
    settings: ProcessingSettings,
    reducto: ReductoClient,
) -> ReductoExtractionProvider | LangGraphExtractionProvider:
    if settings.extraction_provider == "langgraph":
        return LangGraphExtractionProvider()
    return ReductoExtractionProvider(reducto)


def get_chunk_provider(
    settings: ProcessingSettings,
    reducto: ReductoClient,
) -> ReductoChunkProvider | LangChainChunkProvider:
    if settings.chunking_provider == "langchain":
        return LangChainChunkProvider()
    return ReductoChunkProvider(reducto)


def _match_category(
    categories: list[dict[str, Any]],
    category_name: str,
) -> dict[str, Any]:
    for category in categories:
        if category["name"].casefold() == category_name.casefold():
            return category
    logger.warning("Reducto returned unknown category '%s'; using fallback", category_name)
    fallback = next((c for c in categories if "unclassified" in c["name"].casefold()), None)
    return fallback or categories[0]
