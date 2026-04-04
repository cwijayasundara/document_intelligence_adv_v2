"""Audit event dataclass — lightweight payload for the audit queue."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    """Immutable audit event payload.

    Attributes:
        event_type: What happened (e.g. document.uploaded, document.parsed).
        entity_type: Category of entity (document, bulk_job, rag).
        entity_id: UUID string of the primary entity.
        document_id: UUID string of the related document (if any).
        file_name: Original file name (if applicable).
        details: Arbitrary JSON-serializable metadata.
        error: Error message if the event represents a failure.
    """

    event_type: str
    entity_type: str = "document"
    entity_id: str | None = None
    document_id: str | None = None
    file_name: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
