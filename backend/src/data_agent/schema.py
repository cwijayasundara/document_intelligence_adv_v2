"""Database schema introspection for the data agent."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# PE domain annotations for key tables
_ANNOTATIONS: dict[str, str] = {
    "documents": "Core document records (LPA, Subscription Agreements, Side Letters). Status tracks pipeline: uploaded→parsed→classified→extracted→summarized→ingested.",
    "document_categories": "Document type categories (e.g. Limited Partnership Agreement, Subscription Agreement, Side Letter, Other).",
    "extracted_values": "Values extracted from documents per field — fund name, fees, terms. Confidence: high/medium/low.",
    "extraction_fields": "Field definitions per category — field_name, display_name, data_type, required.",
    "extraction_schemas": "Versioned extraction schemas linking categories to field sets.",
    "document_summaries": "Generated document summaries with key topics (JSONB array).",
    "audit_logs": "System activity log — every action (upload, parse, classify, extract, summarize, ingest, RAG query) with event_type and JSON details.",
    "bulk_jobs": "Bulk processing jobs — status (pending/processing/completed/failed), document counts.",
    "bulk_job_documents": "Per-document status within a bulk job — processing time, errors.",
}


async def get_schema_description(session: AsyncSession) -> str:
    """Build a comprehensive schema description for the LLM.

    Returns a formatted string with all tables, columns, types,
    and domain annotations.
    """
    result = await session.execute(text("""
        SELECT c.table_name, c.column_name, c.data_type, c.is_nullable,
               tc.constraint_type
        FROM information_schema.columns c
        LEFT JOIN information_schema.key_column_usage kcu
            ON c.table_name = kcu.table_name AND c.column_name = kcu.column_name
        LEFT JOIN information_schema.table_constraints tc
            ON kcu.constraint_name = tc.constraint_name
            AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
        WHERE c.table_schema = 'public'
        ORDER BY c.table_name, c.ordinal_position
    """))

    rows = result.fetchall()
    tables: dict[str, list[str]] = {}
    for table, col, dtype, nullable, constraint in rows:
        if table == "alembic_version":
            continue
        if table not in tables:
            tables[table] = []
        markers = []
        if constraint == "PRIMARY KEY":
            markers.append("PK")
        if constraint == "FOREIGN KEY":
            markers.append("FK")
        if nullable == "NO":
            markers.append("NOT NULL")
        marker_str = f" ({', '.join(markers)})" if markers else ""
        tables[table].append(f"    {col}: {dtype}{marker_str}")

    parts = []
    for table, columns in tables.items():
        annotation = _ANNOTATIONS.get(table, "")
        header = f"TABLE: {table}"
        if annotation:
            header += f"\n  -- {annotation}"
        parts.append(header + "\n" + "\n".join(columns))

    schema_text = "\n\n".join(parts)
    logger.info("Schema introspected: %d tables", len(tables))
    return schema_text
