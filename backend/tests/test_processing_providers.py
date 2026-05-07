"""Tests for processing provider factories."""

from src.config.settings import ProcessingSettings
from src.services.processing_providers import (
    LangChainChunkProvider,
    LangGraphClassificationProvider,
    LangGraphExtractionProvider,
    ReductoChunkProvider,
    ReductoClassificationProvider,
    ReductoExtractionProvider,
    get_chunk_provider,
    get_classification_provider,
    get_extraction_provider,
)


class _Reducto:
    pass


def test_default_providers_are_reducto() -> None:
    settings = ProcessingSettings()
    reducto = _Reducto()

    assert isinstance(get_classification_provider(settings, reducto), ReductoClassificationProvider)
    assert isinstance(get_extraction_provider(settings, reducto), ReductoExtractionProvider)
    assert isinstance(get_chunk_provider(settings, reducto), ReductoChunkProvider)


def test_legacy_providers_remain_selectable() -> None:
    settings = ProcessingSettings(
        classification_provider="langgraph",
        extraction_provider="langgraph",
        chunking_provider="langchain",
    )
    reducto = _Reducto()

    assert isinstance(
        get_classification_provider(settings, reducto),
        LangGraphClassificationProvider,
    )
    assert isinstance(get_extraction_provider(settings, reducto), LangGraphExtractionProvider)
    assert isinstance(get_chunk_provider(settings, reducto), LangChainChunkProvider)
