"""RAG query API endpoint for document retrieval and Q&A."""

import logging

from fastapi import APIRouter, Depends

from src.api.dependencies import get_app_settings, get_current_user_id
from src.api.schemas.rag import Citation, RAGQueryRequest, RAGQueryResponse
from src.rag.weaviate_client import WeaviateClient
from src.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    summary="Query documents via RAG",
)
async def rag_query(
    body: RAGQueryRequest,
    user_id: str = Depends(get_current_user_id),  # noqa: ARG001
) -> RAGQueryResponse:
    """Execute a RAG query with scope filtering and hybrid search."""
    settings = get_app_settings()
    weaviate = WeaviateClient(url=settings.weaviate_url)

    try:
        weaviate.connect()
        logger.info(
            "RAG query: scope=%s, scope_id=%s, mode=%s, top_k=%d",
            body.scope,
            body.scope_id,
            body.search_mode,
            body.top_k,
        )

        service = RAGService(weaviate_client=weaviate)
        result = await service.query(
            query=body.query,
            scope=body.scope,
            scope_id=body.scope_id,
            search_mode=body.search_mode,
            top_k=body.top_k,
        )

        citations = [Citation(**c) for c in result["citations"]]
        logger.info(
            "RAG query complete: %d citations, answer=%d chars",
            len(citations),
            len(result["answer"]),
        )

        return RAGQueryResponse(
            answer=result["answer"],
            citations=citations,
            search_mode=result["search_mode"],
            chunks_retrieved=result["chunks_retrieved"],
        )
    finally:
        weaviate.disconnect()
