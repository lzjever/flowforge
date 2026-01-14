#!/usr/bin/env python3
"""
Standalone E2E test runner.

This script starts a real server and runs end-to-end tests.
"""

import asyncio
import os
import sys
import threading
import time

# Disable proxies
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""

# Add parent directory to path
sys.path.insert(0, "/home/percy/works/mygithub/routilux")

try:
    import httpx
    import uvicorn
    from fastapi.websockets import WebSocket

    from routilux import Flow, Routine
    from routilux.api.main import app
    from routilux.monitoring import MonitoringRegistry, get_event_manager
    from routilux.monitoring.storage import flow_store, job_store

    print("✓ All dependencies available")

    # Create httpx client without proxy
    http_client = httpx.Client(timeout=30.0)

except ImportError as e:
    print(f"✗ Missing dependencies: {e}")
    print("Install with: uv sync --all-extras")
    sys.exit(1)


class ServerManager:
    """Manages Uvicorn server lifecycle."""

    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.server_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}"
        self.server = None
        self.thread = None

    def start(self):
        """Start server in background thread."""
        print(f"Starting server on {self.server_url}...")
        print(f"  Host: {self.host}")
        print(f"  Port: {self.port}")

        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="info")
        self.server = uvicorn.Server(config)

        # Run in background thread
        print("  Starting server thread...")
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        print("  Server thread started")

        # Wait for server to be ready
        print("  Waiting for server to be ready...")
        for i in range(10):
            time.sleep(0.5)
            try:
                response = http_client.get(f"{self.server_url}/api/health", timeout=2.0)
                if response.status_code == 200:
                    print(f"✓ Server started on {self.server_url}")
                    return
            except Exception:
                print(f"    Attempt {i + 1}/10: Server not ready yet...")
                continue

        print("⚠ Server may not be fully started, but continuing...")

    def stop(self):
        """Stop server."""
        print("Stopping server...")
        if self.server:
            self.server.shutdown()
        if self.thread:
            self.thread.join(timeout=2.0)
        print("✓ Server stopped")


def cleanup():
    """Cleanup resources."""
    print("\nCleaning up...")
    flow_store.clear()
    job_store.clear()
    MonitoringRegistry.disable()

    try:
        event_manager = get_event_manager()
        asyncio.run(event_manager.shutdown())
    except Exception:
        pass
    print("✓ Cleanup complete")


