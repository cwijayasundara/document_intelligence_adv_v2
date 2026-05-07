"""Default `target` callback for the Foundry simulators.

The simulators drive your application: they emit adversarial / jailbreak
queries and call `target(messages, ...)` to capture the assistant's reply.
This default routes through the production RAG service.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def default_rag_target(
    messages: dict,
    stream: bool = False,
    session_state: Any = None,
    context: Optional[dict[str, Any]] = None,
) -> dict:
    """Call production RAGService.query and append the assistant turn."""
    from src.config.settings import get_settings
    from src.rag.weaviate_client import WeaviateClient
    from src.services.rag_service import RAGService

    msgs = messages["messages"]
    query = msgs[-1].get("content", "") if msgs else ""

    s = get_settings()
    client = WeaviateClient(url=s.weaviate_url)
    client.connect()
    try:
        result = await RAGService(client).query(
            query=query,
            scope="all",
            search_mode="hybrid",
            top_k=10,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("simulator target failed: %s", exc)
        result = {"answer": ""}
    finally:
        try:
            client.disconnect()
        except Exception:  # noqa: BLE001
            pass

    msgs.append(
        {
            "role": "assistant",
            "content": result.get("answer", ""),
            "context": {"citations": result.get("citations") or None},
        }
    )
    return {
        "messages": msgs,
        "stream": stream,
        "session_state": session_state,
        "context": context,
    }
