"""In-memory session-based conversation history for agent interactions.

Provides per-session message storage with LRU-like trimming to manage
the context window for multi-turn agent interactions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MessageRole(str, Enum):
    """Role of a conversation message."""

    SYSTEM = "system"
    HUMAN = "human"
    AI = "ai"


@dataclass
class Message:
    """A single conversation message."""

    role: MessageRole
    content: str


class ShortTermMemory:
    """Per-session in-memory conversation history with automatic trimming.

    Messages are automatically trimmed when exceeding max_messages:
    the system message (if any) is preserved along with the most recent
    messages.
    """

    def __init__(self, max_messages: int = 20) -> None:
        self._max_messages = max_messages
        self._sessions: dict[str, list[Message]] = {}

    @property
    def max_messages(self) -> int:
        """Return the maximum number of messages per session."""
        return self._max_messages

    def add_human_message(self, session_id: str, content: str) -> None:
        """Add a human message to a session."""
        self._ensure_session(session_id)
        self._sessions[session_id].append(
            Message(role=MessageRole.HUMAN, content=content)
        )
        self._trim(session_id)

    def add_ai_message(self, session_id: str, content: str) -> None:
        """Add an AI message to a session."""
        self._ensure_session(session_id)
        self._sessions[session_id].append(
            Message(role=MessageRole.AI, content=content)
        )
        self._trim(session_id)

    def add_system_message(self, session_id: str, content: str) -> None:
        """Add a system message to a session."""
        self._ensure_session(session_id)
        self._sessions[session_id].insert(
            0, Message(role=MessageRole.SYSTEM, content=content)
        )
        self._trim(session_id)

    def get_messages(self, session_id: str) -> list[Message]:
        """Get all messages for a session."""
        return list(self._sessions.get(session_id, []))

    def clear_session(self, session_id: str) -> None:
        """Clear all messages for a session but keep the session."""
        if session_id in self._sessions:
            self._sessions[session_id] = []

    def delete_session(self, session_id: str) -> bool:
        """Delete a session entirely. Returns True if existed."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def get_session_count(self) -> int:
        """Return the total number of active sessions."""
        return len(self._sessions)

    def get_conversation_summary(self, session_id: str) -> str:
        """Return formatted text of the last 6 messages (3 exchanges).

        Returns:
            Formatted string with recent messages, or empty string if
            no messages exist.
        """
        messages = self._sessions.get(session_id, [])
        if not messages:
            return ""

        recent = messages[-6:]
        lines = []
        for msg in recent:
            prefix = msg.role.value.upper()
            lines.append(f"{prefix}: {msg.content}")
        return "\n".join(lines)

    def _ensure_session(self, session_id: str) -> None:
        """Ensure a session exists."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []

    def _trim(self, session_id: str) -> None:
        """Trim messages to max_messages, preserving system message."""
        messages = self._sessions[session_id]
        if len(messages) <= self._max_messages:
            return

        system_msgs = [m for m in messages if m.role == MessageRole.SYSTEM]
        non_system = [m for m in messages if m.role != MessageRole.SYSTEM]

        keep_count = self._max_messages - len(system_msgs)
        trimmed = system_msgs + non_system[-keep_count:]
        self._sessions[session_id] = trimmed
