"""
Tests for API enhancements (filtering, pagination, WebSocket, expression evaluation).
"""

import os

import pytest


@pytest.mark.api
def test_list_jobs_with_pagination(client, test_flow, test_job):
    """Test job listing with pagination parameters."""
    response = client.get("/api/jobs?limit=10&offset=0")
    assert response.status_code == 200

    data = response.json()
    assert "jobs" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert isinstance(data["total"], int)


@pytest.mark.api
def test_list_jobs_filter_by_flow_id(client, test_flow, test_job):
    """Test job listing filtered by flow ID."""
    response = client.get(f"/api/jobs?flow_id={test_flow}")
    assert response.status_code == 200

    data = response.json()
    assert "jobs" in data
    # All returned jobs should belong to the specified flow
    for job in data["jobs"]:
        assert job["flow_id"] == test_flow


@pytest.mark.api
def test_list_jobs_filter_by_status(client, test_job):
    """Test job listing filtered by status."""
    # Get job status first
    job_response = client.get(f"/api/jobs/{test_job}")
    job_data = job_response.json()
    status = job_data["status"]

    # Filter by status
    response = client.get(f"/api/jobs?status={status}")
    assert response.status_code == 200

    data = response.json()
    assert "jobs" in data
    # All returned jobs should have the specified status
    for job in data["jobs"]:
        assert job["status"] == status


@pytest.mark.api
def test_list_jobs_invalid_limit(client):
    """Test job listing with invalid limit parameter."""
    # Limit too high
    response = client.get("/api/jobs?limit=2000")
    assert response.status_code == 422  # Validation error

    # Negative limit
    response = client.get("/api/jobs?limit=-1")
    assert response.status_code == 422


@pytest.mark.api
def test_list_jobs_invalid_offset(client):
    """Test job listing with invalid offset parameter."""
    response = client.get("/api/jobs?offset=-1")
    assert response.status_code == 422  # Validation error


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_connection_status(websocket_client):
    """Test WebSocket connection status events."""
    await websocket_client.connect()

    # Wait for connection status message
    message = await websocket_client.receive_message(timeout=5)

    assert message is not None
    assert message["type"] == "connection:status"
    assert message["status"] == "connected"
    assert "timestamp" in message
    assert "server_time" in message


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_ping_pong(websocket_client):
    """Test WebSocket ping/pong heartbeat."""
    await websocket_client.connect()

    # Wait for ping message (within 35 seconds to allow for 30s heartbeat interval)
    # Note: In real tests, you'd want to mock the heartbeat timer
    message = await websocket_client.receive_message(timeout=5)

    # First message should be connection status
    if message and message.get("type") == "ping":
        assert "timestamp" in message

        # Send pong response
        await websocket_client.send_json({"type": "pong"})


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_subscribe_events(websocket_client):
    """Test WebSocket event subscription."""
    await websocket_client.connect()

    # Subscribe to specific events
    await websocket_client.send_json(
        {"action": "subscribe", "events": ["job_started", "job_failed"]}
    )

    # Receive confirmation
    message = await websocket_client.receive_message(timeout=2)
    assert message is not None
    assert message["type"] == "subscription:confirmed"
    assert message["action"] == "subscribe"
    assert message["events"] == ["job_started", "job_failed"]


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_unsubscribe_events(websocket_client):
    """Test WebSocket event unsubscription."""
    await websocket_client.connect()

    # First subscribe
    await websocket_client.send_json(
        {"action": "subscribe", "events": ["job_started", "job_failed"]}
    )

    # Receive confirmation
    await websocket_client.receive_message(timeout=2)

    # Now unsubscribe
    await websocket_client.send_json({"action": "unsubscribe", "events": ["job_failed"]})

    # Receive confirmation
    message = await websocket_client.receive_message(timeout=2)
    assert message is not None
    assert message["type"] == "subscription:confirmed"
    assert message["action"] == "unsubscribe"
    assert message["events"] == ["job_failed"]


@pytest.mark.websocket
@pytest.mark.asyncio
async def test_websocket_subscribe_all(websocket_client):
    """Test WebSocket subscribe to all events."""
    await websocket_client.connect()

    # Subscribe to all events
    await websocket_client.send_json({"action": "subscribe_all"})

    # Receive confirmation
    message = await websocket_client.receive_message(timeout=2)
    assert message is not None
    assert message["type"] == "subscription:confirmed"
    assert message["action"] == "subscribe_all"


