"""Data analytics agent using DeepAgents with gpt-5.3-codex.

Converts natural language questions to SQL, executes them,
and suggests chart configurations for the frontend.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.agents.factory import create_agent
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
- NEVER use bind parameters like :user_id or $1 — always use literal values in queries
- Always include meaningful column aliases for readability
- Use appropriate aggregations (COUNT, AVG, SUM, etc.)
- For time-series data, use DATE_TRUNC for grouping
- The audit_logs.details column is JSONB — use ->> operator to extract fields
- The audit_logs table has NO user_id column — do not filter by user_id
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
        from src.agents.middleware.pii_filter import PIIFilterMiddleware

        self._pii_filter = PIIFilterMiddleware()
        self._agent = create_agent(
            model="openai:gpt-5.3-codex",
            tools=[],
            system_prompt=_SYSTEM_PROMPT,
            response_format=AnalyticsResult,
            name="data_agent",
        )

    async def query(
        self,
        question: str,
        session: AsyncSession,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Process a natural language analytics question.

        Args:
            question: The user's question.
            session: Database session for schema introspection and query execution.
            session_id: Optional session ID for conversation context.

        Returns:
            Dict with sql, data (columns + rows), chart config, and explanation.
        """
        # Check short-term memory first for conversational questions
        if session_id:
            from src.agents.memory import get_short_term_memory

            memory = get_short_term_memory()
            history = memory.get_conversation_summary(session_id)

            # If this is a meta-question about the conversation itself, answer from memory
            lower_q = question.lower()
            if history and any(kw in lower_q for kw in [
                "previous query", "last query", "my previous", "what did i ask",
                "what was my", "repeat", "show again",
            ]):
                logger.info("Answering from short-term memory (conversational question)")
                memory.add_human_message(session_id, question)
                answer = f"Here is your recent conversation:\n\n{history}"
                memory.add_ai_message(session_id, answer)
                return {
                    "sql": "-- Answered from conversation memory, no SQL needed",
                    "data": {"columns": ["conversation"], "rows": [[history]]},
                    "chart": ChartConfig(chart_type="table", title="Conversation History").model_dump(),
                    "explanation": answer,
                }

        # Filter PII from question before sending to LLM
        filtered = self._pii_filter.filter_content(question)
        question = filtered.redacted_text

        schema = await get_schema_description(session)

        # Load conversation history for follow-up queries
        history_block = ""
        if session_id:
            from src.agents.memory import get_short_term_memory as _get_mem

            _mem = _get_mem()
            history = _mem.get_conversation_summary(session_id)
            if history:
                history_block = f"## Previous conversation\n{history}\n\n"

        prompt = (
            f"## Database Schema\n{schema}\n\n"
            f"{history_block}"
            f"## User Question\n{question}\n\n"
            f"Generate a SQL query, chart configuration, and brief explanation. "
            f"If this is a follow-up, use the conversation context."
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

        # Save to short-term memory
        if session_id:
            from src.agents.memory import get_short_term_memory as _get_stm

            stm = _get_stm()
            stm.add_human_message(session_id, question)
            stm.add_ai_message(session_id, f"SQL: {analytics.sql}\n{analytics.explanation}")

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
