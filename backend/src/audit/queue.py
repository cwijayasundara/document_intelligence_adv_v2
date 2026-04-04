"""Background audit queue — fire-and-forget event logging.

Runs a dedicated background thread with its own asyncio event loop
and DB session. Main request threads enqueue events without blocking.
"""

from __future__ import annotations

import asyncio
import logging
import queue
import threading
import uuid
from typing import Any

from src.audit.event import AuditEvent

logger = logging.getLogger(__name__)

_QUEUE_MAX_SIZE = 1000
_SENTINEL = None  # poison pill for shutdown

# SSE subscribers: set of asyncio.Queue that receive broadcast events
_sse_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
_sse_lock = threading.Lock()


def subscribe_sse() -> asyncio.Queue[dict[str, Any]]:
    """Subscribe to real-time audit events via SSE."""
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
    with _sse_lock:
        _sse_subscribers.add(q)
    return q


def unsubscribe_sse(q: asyncio.Queue[dict[str, Any]]) -> None:
    """Unsubscribe from SSE events."""
    with _sse_lock:
        _sse_subscribers.discard(q)


def _broadcast_to_sse(event: AuditEvent) -> None:
    """Push event to all SSE subscribers (non-blocking)."""
    payload = {
        "event_type": event.event_type,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "document_id": event.document_id,
        "file_name": event.file_name,
    }
    with _sse_lock:
        for q in _sse_subscribers:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass  # drop if subscriber is slow


class AuditQueue:
    """Non-blocking audit event queue with background DB writer."""

    def __init__(self) -> None:
        self._queue: queue.Queue[AuditEvent | None] = queue.Queue(
            maxsize=_QUEUE_MAX_SIZE
        )
        self._thread: threading.Thread | None = None
        self._shutdown = threading.Event()
        self._db_url: str = ""
        self._pool_size: int = 2
        self._max_overflow: int = 1

    def start(
        self,
        database_url: str,
        pool_size: int = 2,
        max_overflow: int = 1,
    ) -> None:
        """Start the background writer thread."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._db_url = database_url
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._shutdown.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="audit-writer",
            daemon=True,
        )
        self._thread.start()
        logger.info("Audit queue started (max_size=%d)", _QUEUE_MAX_SIZE)

    def stop(self) -> None:
        """Signal shutdown and wait for pending events to flush."""
        if self._thread is None or not self._thread.is_alive():
            return
        self._shutdown.set()
        self._queue.put(_SENTINEL)
        self._thread.join(timeout=10)
        logger.info("Audit queue stopped")

    def emit(self, event: AuditEvent) -> None:
        """Enqueue an audit event (non-blocking, fire-and-forget)."""
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            logger.warning("Audit queue full, dropping event: %s", event.event_type)

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    # ---- background thread ----

    def _run_loop(self) -> None:
        """Background thread: run asyncio loop processing events."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._process_events(loop))
        except Exception:
            logger.exception("Audit queue loop crashed")
        finally:
            loop.close()

    async def _process_events(self, loop: asyncio.AbstractEventLoop) -> None:
        """Process events until shutdown sentinel received."""
        engine = None
        session_factory = None

        try:
            from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
            from sqlalchemy.orm import sessionmaker

            engine = create_async_engine(
                self._db_url,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
            )
            session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
            logger.info("Audit queue DB connection initialized")
        except Exception:
            logger.exception("Audit queue failed to init DB — events will be logged only")

        while not self._shutdown.is_set() or not self._queue.empty():
            try:
                event = await loop.run_in_executor(
                    None, lambda: self._queue.get(timeout=1.0)
                )
            except queue.Empty:
                continue

            if event is _SENTINEL:
                break

            await self._write_event(event, session_factory)
            _broadcast_to_sse(event)

        # Flush remaining
        while not self._queue.empty():
            event = self._queue.get_nowait()
            if event is not _SENTINEL and event is not None:
                await self._write_event(event, session_factory)

        if engine:
            await engine.dispose()
            logger.info("Audit queue DB connection closed")

    async def _write_event(
        self, event: AuditEvent, session_factory: Any
    ) -> None:
        """Write a single event to the audit_logs table."""
        try:
            if session_factory is None:
                logger.info(
                    "[audit] %s | %s | entity=%s | doc=%s",
                    event.event_type, event.entity_type,
                    event.entity_id, event.document_id,
                )
                return

            async with session_factory() as session:
                from src.db.models.audit import AuditLog

                log = AuditLog(
                    id=uuid.uuid4(),
                    event_type=event.event_type,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                    document_id=event.document_id,
                    file_name=event.file_name,
                    details=event.details if event.details else None,
                    error=event.error,
                )
                session.add(log)
                await session.commit()
        except Exception:
            logger.warning(
                "Failed to write audit event: %s (%s)",
                event.event_type,
                event.entity_id,
                exc_info=True,
            )


# ---- global singleton ----

_audit_queue: AuditQueue | None = None


def get_audit_queue() -> AuditQueue:
    """Get or create the global audit queue singleton."""
    global _audit_queue
    if _audit_queue is None:
        _audit_queue = AuditQueue()
    return _audit_queue


def emit_audit_event(
    event_type: str,
    entity_type: str = "document",
    entity_id: str | None = None,
    document_id: str | None = None,
    file_name: str | None = None,
    details: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """Fire-and-forget: enqueue an audit event.

    Safe to call from any thread. Returns immediately.
    """
    q = get_audit_queue()
    q.emit(
        AuditEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            document_id=document_id,
            file_name=file_name,
            details=details or {},
            error=error,
        )
    )
