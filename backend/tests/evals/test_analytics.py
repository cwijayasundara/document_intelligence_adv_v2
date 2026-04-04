"""Analytics data agent behavioral evals.

Tests SQL generation correctness, execution safety,
and conversational question handling.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.evals.conftest import EvalMetrics


@pytest.mark.asyncio
class TestAnalyticsBehavior:
    """Targeted evals for analytics data agent behavior."""

    async def test_generates_valid_executable_sql(
        self,
        ground_truth: dict[str, Any],
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Generated SQL should execute without errors.

        Measures: SQL validity — the query must be syntactically correct.
        Category: analytics, sql_correctness
        """
        from src.config.settings import get_settings
        from src.data_agent.executor import execute_query
        from src.db.connection import get_session_factory, init_engine

        settings = get_settings()
        init_engine(settings.database_url)
        factory = get_session_factory()

        query_data = ground_truth["analytics_queries"][0]
        # Generate SQL via the data agent
        from src.data_agent.agent import DataAgent

        agent = DataAgent()
        async with factory() as session:
            result = await agent.query(query_data["question"], session)

        eval_metrics.record("question", query_data["question"])
        eval_metrics.record("sql", result["sql"])
        eval_metrics.record("has_error", result.get("error") is not None)
        eval_metrics.record("rows", len(result.get("data", {}).get("rows", [])))
        eval_metrics.finish()

        assert result.get("error") is None, f"SQL error: {result['error']}"
        assert len(result["data"]["rows"]) >= query_data["expected_min_rows"]

    async def test_sql_contains_expected_clauses(
        self,
        ground_truth: dict[str, Any],
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Generated SQL should contain expected keywords.

        Measures: SQL structure — SELECT, GROUP BY, correct tables.
        Category: analytics, sql_correctness
        """
        from src.config.settings import get_settings
        from src.db.connection import get_session_factory, init_engine

        settings = get_settings()
        init_engine(settings.database_url)
        factory = get_session_factory()

        from src.data_agent.agent import DataAgent

        query_data = ground_truth["analytics_queries"][0]
        agent = DataAgent()
        async with factory() as session:
            result = await agent.query(query_data["question"], session)

        sql_upper = result["sql"].upper()
        expected = query_data["expected_sql_contains"]
        found = [kw for kw in expected if kw.upper() in sql_upper]
        missing = [kw for kw in expected if kw.upper() not in sql_upper]

        eval_metrics.record("sql", result["sql"])
        eval_metrics.record("expected_keywords", expected)
        eval_metrics.record("found", found)
        eval_metrics.record("missing", missing)
        eval_metrics.finish()

        assert len(missing) == 0, f"SQL missing keywords: {missing}. SQL: {result['sql']}"

    async def test_conversational_question_from_memory(
        self,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: 'What was my previous query?' should be answered from memory.

        Measures: Memory-first routing — conversational questions skip SQL.
        Category: analytics, memory
        """
        from src.agents.memory import get_short_term_memory

        memory = get_short_term_memory()
        session_id = "eval_analytics_memory"
        memory.add_human_message(session_id, "How many documents?")
        memory.add_ai_message(session_id, "SQL: SELECT COUNT(*) FROM documents\nThere are 5 documents.")

        from src.config.settings import get_settings
        from src.db.connection import get_session_factory, init_engine

        settings = get_settings()
        init_engine(settings.database_url)
        factory = get_session_factory()

        from src.data_agent.agent import DataAgent

        agent = DataAgent()
        async with factory() as session:
            result = await agent.query("what was my previous query?", session, session_id=session_id)

        eval_metrics.record("sql", result["sql"])
        eval_metrics.record("explanation", result["explanation"][:100])
        eval_metrics.finish()

        assert "memory" in result["sql"].lower() or "no sql" in result["sql"].lower(), (
            f"Should have answered from memory, but generated SQL: {result['sql']}"
        )

        memory.delete_session(session_id)

    async def test_blocks_dangerous_sql(
        self,
        eval_metrics: EvalMetrics,
    ) -> None:
        """Eval: Executor should block INSERT/DELETE/DROP queries.

        Measures: SQL safety guard — only SELECT allowed.
        Category: analytics, security
        """
        from src.data_agent.executor import SQLExecutionError, execute_query
        from src.config.settings import get_settings
        from src.db.connection import get_session_factory, init_engine

        settings = get_settings()
        init_engine(settings.database_url)
        factory = get_session_factory()

        dangerous_queries = [
            "DELETE FROM documents",
            "DROP TABLE documents",
            "INSERT INTO documents (id) VALUES ('x')",
        ]

        blocked = 0
        async with factory() as session:
            for sql in dangerous_queries:
                try:
                    await execute_query(session, sql)
                except SQLExecutionError:
                    blocked += 1

        eval_metrics.record("dangerous_queries", len(dangerous_queries))
        eval_metrics.record("blocked", blocked)
        eval_metrics.finish()

        assert blocked == len(dangerous_queries), (
            f"Only blocked {blocked}/{len(dangerous_queries)} dangerous queries"
        )