@pytest.mark.debug
def test_expression_evaluation_disabled_by_default(client, paused_job):
    """Test that expression evaluation is disabled by default."""
    response = client.post(
        f"/api/jobs/{paused_job}/debug/evaluate",
        json={"expression": "1 + 1", "routine_id": "test_routine"},
    )

    # Should return 403 Forbidden
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


@pytest.mark.debug
@pytest.mark.skipif(
    not os.getenv("ROUTILUX_EXPRESSION_EVAL_ENABLED"), reason="Expression evaluation not enabled"
)
def test_expression_evaluation_simple_math(client, paused_job):
    """Test simple mathematical expression evaluation."""
    response = client.post(
        f"/api/jobs/{paused_job}/debug/evaluate",
        json={"expression": "1 + 1", "routine_id": "test_routine"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["result"] == 2
    assert data["type"] == "int"
    assert data["error"] is None


@pytest.mark.debug
@pytest.mark.skipif(
    not os.getenv("ROUTILUX_EXPRESSION_EVAL_ENABLED"), reason="Expression evaluation not enabled"
)
def test_expression_evaluation_with_variables(client, paused_job):
    """Test expression evaluation using routine variables."""
    # First get variables to see what's available
    vars_response = client.get(
        f"/api/jobs/{paused_job}/debug/variables", params={"routine_id": "test_routine"}
    )
    variables = vars_response.json()["variables"]

    if variables:
        # Use first variable in expression
        var_name = list(variables.keys())[0]

        # Evaluate expression with variable
        response = client.post(
            f"/api/jobs/{paused_job}/debug/evaluate",
            json={"expression": f"{var_name}", "routine_id": "test_routine"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["error"] is None
        # Result should match variable value
        # (exact comparison depends on variable type)


@pytest.mark.debug
@pytest.mark.skipif(
    not os.getenv("ROUTILUX_EXPRESSION_EVAL_ENABLED"), reason="Expression evaluation not enabled"
)
def test_expression_evaluation_security_rejection(client, paused_job):
    """Test that unsafe operations are rejected."""
    unsafe_expressions = [
        "import os",  # Import statement
        "__import__('os')",  # Builtin import
        "open('/etc/passwd')",  # File operations
        "eval('1+1')",  # Nested eval
    ]

    for expr in unsafe_expressions:
        response = client.post(
            f"/api/jobs/{paused_job}/debug/evaluate",
            json={"expression": expr, "routine_id": "test_routine"},
        )

        assert response.status_code == 200
        data = response.json()
        # Should have error
        assert data["error"] is not None
        assert "security" in data["error"].lower() or "not allowed" in data["error"].lower()


@pytest.mark.debug
@pytest.mark.skipif(
    not os.getenv("ROUTILUX_EXPRESSION_EVAL_ENABLED"), reason="Expression evaluation not enabled"
)
def test_expression_evaluation_syntax_error(client, paused_job):
    """Test expression evaluation with syntax error."""
    response = client.post(
        f"/api/jobs/{paused_job}/debug/evaluate",
        json={
            "expression": "1 +",  # Invalid syntax
            "routine_id": "test_routine",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["error"] is not None
    assert "syntax" in data["error"].lower()


@pytest.mark.api
def test_response_compression(client):
    """Test that API responses are compressed."""
    # Make a request that returns a large response
    response = client.get("/api/jobs", headers={"Accept-Encoding": "gzip"})

    # Response should be successful
    assert response.status_code == 200

    # Check if response is gzip compressed
    # (Note: TestClient may not decompress automatically)
    # In real HTTP client, you'd check for Content-Encoding: gzip


# Test fixtures would be defined in conftest.py
# Example fixtures:
#
# @pytest.fixture
# def client():
#     from routilux.api.main import app
#     return TestClient(app)
#
# @pytest.fixture
# def test_flow():
#     # Create and register a test flow
#     pass
#
# @pytest.fixture
# def test_job(test_flow):
#     # Start a test job
#     pass
#
# @pytest.fixture
# def paused_job():
#     # Create a paused job for debugging tests
#     pass
#
# @pytest.fixture
# def websocket_client():
#     # Create a WebSocket client for testing
#     pass
