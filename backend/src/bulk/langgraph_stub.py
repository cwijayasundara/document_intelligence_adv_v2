"""Lightweight LangGraph stub for environments without langgraph installed.

Mimics the StateGraph API: add_node, add_edge, set_entry_point,
set_finish_point, compile, and invoke.
"""

from __future__ import annotations

from typing import Any, Callable


class MemorySaver:
    """Stub checkpointer that stores state snapshots in memory."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def save(self, thread_id: str, state: Any) -> None:
        """Save a state checkpoint."""
        self._store[thread_id] = state

    def load(self, thread_id: str) -> Any | None:
        """Load a state checkpoint."""
        return self._store.get(thread_id)


class CompiledGraph:
    """A compiled graph that can be invoked with state."""

    def __init__(
        self,
        nodes: dict[str, Callable],
        edges: list[tuple[str, str]],
        entry: str,
        finish: str,
        checkpointer: MemorySaver | None = None,
    ) -> None:
        self._nodes = nodes
        self._edges = edges
        self._entry = entry
        self._finish = finish
        self._checkpointer = checkpointer

    def _build_order(self) -> list[str]:
        """Build execution order from edges starting at entry."""
        order = [self._entry]
        edge_map = {src: dst for src, dst in self._edges}
        current = self._entry
        while current in edge_map:
            nxt = edge_map[current]
            order.append(nxt)
            current = nxt
        return order

    async def ainvoke(
        self,
        state: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke the graph asynchronously, passing state through nodes."""
        thread_id = ""
        if config and "configurable" in config:
            thread_id = config["configurable"].get("thread_id", "")

        execution_order = self._build_order()
        current_state = dict(state)

        for node_name in execution_order:
            if node_name not in self._nodes:
                continue
            fn = self._nodes[node_name]
            try:
                result = await fn(current_state)
                if isinstance(result, dict):
                    current_state.update(result)
            except Exception as exc:
                current_state["error"] = str(exc)
                break

            if self._checkpointer and thread_id:
                self._checkpointer.save(thread_id, dict(current_state))

        return current_state


class StateGraph:
    """Stub StateGraph mimicking the LangGraph API."""

    def __init__(self, state_schema: type) -> None:
        self._state_schema = state_schema
        self._nodes: dict[str, Callable] = {}
        self._edges: list[tuple[str, str]] = []
        self._entry: str = ""
        self._finish: str = ""

    def add_node(self, name: str, fn: Callable) -> None:
        """Add a named node with its function."""
        self._nodes[name] = fn

    def add_edge(self, source: str, target: str) -> None:
        """Add a directed edge from source to target."""
        self._edges.append((source, target))

    def set_entry_point(self, name: str) -> None:
        """Set the entry node."""
        self._entry = name

    def set_finish_point(self, name: str) -> None:
        """Set the finish node."""
        self._finish = name

    def compile(self, checkpointer: MemorySaver | None = None) -> CompiledGraph:
        """Compile the graph into an executable form."""
        return CompiledGraph(
            nodes=self._nodes,
            edges=self._edges,
            entry=self._entry,
            finish=self._finish,
            checkpointer=checkpointer,
        )
