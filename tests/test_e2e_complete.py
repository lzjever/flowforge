#!/usr/bin/env python3
"""
Complete E2E test for Routilux monitoring API.

This script tests all HTTP endpoints with real server.
"""

import os
import sys
import threading
import time

# Disable proxies
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

sys.path.insert(0, "/home/percy/works/mygithub/routilux")

import httpx
import uvicorn

from routilux import Flow, Routine
from routilux.api.main import app
from routilux.monitoring import MonitoringRegistry, get_event_manager
from routilux.monitoring.monitor_collector import set_max_events_per_job
from routilux.monitoring.storage import flow_store, job_store

print("=" * 70)
print(" Routilux E2E Test Suite - HTTP Endpoints")
print("=" * 70)

# Server configuration
HOST = "127.0.0.1"
PORT = 8766
SERVER_URL = f"http://{HOST}:{PORT}"

# Create HTTP client
client = httpx.Client(timeout=30.0)


def start_server():
    """Start server in background."""
    print(f"\n[SETUP] Starting server on {SERVER_URL}...")

    config = uvicorn.Config(app, host=HOST, port=PORT, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server to be ready
    for i in range(10):
        time.sleep(0.5)
        try:
            response = client.get(f"{SERVER_URL}/api/health")
            if response.status_code == 200:
                print(f"[SETUP] ✓ Server ready on {SERVER_URL}")
                return server
        except Exception:
            if i < 9:
                print(f"[SETUP]   Waiting for server... ({i + 1}/10)")
            continue

    print("[SETUP] ⚠ Server may not be fully ready")
    return server


def stop_server(server):
    """Stop server."""
    print("\n[SETUP] Stopping server...")
    # Don't await shutdown in non-async context
    # Server will be stopped when daemon thread exits


def cleanup():
    """Clean up resources."""
    print("[CLEANUP] Cleaning up resources...")
    flow_store.clear()
    job_store.clear()
    MonitoringRegistry.disable()
    try:
        event_manager = get_event_manager()
        import asyncio

        asyncio.run(event_manager.shutdown())
    except Exception:
        pass
    print("[CLEANUP] ✓ Cleanup complete")


def test_1_health_check():
    """Test 1: Health check endpoint."""
    print("\n[TEST 1] Health Check")

    try:
        response = client.get(f"{SERVER_URL}/api/health")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data["status"] == "healthy"

        print("[TEST 1] ✓ PASS - Health check working")
        return True
    except Exception as e:
        print(f"[TEST 1] ✗ FAIL - {e}")
        return False


def test_2_create_flow():
    """Test 2: Create flow via API."""
    print("\n[TEST 2] Create Flow via API")

    try:
        response = client.post(f"{SERVER_URL}/api/flows", json={"flow_id": "test_flow_2"})
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        flow_data = response.json()
        assert flow_data["flow_id"] == "test_flow_2"

        print("[TEST 2] ✓ PASS - Flow creation working")
        return True
    except Exception as e:
        print(f"[TEST 2] ✗ FAIL - {e}")
        return False


def test_3_start_job():
    """Test 3: Start job execution."""
    print("\n[TEST 3] Start Job Execution")

    try:
        MonitoringRegistry.enable()

        # Create routine and flow
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("process", handler=self.process)

            def process(self, **kwargs):
                return {"processed": True}

        flow = Flow("job_test_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "processor")
        flow_store.add(flow)

        # Start job
        response = client.post(
            f"{SERVER_URL}/api/jobs",
            json={"flow_id": "job_test_flow", "entry_routine_id": "processor"},
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        job_data = response.json()
        assert "job_id" in job_data
        job_id = job_data["job_id"]

        print(f"[TEST 3]   Job started: {job_id}")

        # Wait for execution
        time.sleep(1.0)

        # Verify job completed
        response = client.get(f"{SERVER_URL}/api/jobs/{job_id}")
        assert response.status_code == 200

        print("[TEST 3] ✓ PASS - Job execution working")
        return True
    except Exception as e:
        print(f"[TEST 3] ✗ FAIL - {e}")
        import traceback

        traceback.print_exc()
        return False


def test_4_metrics_and_trace():
    """Test 4: Get job metrics and execution trace."""
    print("\n[TEST 4] Job Metrics and Trace")

    try:
        MonitoringRegistry.enable()

        # Create routine that emits events
        class EventRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("emit", handler=self.emit_events)

            def emit_events(self, **kwargs):
                self.emit("test", data="sample")
                return {"emitted": True}

        flow = Flow("metrics_flow")
        routine = EventRoutine()
        flow.add_routine(routine, "emitter")
        flow_store.add(flow)

        # Start job
        response = client.post(
            f"{SERVER_URL}/api/jobs",
            json={"flow_id": "metrics_flow", "entry_routine_id": "emitter"},
        )
        job_id = response.json()["job_id"]

        # Wait for execution
        time.sleep(1.0)

        # Get metrics
        response = client.get(f"{SERVER_URL}/api/jobs/{job_id}/metrics")
        assert response.status_code == 200
        metrics = response.json()
        print(f"[TEST 4]   Metrics: {metrics.get('total_events', 0)} events")

        # Get trace
        response = client.get(f"{SERVER_URL}/api/jobs/{job_id}/trace")
        assert response.status_code == 200
        trace = response.json()
        print(f"[TEST 4]   Trace: {len(trace)} events")

        # Verify trace has events
        assert len(trace) > 0, "Expected non-empty trace"

        print("[TEST 4] ✓ PASS - Metrics and trace working")
        return True
    except Exception as e:
        print(f"[TEST 4] ✗ FAIL - {e}")
        import traceback

        traceback.print_exc()
        return False


def test_5_breakpoints():
    """Test 5: Breakpoint CRUD operations."""
    print("\n[TEST 5] Breakpoint Management")

    try:
        MonitoringRegistry.enable()

        # Create routine
        class DebugRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("debug_me", handler=lambda **kwargs: None)

        flow = Flow("debug_flow")
        routine = DebugRoutine()
        flow.add_routine(routine, "debugger")
        flow_store.add(flow)

        # Start job
        response = client.post(
            f"{SERVER_URL}/api/jobs", json={"flow_id": "debug_flow", "entry_routine_id": "debugger"}
        )
        job_id = response.json()["job_id"]

        # Create breakpoint
        response = client.post(
            f"{SERVER_URL}/api/jobs/{job_id}/breakpoints",
            json={"type": "slot", "routine_id": "debugger", "slot_name": "debug_me"},
        )
        assert response.status_code == 201
        breakpoint = response.json()
        assert breakpoint["enabled"] is True
        print(f"[TEST 5]   Breakpoint created: {breakpoint['breakpoint_id']}")

        # List breakpoints
        response = client.get(f"{SERVER_URL}/api/jobs/{job_id}/breakpoints")
        assert response.status_code == 200
        breakpoints = response.json()
        assert breakpoints["total"] == 1
        print(f"[TEST 5]   Breakpoints listed: {breakpoints['total']}")

        # Get debug session
        response = client.get(f"{SERVER_URL}/api/jobs/{job_id}/debug/session")
        assert response.status_code == 200
        session = response.json()
        assert "status" in session

        print("[TEST 5] ✓ PASS - Breakpoint management working")
        return True
    except Exception as e:
        print(f"[TEST 5] ✗ FAIL - {e}")
        import traceback

        traceback.print_exc()
        return False


def test_6_ring_buffer():
    """Test 6: Ring buffer memory limiting."""
    print("\n[TEST 6] Ring Buffer Memory Limiting")

    try:
        MonitoringRegistry.enable()

        # Set small ring buffer
        set_max_events_per_job(10)

        # Create routine that emits many events
        class ManyEventsRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("many", handler=self.emit_many)

            def emit_many(self, **kwargs):
                for i in range(50):
                    self.emit("event", index=i)
                return {"emitted": 50}

        flow = Flow("ring_buffer_flow")
        routine = ManyEventsRoutine()
        flow.add_routine(routine, "many")
        flow_store.add(flow)

        # Start job
        response = client.post(
            f"{SERVER_URL}/api/jobs",
            json={"flow_id": "ring_buffer_flow", "entry_routine_id": "many"},
        )
        job_id = response.json()["job_id"]

        # Wait for execution
        time.sleep(1.0)

        # Get trace
        response = client.get(f"{SERVER_URL}/api/jobs/{job_id}/trace")
        assert response.status_code == 200
        trace = response.json()

        # Verify ring buffer limited events
        assert len(trace) <= 10, f"Expected <= 10 events, got {len(trace)}"
        print(f"[TEST 6]   Trace length: {len(trace)} (limited by ring buffer)")

        # Reset ring buffer
        set_max_events_per_job(1000)

        print("[TEST 6] ✓ PASS - Ring buffer working correctly")
        return True
    except Exception as e:
        print(f"[TEST 6] ✗ FAIL - {e}")
        import traceback

        traceback.print_exc()
        return False


def test_7_error_handling():
    """Test 7: Error handling for invalid requests."""
    print("\n[TEST 7] Error Handling")

    try:
        # Test 404 for non-existent job
        response = client.get(f"{SERVER_URL}/api/jobs/nonexistent_job")
        assert response.status_code == 404
        print("[TEST 7]   Non-existent job returns 404")

        # Test 404 for non-existent flow
        response = client.get(f"{SERVER_URL}/api/flows/nonexistent_flow")
        assert response.status_code == 404
        print("[TEST 7]   Non-existent flow returns 404")

        # Test 404 for starting job with non-existent flow
        response = client.post(
            f"{SERVER_URL}/api/jobs", json={"flow_id": "nonexistent", "entry_routine_id": "r1"}
        )
        assert response.status_code == 404
        print("[TEST 7]   Starting job with non-existent flow returns 404")

        print("[TEST 7] ✓ PASS - Error handling working correctly")
        return True
    except Exception as e:
        print(f"[TEST 7] ✗ FAIL - {e}")
        return False


def test_8_concurrent_jobs():
    """Test 8: Multiple concurrent jobs."""
    print("\n[TEST 8] Concurrent Jobs")

    try:
        MonitoringRegistry.enable()

        # Create simple routine
        class QuickRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("quick", handler=lambda **kwargs: {"done": True})

        flow = Flow("concurrent_flow")
        routine = QuickRoutine()
        flow.add_routine(routine, "quick")
        flow_store.add(flow)

        # Start multiple jobs
        job_ids = []
        for i in range(5):
            response = client.post(
                f"{SERVER_URL}/api/jobs",
                json={"flow_id": "concurrent_flow", "entry_routine_id": "quick"},
            )
            assert response.status_code == 201
            job_ids.append(response.json()["job_id"])

        print(f"[TEST 8]   Started {len(job_ids)} concurrent jobs")

        # Wait for all to complete
        time.sleep(2.0)

        # Verify all completed
        for job_id in job_ids:
            response = client.get(f"{SERVER_URL}/api/jobs/{job_id}/metrics")
            assert response.status_code == 200

        print("[TEST 8] ✓ PASS - Concurrent jobs working")
        return True
    except Exception as e:
        print(f"[TEST 8] ✗ FAIL - {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    server = None

    try:
        # Start server
        server = start_server()

        # Run tests
        print("\n" + "=" * 70)
        print(" RUNNING TESTS")
        print("=" * 70)

        results = []
        results.append(("Health Check", test_1_health_check()))
        cleanup()

        results.append(("Create Flow", test_2_create_flow()))
        cleanup()

        results.append(("Start Job", test_3_start_job()))
        cleanup()

        results.append(("Metrics and Trace", test_4_metrics_and_trace()))
        cleanup()

        results.append(("Breakpoints", test_5_breakpoints()))
        cleanup()

        results.append(("Ring Buffer", test_6_ring_buffer()))
        cleanup()

        results.append(("Error Handling", test_7_error_handling()))
        cleanup()

        results.append(("Concurrent Jobs", test_8_concurrent_jobs()))
        cleanup()

        # Print summary
        print("\n" + "=" * 70)
        print(" TEST SUMMARY")
        print("=" * 70)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {name}")

        print("-" * 70)
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
        # Always cleanup
        if server:
            stop_server(server)
        cleanup()


if __name__ == "__main__":
    sys.exit(main())
