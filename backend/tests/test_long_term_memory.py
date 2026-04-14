"""Tests for PostgresLongTermMemory and memory repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.graph_nodes.memory.long_term import PostgresLongTermMemory
from src.db.repositories.memory import (
    ConversationSummaryRepository,
    MemoryEntryRepository,
)
from tests.db_helpers import create_test_session


@pytest.fixture
async def session():
    factory = await create_test_session()
    async with factory() as session:
        yield session


# --- ConversationSummaryRepository tests ---


async def test_upsert_creates_summary(session: AsyncSession) -> None:
    """upsert creates a new conversation summary."""
    repo = ConversationSummaryRepository(session)
    record = await repo.upsert(
        session_id="sess-001",
        agent_type="rag_retriever",
        summary="Test summary",
        key_topics=["topic1"],
        documents_discussed=["doc-1"],
        queries_count=3,
    )
    assert record.session_id == "sess-001"
    assert record.agent_type == "rag_retriever"
    assert record.queries_count == 3


async def test_upsert_updates_existing(session: AsyncSession) -> None:
    """upsert updates an existing summary for the same session_id."""
    repo = ConversationSummaryRepository(session)
    await repo.upsert(
        session_id="sess-002",
        agent_type="classifier",
        summary="First",
        key_topics=[],
        documents_discussed=[],
        queries_count=1,
    )
    updated = await repo.upsert(
        session_id="sess-002",
        agent_type="classifier",
        summary="Updated summary",
        key_topics=["new_topic"],
        documents_discussed=["doc-2"],
        queries_count=5,
    )
    assert updated.summary == "Updated summary"
    assert updated.queries_count == 5


async def test_get_by_session(session: AsyncSession) -> None:
    """get_by_session returns the correct summary or None."""
    repo = ConversationSummaryRepository(session)
    await repo.upsert(
        session_id="sess-003",
        agent_type="extractor",
        summary="A summary",
        key_topics=[],
        documents_discussed=[],
        queries_count=0,
    )
    found = await repo.get_by_session("sess-003")
    assert found is not None
    assert found.summary == "A summary"

    missing = await repo.get_by_session("nonexistent")
    assert missing is None


async def test_upsert_with_user_id_isolation(session: AsyncSession) -> None:
    """upsert scoped by user_id creates separate records per user."""
    repo = ConversationSummaryRepository(session)
    await repo.upsert(
        session_id="sess-shared",
        agent_type="classifier",
        summary="Alice summary",
        key_topics=[],
        documents_discussed=[],
        queries_count=1,
        user_id="alice",
    )
    await repo.upsert(
        session_id="sess-shared",
        agent_type="classifier",
        summary="Bob summary",
        key_topics=[],
        documents_discussed=[],
        queries_count=2,
        user_id="bob",
    )

    alice_record = await repo.get_by_session("sess-shared", user_id="alice")
    bob_record = await repo.get_by_session("sess-shared", user_id="bob")

    assert alice_record is not None
    assert alice_record.summary == "Alice summary"
    assert bob_record is not None
    assert bob_record.summary == "Bob summary"


async def test_get_by_session_user_id_filter(session: AsyncSession) -> None:
    """get_by_session with user_id does not return other users' data."""
    repo = ConversationSummaryRepository(session)
    await repo.upsert(
        session_id="sess-only-alice",
        agent_type="extractor",
        summary="Alice only",
        key_topics=[],
        documents_discussed=[],
        queries_count=0,
        user_id="alice",
    )

    found = await repo.get_by_session("sess-only-alice", user_id="alice")
    assert found is not None

    not_found = await repo.get_by_session("sess-only-alice", user_id="bob")
    assert not_found is None


# --- MemoryEntryRepository tests ---


async def test_put_creates_entry(session: AsyncSession) -> None:
    """put creates a new memory entry."""
    repo = MemoryEntryRepository(session)
    entry = await repo.put("ns1", "key1", {"value": 42})
    assert entry.namespace == "ns1"
    assert entry.key == "key1"
    assert entry.data == {"value": 42}


async def test_put_updates_existing(session: AsyncSession) -> None:
    """put updates an existing entry for same namespace+key."""
    repo = MemoryEntryRepository(session)
    await repo.put("ns2", "key2", {"old": True})
    updated = await repo.put("ns2", "key2", {"new": True})
    assert updated.data == {"new": True}


async def test_get_entry(session: AsyncSession) -> None:
    """get returns the correct entry or None."""
    repo = MemoryEntryRepository(session)
    await repo.put("ns3", "key3", {"x": 1})

    found = await repo.get("ns3", "key3")
    assert found is not None
    assert found.data == {"x": 1}

    missing = await repo.get("ns3", "missing_key")
    assert missing is None


async def test_delete_entry(session: AsyncSession) -> None:
    """delete removes an entry and returns True."""
    repo = MemoryEntryRepository(session)
    await repo.put("ns4", "key4", {"data": "yes"})

    result = await repo.delete("ns4", "key4")
    assert result is True

    missing = await repo.get("ns4", "key4")
    assert missing is None


async def test_delete_nonexistent(session: AsyncSession) -> None:
    """delete returns False for nonexistent entry."""
    repo = MemoryEntryRepository(session)
    result = await repo.delete("ns5", "nope")
    assert result is False


