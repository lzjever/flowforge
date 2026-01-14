#!/usr/bin/env python3
"""
Simplified E2E test runner - HTTP endpoints only.

This script tests HTTP endpoints without WebSocket to avoid timeout issues.
"""

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

sys.path.insert(0, "/home/percy/works/mygithub/routilux")

try:
    import httpx
    import uvicorn

    from routilux import Flow, Routine
    from routilux.api.main import app
    from routilux.monitoring import MonitoringRegistry
    from routilux.monitoring.storage import flow_store, job_store

    print("✓ All dependencies available")
    http_client = httpx.Client(timeout=30.0)
except ImportError as e:
    print(f"✗ Missing dependencies: {e}")
    sys.exit(1)


class ServerManager:
    """Manages Uvicorn server lifecycle."""

    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self.server_url = f"http://{host}:{port}"
        self.server = None
        self.thread = None

    def start(self):
        """Start server in background thread."""
        print(f"Starting server on {self.server_url}...")

        config = uvicorn.Config(app, host=self.host, port=self.port, log_level="error")
        self.server = uvicorn.Server(config)

        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()

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
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=3.0)
        print("✓ Server stopped")


def cleanup():
    """Cleanup resources."""
    print("\nCleaning up...")
    flow_store.clear()
    job_store.clear()
    MonitoringRegistry.disable()
    print("✓ Cleanup complete")


def test_http_endpoints():
    """Test HTTP endpoints without WebSocket."""
    print("\n" + "=" * 60)
    print("Testing HTTP Endpoints")
    print("=" * 60)

    server = ServerManager()
    try:
        server.start()

        # Test 1: Health check
        print("\n[Test 1] Health Check")
        response = http_client.get(f"{server.server_url}/api/health")
        assert response.status_code == 200
        print(f"✓ Health check: {response.json()}")

        print("\n[Test 1] Enabling monitoring...")
        MonitoringRegistry.enable()
        print("✓ Monitoring enabled")

        # Test 2: Create flow
        print("\n[Test 2] Create Flow")

        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.slot = self.define_slot("input", handler=lambda **kwargs: {"result": "ok"})

        print("  Creating flow and routine...")
        flow = Flow("test_flow")
        routine = TestRoutine()
        flow.add_routine(routine, "r1")
        flow_store.add(flow)
        print("  Flow added to store")

        print("  Creating flow via API...")
        response = http_client.post(
            f"{server.server_url}/api/flows", json={"flow_id": "http_flow"}, timeout=10.0
        )
        assert response.status_code == 201
        print("✓ Flow created via API")

        # Test 3: Start job
        print("\n[Test 3] Start Job")
        response = http_client.post(
            f"{server.server_url}/api/jobs",
            json={"flow_id": "http_flow", "entry_routine_id": "r1"},
        )
        assert response.status_code == 201
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"✓ Job started: {job_id}")

        # Wait for execution
        time.sleep(1.0)

        # Test 4: Get job metrics
        print("\n[Test 4] Get Job Metrics")
        response = http_client.get(f"{server.server_url}/api/jobs/{job_id}/metrics")
        assert response.status_code == 200
        metrics = response.json()
        print(f"✓ Metrics: total_events={metrics.get('total_events', 0)}")

        # Test 5: Get execution trace
        print("\n[Test 5] Get Execution Trace")
        response = http_client.get(f"{server.server_url}/api/jobs/{job_id}/trace")
        assert response.status_code == 200
        trace = response.json()
        print(f"✓ Trace: {len(trace)} events")

        # Test 6: Create breakpoint
        print("\n[Test 6] Create Breakpoint")
        response = http_client.post(
            f"{server.server_url}/api/jobs/{job_id}/breakpoints",
            json={"type": "slot", "routine_id": "r1", "slot_name": "input"},
        )
        assert response.status_code == 201
        breakpoint = response.json()
        print(f"✓ Breakpoint created: {breakpoint['breakpoint_id']}")

        # Test 7: List breakpoints
        print("\n[Test 7] List Breakpoints")
        response = http_client.get(f"{server.server_url}/api/jobs/{job_id}/breakpoints")
        assert response.status_code == 200
        breakpoints = response.json()
        print(f"✓ Breakpoints: {breakpoints['total']} total")

        # Test 8: Get flow
        print("\n[Test 8] Get Flow")
        response = http_client.get(f"{server.server_url}/api/flows/http_flow")
        assert response.status_code == 200
        flow_data = response.json()
        print(f"✓ Flow retrieved: {flow_data['flow_id']}")

        # Test 9: List flows
        print("\n[Test 9] List Flows")
        response = http_client.get(f"{server.server_url}/api/flows")
        assert response.status_code == 200
        flows_data = response.json()
        print(f"✓ Flows listed: {flows_data['total']} total")

        print("\n" + "=" * 60)
        print("✅ All HTTP endpoint tests passed!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1
    finally:
        server.stop()
        cleanup()


if __name__ == "__main__":
    sys.exit(test_http_endpoints())
