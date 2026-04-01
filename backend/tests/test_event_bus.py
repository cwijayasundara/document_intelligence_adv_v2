"""Tests for PipelineEventBus in-memory pub/sub."""

import asyncio

from src.bulk.event_bus import PipelineEventBus


class TestSubscribePublishUnsubscribe:
    """Test basic subscribe, publish, and unsubscribe flow."""

    async def test_subscribe_and_receive_event(self) -> None:
        bus = PipelineEventBus()
        queue = await bus.subscribe("job-1")
        await bus.publish("job-1", {"type": "progress", "step": 1})
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert event == {"type": "progress", "step": 1}

    async def test_publish_to_no_subscribers(self) -> None:
        """Publishing to a job with no subscribers should not raise."""
        bus = PipelineEventBus()
        await bus.publish("nonexistent", {"type": "progress"})

    async def test_unsubscribe_stops_receiving(self) -> None:
        bus = PipelineEventBus()
        queue = await bus.subscribe("job-1")
        await bus.unsubscribe("job-1", queue)
        await bus.publish("job-1", {"type": "progress"})
        assert queue.empty()


class TestMultipleSubscribers:
    """Test publishing to multiple subscribers."""

    async def test_all_subscribers_receive_event(self) -> None:
        bus = PipelineEventBus()
        q1 = await bus.subscribe("job-1")
        q2 = await bus.subscribe("job-1")
        await bus.publish("job-1", {"type": "started"})

        e1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert e1 == {"type": "started"}
        assert e2 == {"type": "started"}

    async def test_different_jobs_isolated(self) -> None:
        bus = PipelineEventBus()
        q_a = await bus.subscribe("job-a")
        q_b = await bus.subscribe("job-b")
        await bus.publish("job-a", {"type": "a-event"})
        await bus.publish("job-b", {"type": "b-event"})

        assert (await asyncio.wait_for(q_a.get(), timeout=1.0)) == {"type": "a-event"}
        assert (await asyncio.wait_for(q_b.get(), timeout=1.0)) == {"type": "b-event"}


class TestUnsubscribeCleanup:
    """Test that unsubscribe properly cleans up."""

    async def test_unsubscribe_removes_queue(self) -> None:
        bus = PipelineEventBus()
        queue = await bus.subscribe("job-1")
        assert bus.subscriber_count == 1
        await bus.unsubscribe("job-1", queue)
        assert bus.subscriber_count == 0

    async def test_unsubscribe_nonexistent_job(self) -> None:
        """Unsubscribing from a job that doesn't exist should not raise."""
        bus = PipelineEventBus()
        queue: asyncio.Queue[dict] = asyncio.Queue()
        await bus.unsubscribe("nonexistent", queue)

    async def test_partial_unsubscribe(self) -> None:
        bus = PipelineEventBus()
        q1 = await bus.subscribe("job-1")
        q2 = await bus.subscribe("job-1")
        await bus.unsubscribe("job-1", q1)
        assert bus.subscriber_count == 1
        # q2 should still receive events
        await bus.publish("job-1", {"type": "still-here"})
        event = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert event == {"type": "still-here"}


class TestSubscriberCount:
    """Test the subscriber_count property."""

    async def test_empty_bus(self) -> None:
        bus = PipelineEventBus()
        assert bus.subscriber_count == 0

    async def test_counts_across_jobs(self) -> None:
        bus = PipelineEventBus()
        await bus.subscribe("job-1")
        await bus.subscribe("job-1")
        await bus.subscribe("job-2")
        assert bus.subscriber_count == 3