def test_server_health(server):
    """Test 1: Server health check."""
    print("\n[Test 1] Server health check...")

    try:
        print(f"  Connecting to {server.server_url}/api/health...")
        response = http_client.get(f"{server.server_url}/api/health", timeout=10.0)
        print(f"  Response status: {response.status_code}")

        if response.status_code != 200:
            print(f"  Response body: {response.text}")
            return False

        data = response.json()
        print(f"  Response data: {data}")
        assert data["status"] == "healthy"
        print("✓ Server health check passed")
        return True
    except Exception as e:
        print(f"✗ Server health check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_create_and_execute_flow(server):
    """Test 2: Create and execute flow."""
    print("\n[Test 2] Create and execute flow...")

    try:
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
        response = http_client.post(
            f"{server.server_url}/api/flows", json={"flow_id": "api_flow"}, timeout=5.0
        )
        assert response.status_code == 201, f"Failed to create flow: {response.text}"

        # Start job via API
        response = http_client.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "api_flow", "entry_routine_id": "r1"},
            timeout=5.0,
        )
        assert response.status_code == 201, f"Failed to start job: {response.text}"
        job_data = response.json()
        assert "job_id" in job_data

        job_id = job_data["job_id"]
        print(f"  Started job: {job_id}")

        # Wait for execution
        time.sleep(1.0)

        # Get metrics
        response = http_client.get(f"{server.server_url}/api/jobs/{job_id}/metrics", timeout=5.0)
        assert response.status_code == 200, f"Failed to get metrics: {response.text}"
        metrics = response.json()
        assert metrics["job_id"] == job_id

        print("✓ Create and execute flow passed")
        return True
    except Exception as e:
        print(f"✗ Create and execute flow failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_websocket_monitoring(server):
    """Test 3: WebSocket monitoring."""
    print("\n[Test 3] WebSocket monitoring...")

    try:
        MonitoringRegistry.enable()

        # Create routine that emits events
        class EventRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("trigger", handler=self.emit_events)

            def emit_events(self, **kwargs):
                self.emit("test_event", message="Hello from E2E!")
                return {"done": True}

        # Create flow
        flow = Flow("ws_flow")
        routine = EventRoutine()
        flow.add_routine(routine, "emitter")
        flow_store.add(flow)

        # Start job
        response = http_client.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "ws_flow", "entry_routine_id": "emitter"},
            timeout=5.0,
        )
        assert response.status_code == 201, f"Failed to start job: {response.text}"
        job_id = response.json()["job_id"]
        print(f"  Started job: {job_id}")

        # Connect WebSocket
        received_messages = []
        with httpx.WebSocket() as ws:
            ws.connect(f"{server.ws_url}/api/ws/jobs/{job_id}/monitor", timeout=5.0)
            print("  WebSocket connected")

            # Receive messages for 3 seconds
            start_time = time.time()
            while time.time() - start_time < 3.0:
                try:
                    message = ws.receive_json(timeout=2.0)
                    received_messages.append(message)
                    print(f"  Received: {message.get('type', 'unknown')}")

                    if len(received_messages) >= 3:
                        break
                except Exception as e:
                    print(f"  Receive error (may be expected): {e}")
                    break

        # Verify we received messages
        assert len(received_messages) > 0, "No messages received"
        message_types = [m.get("type") for m in received_messages]
        print(f"  Message types: {message_types}")

        print("✓ WebSocket monitoring passed")
        return True
    except Exception as e:
        print(f"✗ WebSocket monitoring failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_breakpoint_workflow(server):
    """Test 4: Breakpoint workflow."""
    print("\n[Test 4] Breakpoint workflow...")

    try:
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
        response = http_client.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "debug_flow", "entry_routine_id": "debug_routine"},
            timeout=5.0,
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]
        print(f"  Started job: {job_id}")

        # Create breakpoint
        response = http_client.post(
            f"{server.server_url}/api/jobs/{job_id}/breakpoints",
            json={"type": "slot", "routine_id": "debug_routine", "slot_name": "debug"},
            timeout=5.0,
        )
        assert response.status_code == 201, f"Failed to create breakpoint: {response.text}"
        breakpoint = response.json()
        assert breakpoint["enabled"] is True
        print(f"  Created breakpoint: {breakpoint['breakpoint_id']}")

        # List breakpoints
        response = http_client.get(
            f"{server.server_url}/api/jobs/{job_id}/breakpoints", timeout=5.0
        )
        assert response.status_code == 200
        breakpoints = response.json()
        assert breakpoints["total"] == 1
        print(f"  Breakpoints listed: {breakpoints['total']}")

        print("✓ Breakpoint workflow passed")
        return True
    except Exception as e:
        print(f"✗ Breakpoint workflow failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ring_buffer(server):
    """Test 5: Ring buffer memory limiting."""
    print("\n[Test 5] Ring buffer memory limiting...")

    try:
        from routilux.monitoring.monitor_collector import set_max_events_per_job

        MonitoringRegistry.enable()
        set_max_events_per_job(10)  # Small buffer

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
        response = http_client.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "many_events_flow", "entry_routine_id": "many"},
            timeout=5.0,
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]
        print(f"  Started job: {job_id}")

        # Wait for execution
        time.sleep(1.0)

        # Get trace
        response = http_client.get(f"{server.server_url}/api/jobs/{job_id}/trace", timeout=5.0)
        assert response.status_code == 200
        trace = response.json()
        print(f"  Trace length: {len(trace)} (max 10 due to ring buffer)")

        # Should be limited by ring buffer
        assert len(trace) <= 10, f"Trace has {len(trace)} events, should be <= 10"

        # Reset
        set_max_events_per_job(1000)

        print("✓ Ring buffer test passed")
        return True
    except Exception as e:
        print(f"✗ Ring buffer test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_event_driven_architecture(server):
    """Test 6: Event-driven architecture (push vs poll)."""
    print("\n[Test 6] Event-driven architecture...")

    try:
        MonitoringRegistry.enable()

        # Create routine that emits quickly
        class FastRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("fast", handler=self.fast_method)

            def fast_method(self, **kwargs):
                self.emit("fast", timestamp=time.time())
                return {"fast": True}

        # Create flow
        flow = Flow("fast_flow")
        routine = FastRoutine()
        flow.add_routine(routine, "fast")
        flow_store.add(flow)

        # Start job
        response = http_client.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "fast_flow", "entry_routine_id": "fast"},
            timeout=5.0,
        )
        assert response.status_code == 201
        job_id = response.json()["job_id"]

        # Connect WebSocket and measure latency
        with httpx.WebSocket() as ws:
            ws.connect(f"{server.ws_url}/api/ws/jobs/{job_id}/monitor", timeout=5.0)
            print("  WebSocket connected, measuring event push latency...")

            start_time = time.time()

            # Wait for first event
            message = ws.receive_json(timeout=5.0)
            latency = time.time() - start_time

            print(f"  First event received in {latency:.3f}s")

            # Should receive event quickly (< 2 seconds, not polling interval of 1s)
            assert latency < 2.0, f"Event took too long: {latency}s"
            assert message is not None

        print("✓ Event-driven architecture test passed")
        return True
    except Exception as e:
        print(f"✗ Event-driven architecture test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all E2E tests."""
    print("=" * 60)
    print("Routilux E2E Test Suite")
    print("=" * 60)

    server = ServerManager()
    try:
        # Start server
        server.start()

        # Run tests
        results = []
        results.append(("Server Health Check", test_server_health(server)))
        cleanup()

        results.append(("Create and Execute Flow", test_create_and_execute_flow(server)))
        cleanup()

        results.append(("WebSocket Monitoring", test_websocket_monitoring(server)))
        cleanup()

        results.append(("Breakpoint Workflow", test_breakpoint_workflow(server)))
        cleanup()

        results.append(("Ring Buffer", test_ring_buffer(server)))
        cleanup()

        results.append(("Event-Driven Architecture", test_event_driven_architecture(server)))
        cleanup()

        # Print summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {name}")

        print("-" * 60)
        print(f"Results: {passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 All E2E tests passed!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return 1

    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        # Always stop server
        server.stop()
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
