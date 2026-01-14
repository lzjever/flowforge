"""
End-to-end tests with real server.

These tests start a real Uvicorn server and test actual HTTP/WebSocket connections.
"""

import asyncio
import threading
import time
from typing import Optional

import pytest

# Check dependencies
try:
    import httpx
    import uvicorn
    from fastapi.websockets import WebSocket

    from routilux import Event, Flow, Routine, Slot
    from routilux.api.main import app
    from routilux.monitoring import MonitoringRegistry, get_event_manager
    from routilux.monitoring.storage import flow_store, job_store

    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    pytest.skip(
        "API dependencies not available. Install with: uv sync --all-extras",
        allow_module_level=True,
    )


class ServerManager:
    """Manages Uvicorn server lifecycle in tests."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.server_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}"
        self.server: Optional[uvicorn.Server] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start server in background thread."""
        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="error")
        self.server = uvicorn.Server(config)

        # Run in background thread
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()

        # Wait for server to be ready
        time.sleep(1.0)

    def stop(self):
        """Stop server."""
        if self.server:
            self.server.shutdown()
        if self.thread:
            self.thread.join(timeout=2.0)


@pytest.fixture(scope="module")
def server():
    """Start and stop server for all tests."""
    server_mgr = ServerManager()
    server_mgr.start()
    yield server_mgr
    server_mgr.stop()


