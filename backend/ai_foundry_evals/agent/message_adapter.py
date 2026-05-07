"""Convert LangChain message dumps -> OpenAI message schema + tool_definitions.

Foundry agent evaluators consume conversation arrays in the OpenAI message
schema (`role`, structured `content` parts of types `text`, `tool_call`,
`tool_result`). The agentic_rag runner already serialises LangChain messages
via `model_dump()`; we map those onto the Azure-expected shape here.
"""

from __future__ import annotations

from typing import Any

_TYPE_TO_ROLE = {
    "system": "system",
    "human": "user",
    "user": "user",
    "ai": "assistant",
    "assistant": "assistant",
    "tool": "tool",
}


def to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map LangChain `model_dump()` messages to Azure agent eval format."""
    out: list[dict[str, Any]] = []
    for m in messages:
        mtype = m.get("type") or m.get("role") or "ai"
        role = _TYPE_TO_ROLE.get(mtype, mtype)
        content = m.get("content")

        if role == "tool":
            out.append(
                {
                    "role": "tool",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_call_id": m.get("tool_call_id") or "",
                            "tool_result": {
                                "output": content if isinstance(content, str) else content
                            },
                        }
                    ],
                }
            )
            continue

        parts: list[dict[str, Any]] = []
        if isinstance(content, str) and content:
            parts.append({"type": "text", "text": content})
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    parts.append({"type": "text", "text": block["text"]})
                elif isinstance(block, str):
                    parts.append({"type": "text", "text": block})

        for tc in m.get("tool_calls") or []:
            parts.append(
                {
                    "type": "tool_call",
                    "tool_call_id": tc.get("id") or tc.get("tool_call_id") or "",
                    "name": tc.get("name"),
                    "arguments": tc.get("args") or tc.get("arguments") or {},
                }
            )

        if not parts:
            parts.append({"type": "text", "text": ""})
        out.append({"role": role, "content": parts})
    return out


def langchain_tool_to_openai(tool: Any) -> dict[str, Any]:
    """Convert a LangChain BaseTool into an OpenAI function-tool definition."""
    name = getattr(tool, "name", None) or tool.__class__.__name__
    description = getattr(tool, "description", "") or ""
    schema = getattr(tool, "args_schema", None)
    parameters: dict[str, Any] = {"type": "object", "properties": {}}
    if schema is not None:
        try:
            parameters = schema.model_json_schema()  # pydantic v2
        except AttributeError:
            try:
                parameters = schema.schema()  # pydantic v1
            except Exception:  # noqa: BLE001
                pass
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def langchain_tools_to_definitions() -> list[dict[str, Any]]:
    """Build OpenAI tool_definitions from the production agent's tools.

    Returns [] if the production deps aren't importable (e.g. when running
    this package outside the backend venv). Callers can pass their own list.
    """
    try:
        from src.config.settings import get_settings
        from src.rag.agent import _create_tools
        from src.rag.weaviate_client import WeaviateClient
    except Exception:  # noqa: BLE001
        return []

    s = get_settings()
    client = WeaviateClient(url=s.weaviate_url)
    try:
        client.connect()
        tools = _create_tools(weaviate_client=client, document_id=None)
    finally:
        try:
            client.disconnect()
        except Exception:  # noqa: BLE001
            pass
    return [langchain_tool_to_openai(t) for t in tools]
