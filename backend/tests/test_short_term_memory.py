"""Tests for short-term memory."""

from src.agents.memory.short_term import MessageRole, ShortTermMemory


class TestShortTermMemory:
    """Tests for ShortTermMemory."""

    def setup_method(self) -> None:
        self.memory = ShortTermMemory(max_messages=20)

    def test_add_human_message(self) -> None:
        self.memory.add_human_message("s1", "Hello")
        msgs = self.memory.get_messages("s1")
        assert len(msgs) == 1
        assert msgs[0].role == MessageRole.HUMAN
        assert msgs[0].content == "Hello"

    def test_add_ai_message(self) -> None:
        self.memory.add_ai_message("s1", "Hi there")
        msgs = self.memory.get_messages("s1")
        assert len(msgs) == 1
        assert msgs[0].role == MessageRole.AI

    def test_add_system_message(self) -> None:
        self.memory.add_system_message("s1", "You are a helpful assistant")
        msgs = self.memory.get_messages("s1")
        assert len(msgs) == 1
        assert msgs[0].role == MessageRole.SYSTEM

    def test_system_message_at_front(self) -> None:
        self.memory.add_human_message("s1", "Hello")
        self.memory.add_system_message("s1", "System prompt")
        msgs = self.memory.get_messages("s1")
        assert msgs[0].role == MessageRole.SYSTEM

    def test_per_session_isolation(self) -> None:
        self.memory.add_human_message("s1", "Session 1")
        self.memory.add_human_message("s2", "Session 2")
        assert len(self.memory.get_messages("s1")) == 1
        assert len(self.memory.get_messages("s2")) == 1
        assert self.memory.get_messages("s1")[0].content == "Session 1"

    def test_get_messages_empty_session(self) -> None:
        assert self.memory.get_messages("nonexistent") == []

    def test_clear_session(self) -> None:
        self.memory.add_human_message("s1", "Hello")
        self.memory.clear_session("s1")
        assert self.memory.get_messages("s1") == []
        assert self.memory.get_session_count() == 1

    def test_delete_session(self) -> None:
        self.memory.add_human_message("s1", "Hello")
        result = self.memory.delete_session("s1")
        assert result is True
        assert self.memory.get_session_count() == 0

    def test_delete_nonexistent_session(self) -> None:
        result = self.memory.delete_session("nonexistent")
        assert result is False

    def test_get_session_count(self) -> None:
        assert self.memory.get_session_count() == 0
        self.memory.add_human_message("s1", "a")
        self.memory.add_human_message("s2", "b")
        assert self.memory.get_session_count() == 2

    def test_trimming_exceeds_max(self) -> None:
        mem = ShortTermMemory(max_messages=5)
        for i in range(10):
            mem.add_human_message("s1", f"msg-{i}")
        msgs = mem.get_messages("s1")
        assert len(msgs) == 5
        assert msgs[-1].content == "msg-9"

    def test_trimming_preserves_system_message(self) -> None:
        mem = ShortTermMemory(max_messages=5)
        mem.add_system_message("s1", "system")
        for i in range(10):
            mem.add_human_message("s1", f"msg-{i}")
        msgs = mem.get_messages("s1")
        assert len(msgs) == 5
        assert msgs[0].role == MessageRole.SYSTEM
        assert msgs[0].content == "system"

    def test_conversation_summary_last_6(self) -> None:
        for i in range(10):
            if i % 2 == 0:
                self.memory.add_human_message("s1", f"Human {i}")
            else:
                self.memory.add_ai_message("s1", f"AI {i}")
        summary = self.memory.get_conversation_summary("s1")
        lines = summary.strip().split("\n")
        assert len(lines) == 6

    def test_conversation_summary_empty(self) -> None:
        summary = self.memory.get_conversation_summary("nonexistent")
        assert summary == ""

    def test_conversation_summary_fewer_than_6(self) -> None:
        self.memory.add_human_message("s1", "Hello")
        self.memory.add_ai_message("s1", "Hi")
        summary = self.memory.get_conversation_summary("s1")
        assert "HUMAN: Hello" in summary
        assert "AI: Hi" in summary

    def test_max_messages_property(self) -> None:
        assert self.memory.max_messages == 20

    def test_default_max_messages(self) -> None:
        mem = ShortTermMemory()
        assert mem.max_messages == 20

    def test_get_messages_returns_copy(self) -> None:
        self.memory.add_human_message("s1", "Hello")
        msgs = self.memory.get_messages("s1")
        msgs.append(None)  # type: ignore
        assert len(self.memory.get_messages("s1")) == 1


