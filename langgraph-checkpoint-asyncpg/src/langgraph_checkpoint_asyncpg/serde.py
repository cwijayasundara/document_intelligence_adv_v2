"""Serializer seam for the asyncpg-backed checkpointer.

Re-exports ``JsonPlusSerializer`` from ``langgraph-checkpoint`` (MIT). Kept
as a distinct module so that projects wishing to fully sever ties with the
``langgraph-checkpoint`` package can swap this single file for their own
``SerializerProtocol`` implementation.
"""

from __future__ import annotations

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

__all__ = ["JsonPlusSerializer"]
