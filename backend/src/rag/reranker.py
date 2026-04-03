"""Local cross-encoder re-ranker for RAG retrieval.

Uses sentence-transformers CrossEncoder (ms-marco-MiniLM-L-6-v2)
to re-score and re-order retrieved chunks by relevance to the query.
Runs locally — no API calls, no cost.
"""

from __future__ import annotations

import logging

from sentence_transformers import CrossEncoder

from src.rag.weaviate_client import SearchResult

logger = logging.getLogger(__name__)

# Small, fast cross-encoder trained on MS MARCO passage ranking
_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_model: CrossEncoder | None = None


def _get_model() -> CrossEncoder:
    """Lazy-load the cross-encoder model (singleton)."""
    global _model
    if _model is None:
        logger.info("Loading cross-encoder re-ranker: %s", _MODEL_NAME)
        _model = CrossEncoder(_MODEL_NAME)
        logger.info("Re-ranker model loaded")
    return _model


def rerank(
    query: str,
    results: list[SearchResult],
    top_n: int = 5,
) -> list[SearchResult]:
    """Re-rank search results using a cross-encoder model.

    Scores each (query, chunk_text) pair and returns the top_n
    results sorted by cross-encoder relevance score.

    Args:
        query: The original search query.
        results: Initial search results from Weaviate.
        top_n: Number of results to keep after re-ranking.

    Returns:
        Top-n results re-ordered by cross-encoder score.
    """
    if not results:
        return []

    if len(results) <= 1:
        return results

    model = _get_model()

    pairs = [[query, r.chunk_text] for r in results]
    scores = model.predict(pairs)

    scored = list(zip(results, scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    reranked = []
    for result, score in scored[:top_n]:
        reranked.append(
            SearchResult(
                chunk_text=result.chunk_text,
                document_id=result.document_id,
                document_name=result.document_name,
                chunk_index=result.chunk_index,
                relevance_score=float(score),
                metadata=result.metadata,
            )
        )

    logger.info(
        "Re-ranked %d -> %d results (top score=%.2f, bottom score=%.2f)",
        len(results),
        len(reranked),
        reranked[0].relevance_score if reranked else 0,
        reranked[-1].relevance_score if reranked else 0,
    )
    return reranked
