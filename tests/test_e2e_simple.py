#!/usr/bin/env python3
"""
Simple E2E tests using pytest with proper timeout handling.
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

sys.path.insert(0, "/home/percy/works/mygithub/routilux")

import httpx
import pytest
import uvicorn

from routilux import Flow, Routine
from routilux.api.main import app
from routilux.monitoring import MonitoringRegistry
from routilux.monitoring.storage import flow_store


# Server fixture
@pytest.fixture(scope="module")
def server_url():
    """Start server and return URL."""
    host = "127.0.0.1"
    port = 8767
    url = f"http://{host}:{port}"

    config = uvicorn.Config(app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server ready
    client = httpx.Client(timeout=10.0)
    for _ in range(20):
        time.sleep(0.3)
        try:
            response = client.get(f"{url}/api/health")
            if response.status_code == 200:
                yield url
                break
        except Exception:
            continue
    else:
        pytest.fail("Server failed to start")

    # Cleanup
    server.should_exit = True
    thread.join(timeout=2.0)
    client.close()


# HTTP client fixture
@pytest.fixture(scope="module")
def http_client():
    """Create HTTP client."""
    return httpx.Client(timeout=30.0)


def test_health_check(server_url, http_client):
    """Test 1: Health check."""
    response = http_client.get(f"{server_url}/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_flow(server_url, http_client):
    """Test 2: Create flow via API."""
    MonitoringRegistry.enable()

    class TestRoutine(Routine):
        def __init__(self):
            super().__init__()
            self.slot = self.define_slot("input", handler=lambda **kwargs: {"result": "ok"})

    flow = Flow("simple_test_flow")
    routine = TestRoutine()
    flow.add_routine(routine, "r1")
    flow_store.add(flow)

    response = http_client.post(f"{server_url}/api/flows", json={"flow_id": "api_flow"})
    assert response.status_code == 201
    flow_data = response.json()
    assert flow_data["flow_id"] == "api_flow"


def test_start_job(server_url, http_client):
    """Test 3: Start job execution."""
    MonitoringRegistry.enable()

    class QuickRoutine(Routine):
        def __init__(self):
            super().__init__()
            self.slot = self.define_slot("quick", handler=lambda **kwargs: {"done": True})

    flow = Flow("job_flow")
    routine = QuickRoutine()
    flow.add_routine(routine, "quick")
    flow_store.add(flow)

    response = http_client.post(
        f"{server_url}/api/jobs", json={"flow_id": "job_flow", "entry_routine_id": "quick"}
    )
    assert response.status_code == 201
    job_data = response.json()
    assert "job_id" in job_data
    job_id = job_data["job_id"]

    # Wait for execution
    time.sleep(1.0)

    # Get metrics
    response = http_client.get(f"{server_url}/api/jobs/{job_id}/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["job_id"] == job_id


def test_get_execution_trace(server_url, http_client):
    """Test 4: Get execution trace."""
    MonitoringRegistry.enable()

    class EventRoutine(Routine):
        def __init__(self):
            super().__init__()
            self.slot = self.define_slot("event", handler=self.emit_event)

        def emit_event(self, **kwargs):
            self.emit("test", data="sample")
            return {"emitted": True}

    flow = Flow("trace_flow")
    routine = EventRoutine()
    flow.add_routine(routine, "emitter")
    flow_store.add(flow)

    response = http_client.post(
        f"{server_url}/api/jobs", json={"flow_id": "trace_flow", "entry_routine_id": "emitter"}
    )
    job_id = response.json()["job_id"]

    # Wait for execution
    time.sleep(1.0)

    # Get trace
    response = http_client.get(f"{server_url}/api/jobs/{job_id}/trace")
    assert response.status_code == 200
    trace = response.json()
    assert len(trace) > 0


def test_error_handling(server_url, http_client):
    """Test 5: Error handling for invalid requests."""
    # Test 404 for non-existent job
    response = http_client.get(f"{server_url}/api/jobs/nonexistent_job")
    assert response.status_code == 404

    # Test 404 for non-existent flow
    response = http_client.get(f"{server_url}/api/flows/nonexistent_flow")
    assert response.status_code == 404
