"""Audit module — non-blocking event logging with SSE broadcast."""

from src.audit.event import AuditEvent
from src.audit.queue import emit_audit_event, get_audit_queue, subscribe_sse, unsubscribe_sse

__all__ = [
    "AuditEvent",
    "emit_audit_event",
    "get_audit_queue",
    "subscribe_sse",
    "unsubscribe_sse",
]