async def test_search_namespace(session: AsyncSession) -> None:
    """search returns all entries in a namespace."""
    repo = MemoryEntryRepository(session)
    await repo.put("searchns", "a", {"order": 1})
    await repo.put("searchns", "b", {"order": 2})
    await repo.put("otherns", "c", {"order": 3})

    results = await repo.search("searchns")
    assert len(results) == 2
    keys = {e.key for e in results}
    assert keys == {"a", "b"}


# --- PostgresLongTermMemory integration tests ---


async def test_ltm_save_and_get_summary(session: AsyncSession) -> None:
    """PostgresLongTermMemory saves and retrieves conversation summaries."""
    ltm = PostgresLongTermMemory(session)

    result = await ltm.save_conversation_summary(
        session_id="ltm-001",
        agent_type="summarizer",
        summary="LTM test summary",
        key_topics=["fees"],
        documents_discussed=["doc-abc"],
        queries_count=2,
    )
    assert result["session_id"] == "ltm-001"
    assert result["summary"] == "LTM test summary"

    fetched = await ltm.get_conversation_summary("ltm-001")
    assert fetched is not None
    assert fetched["queries_count"] == 2


async def test_ltm_get_nonexistent_summary(session: AsyncSession) -> None:
    """get_conversation_summary returns None for missing session."""
    ltm = PostgresLongTermMemory(session)
    result = await ltm.get_conversation_summary("nonexistent")
    assert result is None


async def test_ltm_kv_put_get_delete(session: AsyncSession) -> None:
    """PostgresLongTermMemory KV store: put, get, delete."""
    ltm = PostgresLongTermMemory(session)

    await ltm.put("prefs", "theme", {"mode": "dark"})
    result = await ltm.get("prefs", "theme")
    assert result is not None
    assert result["data"]["mode"] == "dark"

    deleted = await ltm.delete("prefs", "theme")
    assert deleted is True

    gone = await ltm.get("prefs", "theme")
    assert gone is None


async def test_ltm_search(session: AsyncSession) -> None:
    """PostgresLongTermMemory search returns all in namespace."""
    ltm = PostgresLongTermMemory(session)
    await ltm.put("agent_state", "key1", {"v": 1})
    await ltm.put("agent_state", "key2", {"v": 2})

    results = await ltm.search("agent_state")
    assert len(results) == 2


# --- PostgresLongTermMemory user isolation tests ---


async def test_ltm_summary_user_isolation(session: AsyncSession) -> None:
    """Summaries are isolated by user_id."""
    ltm = PostgresLongTermMemory(session)

    await ltm.save_conversation_summary(
        session_id="shared-sess",
        agent_type="summarizer",
        summary="Alice summary",
        user_id="alice",
    )
    await ltm.save_conversation_summary(
        session_id="shared-sess",
        agent_type="summarizer",
        summary="Bob summary",
        user_id="bob",
    )

    alice = await ltm.get_conversation_summary("shared-sess", user_id="alice")
    bob = await ltm.get_conversation_summary("shared-sess", user_id="bob")

    assert alice is not None
    assert alice["summary"] == "Alice summary"
    assert bob is not None
    assert bob["summary"] == "Bob summary"


async def test_ltm_summary_user_not_visible(session: AsyncSession) -> None:
    """One user cannot see another user's summary."""
    ltm = PostgresLongTermMemory(session)

    await ltm.save_conversation_summary(
        session_id="private-sess",
        agent_type="extractor",
        summary="Secret data",
        user_id="alice",
    )

    bob_result = await ltm.get_conversation_summary("private-sess", user_id="bob")
    assert bob_result is None


async def test_ltm_kv_user_isolation(session: AsyncSession) -> None:
    """KV entries are isolated by user_id via namespace scoping."""
    ltm = PostgresLongTermMemory(session)

    await ltm.put("prefs", "theme", {"mode": "dark"}, user_id="alice")
    await ltm.put("prefs", "theme", {"mode": "light"}, user_id="bob")

    alice_pref = await ltm.get("prefs", "theme", user_id="alice")
    bob_pref = await ltm.get("prefs", "theme", user_id="bob")

    assert alice_pref is not None
    assert alice_pref["data"]["mode"] == "dark"
    assert bob_pref is not None
    assert bob_pref["data"]["mode"] == "light"


async def test_ltm_kv_search_user_isolation(session: AsyncSession) -> None:
    """Search only returns entries for the requesting user."""
    ltm = PostgresLongTermMemory(session)

    await ltm.put("docs", "d1", {"title": "Alice doc"}, user_id="alice")
    await ltm.put("docs", "d2", {"title": "Bob doc"}, user_id="bob")

    alice_results = await ltm.search("docs", user_id="alice")
    bob_results = await ltm.search("docs", user_id="bob")

    assert len(alice_results) == 1
    assert alice_results[0]["data"]["title"] == "Alice doc"
    assert len(bob_results) == 1
    assert bob_results[0]["data"]["title"] == "Bob doc"


async def test_ltm_kv_delete_user_isolation(session: AsyncSession) -> None:
    """Deleting one user's entry does not affect another."""
    ltm = PostgresLongTermMemory(session)

    await ltm.put("cache", "item", {"v": 1}, user_id="alice")
    await ltm.put("cache", "item", {"v": 2}, user_id="bob")

    deleted = await ltm.delete("cache", "item", user_id="alice")
    assert deleted is True

    alice_gone = await ltm.get("cache", "item", user_id="alice")
    assert alice_gone is None

    bob_still = await ltm.get("cache", "item", user_id="bob")
    assert bob_still is not None
    assert bob_still["data"]["v"] == 2
