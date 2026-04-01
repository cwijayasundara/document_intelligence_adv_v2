"""Memory ORM models: conversation summaries and key-value entries."""

import uuid

from sqlalchemy import Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.models.base import Base, TimestampMixin


class ConversationSummary(TimestampMixin, Base):
    """Persistent conversation summaries for long-term memory."""

    __tablename__ = "conversation_summaries"
    __table_args__ = (
        UniqueConstraint("user_id", "session_id", name="uq_conversation_summaries_user_session"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    session_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_topics: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'[]'"))
    documents_discussed: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'")
    )
    queries_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class MemoryEntry(TimestampMixin, Base):
    """Generic key-value store for long-term memory."""

    __tablename__ = "memory_entries"
    __table_args__ = (UniqueConstraint("namespace", "key", name="uq_memory_entries_ns_key"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    namespace: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(500), nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
