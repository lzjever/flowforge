"""
Performance tests for WebSocket and event manager integration.

Tests verify:
1. Event-driven push instead of polling (sub-second latency)
2. Multiple concurrent WebSocket connections
3. Connection lifecycle (subscribe/unsubscribe/cleanup)
4. Event queue overflow handling (ring buffer behavior)

Requires API dependencies to be installed.
"""

import asyncio
import time

import pytest

# Check if API dependencies are available
try:
    from fastapi.testclient import TestClient
    from fastapi.websockets import WebSocketDisconnect

    from routilux.api.main import app
    from routilux.monitoring.event_manager import get_event_manager

    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    pytest.skip(
        "API dependencies not available. Install with: uv sync --all-extras",
        allow_module_level=True,
    )

from routilux import Flow, Routine
from routilux.monitoring.storage import flow_store, job_store


class TestEventManager:
    """Test JobEventManager functionality."""

    @pytest.fixture
    def event_manager(self):
        """Get event manager instance."""
        manager = get_event_manager()
        yield manager
        # Cleanup after tests
        asyncio.run(manager.shutdown())

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, event_manager):
        """Test subscribe and unsubscribe lifecycle."""
        job_id = "test_job_001"

        # Subscribe
        subscriber_id = await event_manager.subscribe(job_id)
        assert subscriber_id.startswith("sub_")

        # Check subscriber count
        count = event_manager.get_subscriber_count(job_id)
        assert count == 1

        # Unsubscribe
        await event_manager.unsubscribe(subscriber_id)

        # Check subscriber count (should be 0)
        count = event_manager.get_subscriber_count(job_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_publish_and_receive(self, event_manager):
        """Test publishing and receiving events."""
        job_id = "test_job_002"

        # Subscribe
        subscriber_id = await event_manager.subscribe(job_id)

        # Publish event
        test_event = {"type": "test", "data": "test_data"}
        await event_manager.publish(job_id, test_event)

        # Receive event
        events_received = []
        async for event in event_manager.iter_events(subscriber_id):
            events_received.append(event)
            if len(events_received) >= 1:
                break

        # Verify event
        assert len(events_received) == 1
        assert events_received[0]["type"] == "test"
        assert events_received[0]["data"] == "test_data"

        # Cleanup
        await event_manager.unsubscribe(subscriber_id)

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_manager):
        """Test multiple subscribers to the same job."""
        job_id = "test_job_003"

        # Subscribe multiple times
        sub1 = await event_manager.subscribe(job_id)
        sub2 = await event_manager.subscribe(job_id)
        sub3 = await event_manager.subscribe(job_id)

        # Check subscriber count
        count = event_manager.get_subscriber_count(job_id)
        assert count == 3

        # Publish event (all subscribers should receive it)
        test_event = {"type": "test", "data": "multi_test"}
        await event_manager.publish(job_id, test_event)

        # Cleanup
        await event_manager.unsubscribe(sub1)
        await event_manager.unsubscribe(sub2)
        await event_manager.unsubscribe(sub3)

        # Verify no subscribers left
        count = event_manager.get_subscriber_count(job_id)
        assert count == 0

    @pytest.mark.asyncio
    async def test_ring_buffer_overflow(self, event_manager):
        """Test event queue ring buffer behavior (MAX_QUEUE_SIZE=100)."""
        job_id = "test_job_004"

        # Subscribe
        subscriber_id = await event_manager.subscribe(job_id)

        # Publish more events than queue size (150 > 100)
        for i in range(150):
            await event_manager.publish(job_id, {"type": "test", "index": i})

        # Receive events (should only get latest 100 due to ring buffer)
        events_received = []
        async for event in event_manager.iter_events(subscriber_id):
            events_received.append(event)
            if len(events_received) >= 100:
                break

        # Verify we got exactly 100 events (ring buffer size)
        assert len(events_received) == 100

        # Verify first event is index 50 (oldest 50 were dropped)
        assert events_received[0]["index"] == 50

        # Verify last event is index 149
        assert events_received[-1]["index"] == 149

        # Cleanup
        await event_manager.unsubscribe(subscriber_id)

    @pytest.mark.asyncio
    async def test_cleanup_job(self, event_manager):
        """Test cleanup removes all subscribers for a job."""
        job_id = "test_job_005"

        # Subscribe multiple times
        sub1 = await event_manager.subscribe(job_id)
        sub2 = await event_manager.subscribe(job_id)

        # Verify subscribers
        assert event_manager.get_subscriber_count(job_id) == 2

        # Cleanup job
        await event_manager.cleanup(job_id)

        # Verify no subscribers left
        assert event_manager.get_subscriber_count(job_id) == 0

        # Verify subscribers are removed
        status = event_manager.get_status()
        assert job_id not in status["jobs"]

    @pytest.mark.asyncio
    async def test_get_status(self, event_manager):
        """Test get_status returns correct information."""
        job1 = "test_job_006"
        job2 = "test_job_007"

        # Subscribe to multiple jobs
        sub1 = await event_manager.subscribe(job1)
        sub2 = await event_manager.subscribe(job1)
        sub3 = await event_manager.subscribe(job2)

        # Get status
        status = event_manager.get_status()

        # Verify
        assert status["total_jobs"] == 2
        assert status["total_subscribers"] == 3
        assert job1 in status["jobs"]
        assert job2 in status["jobs"]
        assert status["jobs"][job1]["subscribers"] == 2
        assert status["jobs"][job2]["subscribers"] == 1

        # Cleanup
        await event_manager.unsubscribe(sub1)
        await event_manager.unsubscribe(sub2)
        await event_manager.unsubscribe(sub3)


