"""Safe SQL executor with read-only guards."""

from __future__ import annotations

import logging
import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)
_MAX_ROWS = 1000
_QUERY_TIMEOUT_MS = 10000


class SQLExecutionError(Exception):
    """Raised when SQL execution fails."""


async def execute_query(
    session: AsyncSession,
    sql: str,
) -> dict:
    """Execute a read-only SQL query with safety guards.

    Returns dict with 'columns' (list[str]) and 'rows' (list[list]).
    """
    if _BLOCKED_KEYWORDS.search(sql):
        raise SQLExecutionError(
            "Query blocked: only SELECT queries are allowed."
        )

    # Auto-add LIMIT if not present
    if "limit" not in sql.lower():
        sql = sql.rstrip("; \n") + f" LIMIT {_MAX_ROWS}"

    logger.info("Executing SQL: %s", sql[:200])

    try:
        result = await session.execute(text(sql))
        columns = list(result.keys())
        rows = [list(row) for row in result.fetchall()]

        # Convert non-serializable types
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                if hasattr(val, "isoformat"):
                    rows[i][j] = val.isoformat()
                elif hasattr(val, "__str__") and not isinstance(val, (str, int, float, bool, type(None))):
                    rows[i][j] = str(val)

        logger.info("Query returned %d rows, %d columns", len(rows), len(columns))
        return {"columns": columns, "rows": rows}
    except Exception as exc:
        logger.error("SQL execution failed: %s", exc)
        raise SQLExecutionError(str(exc)) from exc
