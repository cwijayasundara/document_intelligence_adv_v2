"""Agent memory layer: short-term and long-term storage.

Short-term: in-memory per-session conversation history (singleton).
Long-term: PostgreSQL-backed persistent storage (per DB session).
"""

from src.agents.memory.short_term import ShortTermMemory

# Global singleton — shared across all requests, scoped by session_id
_short_term: ShortTermMemory | None = None


def get_short_term_memory() -> ShortTermMemory:
    """Get or create the global short-term memory singleton."""
    global _short_term
    if _short_term is None:
        _short_term = ShortTermMemory(max_messages=20)
    return _short_term