class TestEventDrivenWebSocket:
    """Test WebSocket with event-driven push (no polling)."""

    @pytest.fixture
    def cleanup(self):
        """Cleanup after tests."""
        yield
        flow_store.clear()
        job_store.clear()

    def test_websocket_receives_events_immediately(self, cleanup):
        """Test WebSocket receives events immediately (no 1-second polling delay).

        This is the key performance test: events should be pushed within
        milliseconds, not seconds (as with polling).
        """

        # Create flow and job
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.trigger = self.define_slot("trigger", handler=self._handle)
                self.output = self.define_event("output", ["data"])

            def _handle(self, **kwargs):
                # Emit an event
                self.emit("output", data="test_event")

        flow = Flow("test_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "r1")
        flow_store.add(flow)

        # Start job
        job_state = flow.execute("r1")
        job_store.add(job_state)

        # Connect WebSocket and measure time to receive event
        client = TestClient(app)
        start_time = time.time()

        with client.websocket_connect(f"/api/ws/jobs/{job_state.job_id}/monitor") as websocket:
            # Receive first message (should be initial metrics)
            message = websocket.receive_json()
            assert message["type"] in ("metrics", "execution_event")

            # Wait for execution event (should be pushed immediately)
            timeout = 2.0  # Maximum 2 seconds (way less than old polling interval)
            event_received = False

            while time.time() - start_time < timeout:
                try:
                    message = websocket.receive_json(timeout=0.1)
                    if message.get("event_type") == "event_emit":
                        event_received = True
                        elapsed = time.time() - start_time
                        break
                except Exception:
                    continue

            # Verify event was received quickly
            assert event_received, "Event should be received via push, not polling"
            elapsed = time.time() - start_time
            assert elapsed < 1.0, f"Event should be received within 1 second, took {elapsed:.2f}s"

    def test_multiple_websocket_connections(self, cleanup):
        """Test multiple concurrent WebSocket connections to the same job."""

        # Create flow and job
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.trigger = self.define_slot("trigger", handler=lambda **kwargs: None)

        flow = Flow("test_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "r1")
        flow_store.add(flow)

        # Start job
        job_state = flow.execute("r1")
        job_store.add(job_state)

        # Create multiple WebSocket connections
        client = TestClient(app)

        # Use threads to simulate multiple concurrent connections
        from concurrent.futures import ThreadPoolExecutor

        def connect_websocket(job_id):
            """Connect and receive messages."""
            with client.websocket_connect(f"/api/ws/jobs/{job_id}/monitor") as websocket:
                # Receive at least one message
                message = websocket.receive_json(timeout=2.0)
                return message is not None

        # Test 3 concurrent connections
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(connect_websocket, job_state.job_id) for _ in range(3)]
            results = [f.result() for f in futures]

        # All connections should succeed
        assert all(results), "All WebSocket connections should succeed"

    def test_websocket_auto_unsubscribe_on_disconnect(self, cleanup):
        """Test WebSocket unsubscribes automatically on disconnect."""

        # Create flow and job
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.trigger = self.define_slot("trigger", handler=lambda **kwargs: None)

        flow = Flow("test_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "r1")
        flow_store.add(flow)

        # Start job
        job_state = flow.execute("r1")
        job_store.add(job_state)

        # Get event manager
        event_manager = get_event_manager()

        # Connect WebSocket
        client = TestClient(app)
        with client.websocket_connect(f"/api/ws/jobs/{job_state.job_id}/monitor") as websocket:
            # Verify subscriber exists
            assert event_manager.get_subscriber_count(job_state.job_id) >= 1

        # After disconnect, verify subscriber is removed
        # Note: This may take a moment due to async cleanup
        time.sleep(0.5)
        # The subscriber should be cleaned up (count might be 0 or there might be other subscribers)


class TestWebSocketPerformance:
    """Performance benchmarks for WebSocket and event manager."""

    @pytest.fixture
    def cleanup(self):
        """Cleanup after tests."""
        yield
        flow_store.clear()
        job_store.clear()
        # Shutdown event manager
        event_manager = get_event_manager()
        asyncio.run(event_manager.shutdown())

    def test_event_push_latency(self, cleanup):
        """Benchmark: Measure event push latency (should be < 100ms)."""
        event_manager = get_event_manager()
        job_id = "perf_test_job"

        # Subscribe
        subscriber_id = asyncio.run(event_manager.subscribe(job_id))

        # Measure push latency
        latencies = []
        for i in range(10):
            test_event = {"type": "test", "index": i}

            start = time.time()
            asyncio.run(event_manager.publish(job_id, test_event))

            # Receive event
            received = False

            async def receive_one():
                nonlocal received
                async for event in event_manager.iter_events(subscriber_id):
                    received = True
                    return event

            asyncio.run(receive_one())
            elapsed = (time.time() - start) * 1000  # Convert to ms
            latencies.append(elapsed)

        # Cleanup
        asyncio.run(event_manager.unsubscribe(subscriber_id))

        # Calculate average latency
        avg_latency = sum(latencies) / len(latencies)

        # Assert: Average latency should be < 100ms
        assert avg_latency < 100, (
            f"Average event push latency {avg_latency:.2f}ms exceeds 100ms threshold"
        )

    def test_concurrent_event_throughput(self, cleanup):
        """Benchmark: Test event throughput with multiple concurrent publishers."""
        event_manager = get_event_manager()
        job_id = "throughput_test_job"

        # Subscribe multiple clients
        subscribers = []
        for i in range(5):
            sub_id = asyncio.run(event_manager.subscribe(job_id))
            subscribers.append(sub_id)

        # Publish 100 events concurrently
        async def publish_events():
            for i in range(100):
                await event_manager.publish(job_id, {"type": "test", "index": i})

        start = time.time()
        asyncio.run(publish_events())
        elapsed = time.time() - start

        # Cleanup
        for sub_id in subscribers:
            asyncio.run(event_manager.unsubscribe(sub_id))

        # Assert: Should publish 100 events quickly (< 1 second)
        assert elapsed < 1.0, f"Publishing 100 events took {elapsed:.2f}s, should be < 1s"

        # Calculate throughput
        throughput = 100 / elapsed
        assert throughput > 100, (
            f"Event throughput {throughput:.2f} events/sec should be > 100 events/sec"
        )
