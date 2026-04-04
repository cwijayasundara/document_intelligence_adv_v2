"""Data analytics agent using DeepAgents with gpt-5.3-codex.

Converts natural language questions to SQL, executes them,
and suggests chart configurations for the frontend.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from deepagents import create_deep_agent
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.data_agent.executor import SQLExecutionError, execute_query
from src.data_agent.schema import get_schema_description

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a data analytics agent for a Private Equity Document Intelligence platform.

Your job:
1. Understand the user's natural language question about the system's data
2. Generate a PostgreSQL SELECT query to answer it
3. Suggest a chart type and configuration for visualizing the results

## Rules
- ONLY generate SELECT queries — no INSERT, UPDATE, DELETE, DROP, etc.
- Always include meaningful column aliases for readability
- Use appropriate aggregations (COUNT, AVG, SUM, etc.)
- For time-series data, use DATE_TRUNC for grouping
- The audit_logs.details column is JSONB — use ->> operator to extract fields
- Return the SQL query, a chart configuration, and a brief explanation

## Chart Types Available
- bar: For categorical comparisons (e.g. documents per status)
- line: For time-series trends (e.g. activity over days)
- pie: For proportional breakdowns (e.g. category distribution)
- table: For detailed listings (e.g. recent queries, document details)

## Common Queries
- Document counts by status: SELECT status, COUNT(*) as count FROM documents GROUP BY status
- Documents by category: SELECT dc.name, COUNT(*) FROM documents d JOIN document_categories dc ON d.document_category_id = dc.id GROUP BY dc.name
- Activity timeline: SELECT DATE_TRUNC('day', created_at) as day, COUNT(*) FROM audit_logs GROUP BY day ORDER BY day
- Extraction confidence: SELECT confidence, COUNT(*) FROM extracted_values GROUP BY confidence
- Recent RAG queries: SELECT details->>'query' as query, details->>'answer' as answer, created_at FROM audit_logs WHERE event_type = 'rag.query' ORDER BY created_at DESC
"""


class ChartConfig(BaseModel):
    """Chart configuration for the frontend."""

    chart_type: str = Field(description="bar, line, pie, or table")
    title: str = Field(description="Chart title")
    x_key: str = Field(default="", description="Column name for X axis")
    y_key: str = Field(default="", description="Column name for Y axis")
    name_key: str = Field(default="", description="Column for pie chart labels")
    value_key: str = Field(default="", description="Column for pie chart values")


class AnalyticsResult(BaseModel):
    """Response from the data agent."""

    sql: str = Field(description="The SQL query that was executed")
    explanation: str = Field(description="Brief explanation of the results")
    chart: ChartConfig = Field(description="Chart configuration")


class DataAgent:
    """Analytics agent that converts NL questions to SQL + charts."""

    def __init__(self) -> None:
        self._agent = create_deep_agent(
            model="openai:gpt-5.3-codex",
            tools=[],
            system_prompt=_SYSTEM_PROMPT,
            response_format=AnalyticsResult,
        )

    async def query(
        self,
        question: str,
        session: AsyncSession,
    ) -> dict[str, Any]:
        """Process a natural language analytics question.

        Args:
            question: The user's question.
            session: Database session for schema introspection and query execution.

        Returns:
            Dict with sql, data (columns + rows), chart config, and explanation.
        """
        schema = await get_schema_description(session)

        prompt = (
            f"## Database Schema\n{schema}\n\n"
            f"## User Question\n{question}\n\n"
            f"Generate a SQL query, chart configuration, and brief explanation."
        )

        result = await self._agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

        analytics = self._parse_result(result)

        # Execute the SQL
        try:
            data = await execute_query(session, analytics.sql)
        except SQLExecutionError as exc:
            return {
                "sql": analytics.sql,
                "error": str(exc),
                "data": {"columns": [], "rows": []},
                "chart": analytics.chart.model_dump(),
                "explanation": analytics.explanation,
            }

        return {
            "sql": analytics.sql,
            "data": data,
            "chart": analytics.chart.model_dump(),
            "explanation": analytics.explanation,
        }

    def _parse_result(self, result: dict[str, Any]) -> AnalyticsResult:
        """Parse LLM response into AnalyticsResult."""
        structured = result.get("structured_response")
        if structured is not None and isinstance(structured, AnalyticsResult):
            return structured

        # Fallback: try to extract from messages
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            content = getattr(last, "content", "")
            if isinstance(content, list):
                content = " ".join(
                    b.get("text", "") if isinstance(b, dict) else str(b)
                    for b in content
                )
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    return AnalyticsResult(**parsed)
                except (json.JSONDecodeError, TypeError):
                    pass

        # Final fallback
        return AnalyticsResult(
            sql="SELECT 'No query generated' as message",
            explanation="Could not generate a query for this question.",
            chart=ChartConfig(chart_type="table", title="Error"),
        )