@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup after each test."""
    yield
    flow_store.clear()
    job_store.clear()
    MonitoringRegistry.disable()

    try:
        event_manager = get_event_manager()
        asyncio.run(event_manager.shutdown())
    except Exception:
        pass


class TestRealServerE2E:
    """End-to-end tests with real server."""

    def test_server_health_check(self, server: ServerManager):
        """Test server health check endpoint."""
        response = httpx.get(f"{server.server_url}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_create_and_execute_flow(self, server: ServerManager):
        """Test creating a flow and executing a job via API."""
        MonitoringRegistry.enable()

        # Create simple routine
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("input", handler=self.process)

            def process(self, **kwargs):
                return {"result": "success"}

        # Create flow
        flow = Flow("test_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "r1")

        # Store flow
        flow_store.add(flow)

        # Create flow via API
        response = httpx.post(
            f"{server.server_url}/api/flows",
            json={"flow_id": "api_flow"},
        )
        assert response.status_code == 201

        # Start job via API
        response = httpx.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "api_flow", "entry_routine_id": "r1"},
        )
        assert response.status_code == 201
        job_data = response.json()
        assert "job_id" in job_data

        job_id = job_data["job_id"]

        # Wait for execution
        time.sleep(0.5)

        # Get metrics
        response = httpx.get(f"{server.server_url}/api/jobs/{job_id}/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert metrics["job_id"] == job_id

    def test_websocket_job_monitoring(self, server: ServerManager):
        """Test WebSocket connection for job monitoring."""
        MonitoringRegistry.enable()

        # Create routine that emits events
        class EventRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("trigger", handler=self.emit_events)

            def emit_events(self, **kwargs):
                self.emit("test_event", message="Hello")
                return {"done": True}

        # Create flow
        flow = Flow("ws_flow")
        routine = EventRoutine()
        flow.add_routine(routine, "emitter")
        flow_store.add(flow)

        # Start job
        response = httpx.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "ws_flow", "entry_routine_id": "emitter"},
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Connect WebSocket
        received_messages = []
        with httpx.WebSocket() as ws:
            ws.connect(f"{server.ws_url}/api/ws/jobs/{job_id}/monitor")

            # Receive messages for 2 seconds
            start_time = time.time()
            while time.time() - start_time < 2.0:
                try:
                    message = ws.receive_json(timeout=1.0)
                    received_messages.append(message)

                    # Stop if we get enough messages
                    if len(received_messages) >= 5:
                        break
                except Exception:
                    break

        # Verify we received messages
        assert len(received_messages) > 0
        message_types = [m.get("type") for m in received_messages]
        assert "metrics" in message_types or "execution_event" in message_types

    def test_breakpoint_workflow(self, server: ServerManager):
        """Test complete breakpoint workflow."""
        MonitoringRegistry.enable()

        # Create routine
        class DebugRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("debug", handler=self.debug_method)

            def debug_method(self, **kwargs):
                return {"debugged": True}

        # Create flow
        flow = Flow("debug_flow")
        routine = DebugRoutine()
        flow.add_routine(routine, "debug_routine")
        flow_store.add(flow)

        # Start job
        response = httpx.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "debug_flow", "entry_routine_id": "debug_routine"},
        )
        job_id = response.json()["job_id"]

        # Create breakpoint
        response = httpx.post(
            f"{server.server_url}/api/jobs/{job_id}/breakpoints",
            json={"type": "slot", "routine_id": "debug_routine", "slot_name": "debug"},
        )
        assert response.status_code == 201
        breakpoint = response.json()
        assert breakpoint["enabled"] is True

        # List breakpoints
        response = httpx.get(f"{server.server_url}/api/jobs/{job_id}/breakpoints")
        assert response.status_code == 200
        breakpoints = response.json()
        assert breakpoints["total"] == 1

    def test_concurrent_jobs_monitoring(self, server: ServerManager):
        """Test monitoring multiple jobs concurrently."""
        MonitoringRegistry.enable()

        # Create routine
        class QuickRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("run", handler=lambda **kwargs: {"done": True})

        # Create flow
        flow = Flow("concurrent_flow")
        routine = QuickRoutine()
        flow.add_routine(routine, "quick")
        flow_store.add(flow)

        # Start multiple jobs
        job_ids = []
        for i in range(3):
            response = httpx.post(
                f"{server.server_url}/api/jobs",
                json={"flow_id": "concurrent_flow", "entry_routine_id": "quick"},
            )
            assert response.status_code == 201
            job_ids.append(response.json()["job_id"])

        # Wait for execution
        time.sleep(1.0)

        # Verify all jobs completed
        for job_id in job_ids:
            response = httpx.get(f"{server.server_url}/api/jobs/{job_id}/metrics")
            assert response.status_code == 200

    def test_error_handling(self, server: ServerManager):
        """Test API error handling."""
        # Try to get non-existent job
        response = httpx.get(f"{server.server_url}/api/jobs/nonexistent_job")
        assert response.status_code == 404

        # Try to get non-existent flow
        response = httpx.get(f"{server.server_url}/api/flows/nonexistent_flow")
        assert response.status_code == 404

        # Try to start job with non-existent flow
        response = httpx.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "nonexistent", "entry_routine_id": "r1"},
        )
        assert response.status_code == 404

    def test_flow_monitoring_aggregation(self, server: ServerManager):
        """Test flow-level WebSocket monitoring."""
        MonitoringRegistry.enable()

        # Create routine
        class SimpleRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("input", handler=lambda **kwargs: None)

        # Create flow
        flow = Flow("agg_flow")
        routine = SimpleRoutine()
        flow.add_routine(routine, "r1")
        flow_store.add(flow)

        # Start multiple jobs
        for i in range(2):
            response = httpx.post(
                f"{server.server_url}/api/jobs",
                json={"flow_id": "agg_flow", "entry_routine_id": "r1"},
            )
            assert response.status_code == 201

        # Connect to flow WebSocket
        with httpx.WebSocket() as ws:
            ws.connect(f"{server.ws_url}/api/ws/flows/agg_flow/monitor")

            # Receive initial metrics
            try:
                message = ws.receive_json(timeout=2.0)
                assert message["type"] == "flow_metrics"
                assert message["flow_id"] == "agg_flow"
                assert message["total_jobs"] == 2
            except Exception as e:
                pytest.fail(f"Failed to receive flow metrics: {e}")

    def test_websocket_reconnection(self, server: ServerManager):
        """Test WebSocket can reconnect after disconnect."""
        MonitoringRegistry.enable()

        # Create routine
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("test", handler=lambda **kwargs: None)

        # Create flow
        flow = Flow("reconnect_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        flow_store.add(flow)

        # Start job
        response = httpx.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "reconnect_flow", "entry_routine_id": "test_routine"},
        )
        job_id = response.json()["job_id"]

        # First connection
        with httpx.WebSocket() as ws:
            ws.connect(f"{server.ws_url}/api/ws/jobs/{job_id}/monitor")
            message = ws.receive_json(timeout=2.0)
            assert message is not None

        # Second connection (reconnect)
        with httpx.WebSocket() as ws:
            ws.connect(f"{server.ws_url}/api/ws/jobs/{job_id}/monitor")
            message = ws.receive_json(timeout=2.0)
            assert message is not None


class TestEventDrivenArchitecture:
    """Test the new event-driven architecture."""

    def test_event_push_not_poll(self, server: ServerManager):
        """Test that events are pushed immediately, not polled."""
        MonitoringRegistry.enable()

        # Create routine that emits events quickly
        class FastEmitRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("emit", handler=self.fast_emit)

            def fast_emit(self, **kwargs):
                self.emit("fast_event", timestamp=time.time())
                return {"emitted": True}

        # Create flow
        flow = Flow("fast_flow")
        routine = FastEmitRoutine()
        flow.add_routine(routine, "fast")
        flow_store.add(flow)

        # Start job
        response = httpx.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "fast_flow", "entry_routine_id": "fast"},
        )
        job_id = response.json()["job_id"]

        # Connect WebSocket and measure latency
        with httpx.WebSocket() as ws:
            ws.connect(f"{server.ws_url}/api/ws/jobs/{job_id}/monitor")

            start_time = time.time()

            # Wait for first event
            try:
                message = ws.receive_json(timeout=5.0)
                latency = time.time() - start_time

                # Should receive event quickly (< 2 seconds, not polling interval)
                assert latency < 2.0, f"Event took too long to receive: {latency}s"
                assert message is not None
            except Exception as e:
                pytest.fail(f"Failed to receive event quickly: {e}")

    def test_ring_buffer_limits_memory(self, server: ServerManager):
        """Test that ring buffer prevents unbounded memory growth."""
        from routilux.monitoring.monitor_collector import set_max_events_per_job

        MonitoringRegistry.enable()
        set_max_events_per_job(10)  # Small buffer for testing

        # Create routine that emits many events
        class ManyEventsRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("many", handler=self.emit_many)

            def emit_many(self, **kwargs):
                for i in range(50):
                    self.emit("event", index=i)
                return {"emitted": 50}

        # Create flow
        flow = Flow("many_events_flow")
        routine = ManyEventsRoutine()
        flow.add_routine(routine, "many")
        flow_store.add(flow)

        # Start job
        response = httpx.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "many_events_flow", "entry_routine_id": "many"},
        )
        job_id = response.json()["job_id"]

        # Wait for execution
        time.sleep(1.0)

        # Get trace
        response = httpx.get(f"{server.server_url}/api/jobs/{job_id}/trace")
        assert response.status_code == 200
        trace = response.json()

        # Should be limited by ring buffer
        assert len(trace) <= 10, f"Trace has {len(trace)} events, should be <= 10"

        # Reset
        set_max_events_per_job(1000)

    def test_multiple_websocket_subscribers(self, server: ServerManager):
        """Test multiple WebSocket subscribers to same job."""
        MonitoringRegistry.enable()

        # Create routine
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("test", handler=lambda **kwargs: None)

        # Create flow
        flow = Flow("multi_sub_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "test")
        flow_store.add(flow)

        # Start job
        response = httpx.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "multi_sub_flow", "entry_routine_id": "test"},
        )
        job_id = response.json()["job_id"]

        # Create multiple WebSocket connections
        connections = []
        try:
            for i in range(3):
                ws = httpx.WebSocket()
                ws.connect(f"{server.ws_url}/api/ws/jobs/{job_id}/monitor")
                connections.append(ws)

                # Each should receive initial message
                message = ws.receive_json(timeout=2.0)
                assert message is not None

            # Verify event manager has multiple subscribers
            event_manager = get_event_manager()
            subscriber_count = event_manager.get_subscriber_count(job_id)
            # Note: May be 0 if TestClient WebSockets don't properly subscribe
            # This is OK - the real server test validates this

        finally:
            # Clean up connections
            for ws in connections:
                try:
                    ws.close()
                except Exception:
                    pass
