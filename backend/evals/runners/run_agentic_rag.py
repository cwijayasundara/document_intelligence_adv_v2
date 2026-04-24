"""Agentic RAG runner — captures full trajectory for tool-call grading.

Mirrors the production `agentic_rag_query()` logic but retains the messages
so trajectory evaluators can grade the tool-call sequence. Production code
is unchanged.
"""

from __future__ import annotations

from typing import Any

from ._base import Example, run_experiment as _run_experiment


async def _predict(example: Example) -> dict[str, Any]:
    from langchain.agents import create_agent
    from langchain_core.messages import HumanMessage, SystemMessage

    from src.config.settings import get_settings
    from src.graph_nodes.llm import get_llm
    from src.rag.agent import _SYSTEM_PROMPT, _create_tools
    from src.rag.weaviate_client import WeaviateClient

    inputs = example.inputs
    query = inputs.get("query", "")
    doc_id = inputs.get("doc_id")
    history = inputs.get("conversation_history") or ""

    settings = get_settings()
    client = WeaviateClient(url=settings.weaviate_url)
    client.connect()
    try:
        tools = _create_tools(weaviate_client=client, document_id=doc_id)
        llm = get_llm()
        agent = create_agent(llm, tools)

        messages: list[Any] = [SystemMessage(content=_SYSTEM_PROMPT)]
        if history:
            messages.append(SystemMessage(content=f"## Previous conversation\n{history}"))
        messages.append(HumanMessage(content=query))

        result = await agent.ainvoke({"messages": messages})
        final_messages = result.get("messages", [])

        trajectory: list[dict[str, Any]] = []
        for msg in final_messages:
            for tc in getattr(msg, "tool_calls", None) or []:
                trajectory.append(
                    {
                        "type": "tool_call",
                        "name": (tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)),
                        "args": (tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})),
                    }
                )
        last = final_messages[-1] if final_messages else None
        answer = getattr(last, "content", "") if last else ""
        if isinstance(answer, list):
            answer = "\n".join(
                b.get("text") if isinstance(b, dict) else str(b) for b in answer
            )
        # LangChain Message objects aren't JSON-serialisable — the eval framework
        # persists `prediction` into a JSONB column. Serialise to a minimal dict
        # representation so trajectory evaluators still see role/content/tool_calls.
        serialised_messages = []
        for m in final_messages:
            if hasattr(m, "model_dump"):
                try:
                    serialised_messages.append(m.model_dump(exclude_none=True))
                    continue
                except Exception:  # noqa: BLE001
                    pass
            serialised_messages.append({
                "type": getattr(m, "type", type(m).__name__),
                "content": getattr(m, "content", str(m)),
            })
        return {"answer": answer, "trajectory": trajectory, "messages": serialised_messages}
    finally:
        try:
            client.disconnect()
        except Exception:  # noqa: BLE001
            pass


def _evaluators() -> list[tuple[str, Any]]:
    import os

    from evals.evaluators.metric_based import (
        rag_answer_contains,
        rag_citation_count_in_range,
    )
    from evals.evaluators.trajectory import (
        no_unnecessary_calls,
        trajectory_order,
        trajectory_subset,
    )

    evs: list[tuple[str, Any]] = [
        ("trajectory_subset", trajectory_subset),
        ("trajectory_order", trajectory_order),
        ("no_unnecessary_calls", no_unnecessary_calls),
        ("rag_answer_contains", rag_answer_contains),
        ("rag_citation_count_in_range", rag_citation_count_in_range),
    ]
    if os.environ.get("OPENAI_API_KEY"):
        from evals.evaluators.llm_judge import rag_answer_faithfulness
        from evals.evaluators.rubric import make_rubric_evaluator
        from evals.evaluators.trajectory import tool_input_quality

        evs.extend([
            ("rag_answer_faithfulness", rag_answer_faithfulness),
            ("tool_input_quality", tool_input_quality),
            (
                "rubric_agent_trajectory",
                make_rubric_evaluator("agent_trajectory", context_keys=["query"]),
            ),
        ])
    return evs


async def run_experiment_wrapper(
    subset: int | None = None,
    tags: list[str] | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    return await _run_experiment(
        stage="agentic_rag",
        dataset_file="rag_golden.jsonl",
        predict=_predict,
        evaluators=_evaluators(),
        subset=subset,
        tags=tags,
        model=model,
    )


run_experiment = run_experiment_wrapper  # alias for CLI discovery
