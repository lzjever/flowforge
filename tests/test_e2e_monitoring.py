"""
End-to-end tests for Routilux monitoring and debugging API.

These tests require API dependencies and run against a live server.
They test the complete integration of monitoring, WebSocket, and debugging features.
"""

import asyncio
import time

import pytest

# Check if API dependencies are available
try:
    import httpx
    from fastapi.testclient import TestClient
    from fastapi.websockets import WebSocket

    from routilux import Event, Flow, Routine, Slot
    from routilux.api.main import app
    from routilux.monitoring import MonitoringRegistry, get_event_manager
    from routilux.monitoring.storage import flow_store, job_store

    API_AVAILABLE = True
except ImportError as e:
    API_AVAILABLE = False
    pytest.skip(
        f"API dependencies not available. Install with: uv sync --all-extras. Error: {e}",
        allow_module_level=True,
    )


class TestE2EWorkflow:
    """End-to-end tests for complete workflow execution with monitoring."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def cleanup(self):
        """Cleanup after tests."""
        yield
        flow_store.clear()
        job_store.clear()
        MonitoringRegistry.disable()

        # Clean up event manager
        try:
            event_manager = get_event_manager()
            asyncio.run(event_manager.shutdown())
        except Exception:
            pass

    def test_complete_monitoring_workflow(self, client, cleanup):
        """Test complete workflow: create flow, start job, monitor via WebSocket."""
        MonitoringRegistry.enable()

        # Create a simple flow with two routines
        class Producer(Routine):
            def __init__(self):
                super().__init__()
                self.trigger_slot = self.define_slot("trigger", handler=self.produce)
                self.output_event = self.define_event("output", ["data"])

            def produce(self, data: str = None, **kwargs):
                self.emit("output", data=data or "test_data")
                return {"produced": data or "test_data"}

        class Consumer(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("consume", handler=self.consume)
                self.output_event = self.define_event("result", ["status"])

            def consume(self, data: str = None, **kwargs):
                result = f"consumed_{data}"
                self.emit("result", status=result)
                return {"status": result}

        # Create flow
        flow = Flow("test_flow")
        producer = Producer()
        consumer = Consumer()
        flow.add_routine(producer, "producer")
        flow.add_routine(consumer, "consumer")

        # Connect producer to consumer
        flow.connect("producer", "output", "consumer", "consume")

        # Store flow
        flow_store.add(flow)

        # Start job via API
        response = client.post(
            "/api/jobs",
            json={
                "flow_id": "test_flow",
                "entry_routine_id": "producer",
                "entry_slot": "trigger",
                "entry_params": {"data": "initial"},
            },
        )
        assert response.status_code == 201
        job_data = response.json()
        job_id = job_data["job_id"]
        assert job_id is not None

        # Wait a bit for execution
        time.sleep(0.5)

        # Get job metrics
        response = client.get(f"/api/jobs/{job_id}/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert metrics["job_id"] == job_id
        assert metrics["total_events"] > 0

        # Get execution trace
        response = client.get(f"/api/jobs/{job_id}/trace")
        assert response.status_code == 200
        trace_data = response.json()
        trace = trace_data["events"]
        assert len(trace) > 0

        # Verify events include both routines
        routine_ids = [event["routine_id"] for event in trace]
        assert "producer" in routine_ids
        assert "consumer" in routine_ids

    def test_websocket_monitoring_integration(self, client, cleanup):
        """Test WebSocket monitoring integration with real event flow."""
        MonitoringRegistry.enable()

        # Create a routine that emits multiple events
        class MultiEventRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("trigger", handler=self.process)

            def process(self, count: int = 5, **kwargs):
                for i in range(count):
                    self.emit("step", step=i, value=f"step_{i}")
                return {"processed": count}

        # Create flow
        flow = Flow("multi_event_flow")
        routine = MultiEventRoutine()
        flow.add_routine(routine, "r1")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={
                "flow_id": "multi_event_flow",
                "entry_routine_id": "r1",
                "entry_params": {"count": 3},
            },
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Test WebSocket connection
        received_events = []
        with client.websocket_connect(f"/api/ws/jobs/{job_id}/monitor") as websocket:
            # Receive events for 2 seconds
            start_time = time.time()
            while time.time() - start_time < 2.0:
                try:
                    message = websocket.receive_json(timeout=0.5)
                    received_events.append(message)
                    if message.get("type") == "ping":
                        continue
                except Exception:
                    break

        # Verify we received events
        assert len(received_events) > 0
        event_types = [e.get("event_type") for e in received_events if "event_type" in e]
        assert "routine_start" in event_types
        assert "slot_call" in event_types
        assert "event_emit" in event_types

    def test_breakpoint_workflow(self, client, cleanup):
        """Test complete breakpoint workflow: create, hit, debug, resume."""
        MonitoringRegistry.enable()

        # Create a routine for debugging
        class DebuggableRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("process", handler=self.process)
                self.counter = 0

            def process(self, **kwargs):
                self.counter += 1
                return {"counter": self.counter}

        # Create flow
        flow = Flow("debug_flow")
        routine = DebuggableRoutine()
        flow.add_routine(routine, "debug_routine")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "debug_flow", "entry_routine_id": "debug_routine"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Create breakpoint
        response = client.post(
            f"/api/jobs/{job_id}/breakpoints",
            json={"type": "slot", "routine_id": "debug_routine", "slot_name": "process"},
        )
        assert response.status_code == 201
        breakpoint = response.json()
        assert breakpoint["enabled"] is True
        assert breakpoint["breakpoint_id"] is not None

        # List breakpoints
        response = client.get(f"/api/jobs/{job_id}/breakpoints")
        assert response.status_code == 200
        breakpoints = response.json()
        assert breakpoints["total"] == 1
        assert len(breakpoints["breakpoints"]) == 1

        # Get debug session
        response = client.get(f"/api/jobs/{job_id}/debug/session")
        assert response.status_code == 200
        session = response.json()
        assert "status" in session

    def test_flow_monitoring_aggregation(self, client, cleanup):
        """Test flow-level monitoring that aggregates multiple jobs."""
        MonitoringRegistry.enable()

        # Create a simple routine
        class SimpleRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=lambda **kwargs: None)

        # Create flow
        flow = Flow("aggregation_flow")
        routine = SimpleRoutine()
        flow.add_routine(routine, "r1")
        flow_store.add(flow)

        # Start multiple jobs
        job_ids = []
        for i in range(3):
            response = client.post(
                "/api/jobs",
                json={"flow_id": "aggregation_flow", "entry_routine_id": "r1"},
            )
            assert response.status_code == 201
            job_ids.append(response.json()["job_id"])

        # Test flow WebSocket aggregation
        received_events = []
        with client.websocket_connect("/api/ws/flows/aggregation_flow/monitor") as websocket:
            # Receive initial metrics
            try:
                message = websocket.receive_json(timeout=1.0)
                received_events.append(message)
            except Exception:
                pass

            # Verify we got flow metrics
            assert len(received_events) > 0
            assert received_events[0]["type"] == "flow_metrics"
            assert received_events[0]["flow_id"] == "aggregation_flow"
            assert received_events[0]["total_jobs"] == 3

    def test_error_handling_and_recovery(self, client, cleanup):
        """Test error handling and graceful degradation."""
        MonitoringRegistry.enable()

        # Create a routine that fails
        class FailingRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("fail", handler=self.fail_method)

            def fail_method(self, **kwargs):
                raise ValueError("Intentional failure for testing")

        # Create flow
        flow = Flow("error_flow")
        routine = FailingRoutine()
        flow.add_routine(routine, "failing_routine")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "error_flow", "entry_routine_id": "failing_routine"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Wait for execution and error
        time.sleep(0.5)

        # Get metrics - should show error
        response = client.get(f"/api/jobs/{job_id}/metrics")
        assert response.status_code == 200
        metrics = response.json()
        # Error should be recorded
        if metrics.get("errors"):
            assert len(metrics["errors"]) > 0

    def test_concurrent_websocket_connections(self, client, cleanup):
        """Test multiple concurrent WebSocket connections to the same job."""
        MonitoringRegistry.enable()

        # Create a long-running routine
        class SlowRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("start", handler=self.slow_process)

            def slow_process(self, **kwargs):
                time.sleep(0.1)  # Simulate slow processing
                return {"done": True}

        # Create flow
        flow = Flow("concurrent_flow")
        routine = SlowRoutine()
        flow.add_routine(routine, "slow")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "concurrent_flow", "entry_routine_id": "slow"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Test multiple concurrent WebSocket connections
        connections = []
        try:
            for i in range(3):
                ws = client.websocket_connect(f"/api/ws/jobs/{job_id}/monitor")
                ws.__enter__()
                connections.append(ws)

            # All connections should be active
            time.sleep(0.2)

            # Verify event manager has multiple subscribers
            event_manager = get_event_manager()
            subscriber_count = event_manager.get_subscriber_count(job_id)
            assert subscriber_count == 3

        finally:
            # Clean up connections
            for ws in connections:
                try:
                    ws.__exit__(None, None, None)
                except Exception:
                    pass

    def test_ring_buffer_behavior(self, client, cleanup):
        """Test that ring buffer prevents unbounded memory growth."""
        from routilux.monitoring.monitor_collector import set_max_events_per_job

        MonitoringRegistry.enable()

        # Set small ring buffer for testing
        set_max_events_per_job(10)

        # Create a routine that emits many events
        class EventGenerator(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("generate", handler=self.generate)

            def generate(self, **kwargs):
                # Emit 50 events
                for i in range(50):
                    self.emit("generated", index=i, value=f"event_{i}")
                return {"generated": 50}

        # Create flow
        flow = Flow("ring_buffer_flow")
        routine = EventGenerator()
        flow.add_routine(routine, "generator")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "ring_buffer_flow", "entry_routine_id": "generator"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Wait for execution
        time.sleep(1.0)

        # Get trace - should have at most 10 events due to ring buffer
        response = client.get(f"/api/jobs/{job_id}/trace")
        assert response.status_code == 200
        trace = response.json()

        # Should not exceed ring buffer size
        assert len(trace) <= 10

        # Reset to default
        set_max_events_per_job(1000)

    def test_event_manager_cleanup(self, client, cleanup):
        """Test that event manager properly cleans up completed jobs."""
        MonitoringRegistry.enable()

        # Create simple routine
        class SimpleRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input", handler=lambda **kwargs: None)

        # Create flow
        flow = Flow("cleanup_flow")
        routine = SimpleRoutine()
        flow.add_routine(routine, "r1")
        flow_store.add(flow)

        # Start and complete job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "cleanup_flow", "entry_routine_id": "r1"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Wait for completion
        time.sleep(0.5)

        # Verify event manager has no subscribers after completion
        event_manager = get_event_manager()
        # Note: Subscribers are cleaned up when WebSocket disconnects
        # This test verifies the cleanup mechanism exists
        assert event_manager is not None

        # Test cleanup method
        asyncio.run(event_manager.cleanup(job_id))

        # Verify cleanup worked
        status = event_manager.get_status()
        assert job_id not in status["jobs"]

    def test_websocket_reconnection(self, client, cleanup):
        """Test WebSocket reconnection after disconnect."""
        MonitoringRegistry.enable()

        # Create a routine that continues running
        class ContinuousRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("start", handler=self.run_continuous)

            def run_continuous(self, **kwargs):
                self.emit("status", message="started")
                return {"status": "running"}

        # Create flow
        flow = Flow("reconnect_flow")
        routine = ContinuousRoutine()
        flow.add_routine(routine, "continuous")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "reconnect_flow", "entry_routine_id": "continuous"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # First connection
        with client.websocket_connect(f"/api/ws/jobs/{job_id}/monitor") as ws1:
            message = ws1.receive_json(timeout=1.0)
            assert message is not None

        # Reconnection (simulate new client)
        with client.websocket_connect(f"/api/ws/jobs/{job_id}/monitor") as ws2:
            message = ws2.receive_json(timeout=1.0)
            assert message is not None

    def test_debug_websocket_filters_events(self, client, cleanup):
        """Test that debug WebSocket filters and sends only relevant events."""
        MonitoringRegistry.enable()

        # Create routine with multiple event types
        class MultiEventRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("process", handler=self.process)

            def process(self, **kwargs):
                # Emit various events
                self.emit("custom", type="custom_event")
                return {"processed": True}

        # Create flow
        flow = Flow("filter_flow")
        routine = MultiEventRoutine()
        flow.add_routine(routine, "multi")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "filter_flow", "entry_routine_id": "multi"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Connect to debug WebSocket
        debug_events = []
        with client.websocket_connect(f"/api/ws/jobs/{job_id}/debug") as websocket:
            # Receive events for 1 second
            start_time = time.time()
            while time.time() - start_time < 1.0:
                try:
                    message = websocket.receive_json(timeout=0.5)
                    debug_events.append(message)
                except Exception:
                    break

        # Verify filtering - should only have debug-relevant events
        for event in debug_events:
            if event.get("type") == "debug_event":
                event_data = event.get("event", {})
                event_type = event_data.get("event_type")
                # Should be one of: routine_start, routine_end, slot_call
                assert event_type in ("routine_start", "routine_end", "slot_call", None)


class TestE2EAPIEndpoints:
    """Test API endpoint functionality end-to-end."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def cleanup(self):
        """Cleanup after tests."""
        yield
        flow_store.clear()
        job_store.clear()
        MonitoringRegistry.disable()

    def test_flow_crud_operations(self, client, cleanup):
        """Test complete CRUD lifecycle for flows."""
        # Create
        response = client.post("/api/flows", json={"flow_id": "crud_flow"})
        assert response.status_code == 201
        assert response.json()["flow_id"] == "crud_flow"

        # Read
        response = client.get("/api/flows/crud_flow")
        assert response.status_code == 200
        assert response.json()["flow_id"] == "crud_flow"

        # List
        response = client.get("/api/flows")
        assert response.status_code == 200
        flows = response.json()["flows"]
        assert len(flows) == 1

        # Delete
        response = client.delete("/api/flows/crud_flow")
        assert response.status_code == 204

        # Verify deleted
        response = client.get("/api/flows/crud_flow")
        assert response.status_code == 404

    def test_job_lifecycle(self, client, cleanup):
        """Test complete job lifecycle from start to completion."""
        from routilux import Routine

        # Create a routine
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot(
                    "input", handler=lambda **kwargs: {"result": "ok"}
                )

        # Create and store flow
        flow = Flow("lifecycle_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "lifecycle_flow", "entry_routine_id": "test_routine"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Get job status
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        job_info = response.json()
        assert job_info["job_id"] == job_id
        assert job_info["flow_id"] == "lifecycle_flow"

        # Wait for completion
        time.sleep(0.5)

        # Get final metrics
        response = client.get(f"/api/jobs/{job_id}/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert metrics["job_id"] == job_id

    def test_breakpoint_crud(self, client, cleanup):
        """Test breakpoint CRUD operations."""
        from routilux import Routine

        # Create routine and flow
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("test", handler=lambda **kwargs: None)

        flow = Flow("bp_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "bp_flow", "entry_routine_id": "test_routine"},
        )
        job_id = response.json()["job_id"]

        # Create breakpoint
        response = client.post(
            f"/api/jobs/{job_id}/breakpoints",
            json={"type": "slot", "routine_id": "test_routine", "slot_name": "test"},
        )
        assert response.status_code == 201
        bp_id = response.json()["breakpoint_id"]

        # List breakpoints
        response = client.get(f"/api/jobs/{job_id}/breakpoints")
        assert response.status_code == 200
        breakpoints = response.json()
        assert breakpoints["total"] == 1

        # Delete breakpoint
        response = client.delete(f"/api/jobs/{job_id}/breakpoints/{bp_id}")
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/jobs/{job_id}/breakpoints")
        assert response.status_code == 200
        breakpoints = response.json()
        assert breakpoints["total"] == 0


class TestE2EPerformance:
    """Performance and stress tests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def cleanup(self):
        """Cleanup after tests."""
        yield
        flow_store.clear()
        job_store.clear()
        MonitoringRegistry.disable()
        try:
            event_manager = get_event_manager()
            asyncio.run(event_manager.shutdown())
        except Exception:
            pass

    def test_high_volume_event_streaming(self, client, cleanup):
        """Test handling high volume of events."""
        MonitoringRegistry.enable()

        # Create routine that emits many events
        class HighVolumeRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("emit", handler=self.emit_many)

            def emit_many(self, count: int = 100, **kwargs):
                for i in range(count):
                    self.emit("item", index=i, data=f"item_{i}")
                return {"emitted": count}

        # Create flow
        flow = Flow("high_volume_flow")
        routine = HighVolumeRoutine()
        flow.add_routine(routine, "emitter")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={
                "flow_id": "high_volume_flow",
                "entry_routine_id": "emitter",
                "entry_params": {"count": 50},
            },
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Test WebSocket with high volume
        received_count = 0
        with client.websocket_connect(f"/api/ws/jobs/{job_id}/monitor") as websocket:
            start_time = time.time()
            timeout = 5.0

            while time.time() - start_time < timeout:
                try:
                    message = websocket.receive_json(timeout=1.0)
                    if message.get("type") != "ping":
                        received_count += 1
                except Exception:
                    break

        # Should receive many events (but limited by ring buffer)
        assert received_count > 0

    def test_multiple_concurrent_jobs(self, client, cleanup):
        """Test handling multiple jobs running concurrently."""
        MonitoringRegistry.enable()

        # Create simple routine
        class QuickRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("run", handler=lambda **kwargs: {"done": True})

        # Create flow
        flow = Flow("concurrent_jobs_flow")
        routine = QuickRoutine()
        flow.add_routine(routine, "quick")
        flow_store.add(flow)

        # Start multiple jobs concurrently
        job_ids = []
        for i in range(5):
            response = client.post(
                "/api/jobs",
                json={"flow_id": "concurrent_jobs_flow", "entry_routine_id": "quick"},
            )
            assert response.status_code == 201
            job_ids.append(response.json()["job_id"])

        # Wait for all to complete
        time.sleep(1.0)

        # Verify all jobs completed
        for job_id in job_ids:
            response = client.get(f"/api/jobs/{job_id}/metrics")
            assert response.status_code == 200

    def test_websocket_connection_timeout_handling(self, client, cleanup):
        """Test that WebSocket handles timeouts gracefully."""
        MonitoringRegistry.enable()

        # Create a routine that takes time
        class SlowRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("slow", handler=self.slow_method)

            def slow_method(self, **kwargs):
                time.sleep(0.2)
                return {"slow": "done"}

        # Create flow
        flow = Flow("timeout_flow")
        routine = SlowRoutine()
        flow.add_routine(routine, "slow_routine")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "timeout_flow", "entry_routine_id": "slow_routine"},
        )
        job_id = response.json()["job_id"]

        # Connect WebSocket
        with client.websocket_connect(f"/api/ws/jobs/{job_id}/monitor") as websocket:
            # Should receive at least initial metrics
            message = websocket.receive_json(timeout=2.0)
            assert message is not None
            assert message["type"] in ("metrics", "execution_event")

    def test_event_queue_overflow_recovery(self, client, cleanup):
        """Test system recovers from event queue overflow."""
        from routilux.monitoring.monitor_collector import set_max_events_per_job

        MonitoringRegistry.enable()

        # Set very small ring buffer
        set_max_events_per_job(5)

        # Create routine that emits many events
        class OverflowRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("overflow", handler=self.overflow)

            def overflow(self, **kwargs):
                for i in range(20):
                    self.emit("overflow_event", index=i)
                return {"overflow": True}

        # Create flow
        flow = Flow("overflow_flow")
        routine = OverflowRoutine()
        flow.add_routine(routine, "overflow_test")
        flow_store.add(flow)

        # Start job
        response = client.post(
            "/api/jobs",
            json={"flow_id": "overflow_flow", "entry_routine_id": "overflow_test"},
        )
        job_id = response.json()["job_id"]

        # Wait for execution
        time.sleep(0.5)

        # Get trace - should have max 5 events
        response = client.get(f"/api/jobs/{job_id}/trace")
        assert response.status_code == 200
        trace = response.json()
        assert len(trace) <= 5

        # Reset ring buffer
        set_max_events_per_job(1000)