class TestShortTermMemoryUserIsolation:
    """Tests that user_id scoping isolates memories between users."""

    def setup_method(self) -> None:
        self.memory = ShortTermMemory(max_messages=20)

    def test_make_key(self) -> None:
        key = ShortTermMemory._make_key("user-1", "sess-1")
        assert key == "user-1:sess-1"

    def test_user_isolation_messages(self) -> None:
        """User A's messages are invisible to User B in the same session."""
        self.memory.add_human_message("s1", "Alice says hi", user_id="alice")
        self.memory.add_human_message("s1", "Bob says hi", user_id="bob")

        alice_msgs = self.memory.get_messages("s1", user_id="alice")
        bob_msgs = self.memory.get_messages("s1", user_id="bob")

        assert len(alice_msgs) == 1
        assert alice_msgs[0].content == "Alice says hi"
        assert len(bob_msgs) == 1
        assert bob_msgs[0].content == "Bob says hi"

    def test_user_isolation_clear(self) -> None:
        """Clearing one user's session does not affect another."""
        self.memory.add_human_message("s1", "Alice", user_id="alice")
        self.memory.add_human_message("s1", "Bob", user_id="bob")

        self.memory.clear_session("s1", user_id="alice")

        assert self.memory.get_messages("s1", user_id="alice") == []
        assert len(self.memory.get_messages("s1", user_id="bob")) == 1

    def test_user_isolation_delete(self) -> None:
        """Deleting one user's session does not affect another."""
        self.memory.add_human_message("s1", "Alice", user_id="alice")
        self.memory.add_human_message("s1", "Bob", user_id="bob")

        result = self.memory.delete_session("s1", user_id="alice")
        assert result is True

        assert self.memory.get_messages("s1", user_id="alice") == []
        assert len(self.memory.get_messages("s1", user_id="bob")) == 1

    def test_user_isolation_summary(self) -> None:
        """Each user gets their own conversation summary."""
        self.memory.add_human_message("s1", "Alice topic", user_id="alice")
        self.memory.add_ai_message("s1", "Alice response", user_id="alice")
        self.memory.add_human_message("s1", "Bob topic", user_id="bob")

        alice_summary = self.memory.get_conversation_summary("s1", user_id="alice")
        bob_summary = self.memory.get_conversation_summary("s1", user_id="bob")

        assert "Alice topic" in alice_summary
        assert "Bob topic" not in alice_summary
        assert "Bob topic" in bob_summary

    def test_default_user_id_is_anonymous(self) -> None:
        """Calls without user_id default to 'anonymous'."""
        self.memory.add_human_message("s1", "anon message")
        msgs = self.memory.get_messages("s1")
        assert len(msgs) == 1

        # Explicit anonymous should see the same data
        msgs_explicit = self.memory.get_messages("s1", user_id="anonymous")
        assert len(msgs_explicit) == 1
        assert msgs_explicit[0].content == "anon message"

    def test_anonymous_isolated_from_named_user(self) -> None:
        """Anonymous user does not see named user's messages."""
        self.memory.add_human_message("s1", "anon msg")
        self.memory.add_human_message("s1", "alice msg", user_id="alice")

        assert len(self.memory.get_messages("s1")) == 1
        assert self.memory.get_messages("s1")[0].content == "anon msg"
        assert len(self.memory.get_messages("s1", user_id="alice")) == 1

    def test_session_count_includes_all_users(self) -> None:
        """Session count reflects all user-scoped sessions."""
        self.memory.add_human_message("s1", "a", user_id="alice")
        self.memory.add_human_message("s1", "b", user_id="bob")
        # Two distinct internal keys: alice:s1 and bob:s1
        assert self.memory.get_session_count() == 2
