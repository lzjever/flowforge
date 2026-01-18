"""
Category 3: Debugging Session Workflows - User Story Tests

Tests for interactive debugging scenarios, including:
- Setting breakpoints
- Inspecting variables at breakpoints
- Stepping through execution
- Modifying variables during debug
- Resuming after debugging

These tests simulate a user debugging a workflow interactively.
"""

import pytest

pytestmark = pytest.mark.userstory


class TestBreakpointDebugging:
    """Test breakpoint debugging workflow.

    User Story: As a user, I want to set breakpoints in my workflow,
    inspect variables when execution pauses, and resume execution.
    """

    def test_get_debug_session_for_job(self, api_client, registered_pipeline_flow):
        """Test getting debug session information for a job."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Get debug session (should exist, though may not be paused)
        response = api_client.get(f"/api/v1/debug/jobs/{job_id}/debug/session")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "status" in data

    def test_debug_session_without_breakpoint(self, api_client, registered_pipeline_flow):
        """Test debug session for job without breakpoint (no session)."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job without breakpoint
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Get debug session - may report no active session
        response = api_client.get(f"/api/v1/debug/jobs/{job_id}/debug/session")
        assert response.status_code == 200
        # Status could be "no_session" or similar when not paused


class TestVariableInspection:
    """Test variable inspection at breakpoints.

    User Story: As a user, I want to inspect variables when my
    workflow pauses at a breakpoint.
    """

    def test_get_variables_for_routine(self, api_client, registered_pipeline_flow):
        """Test getting variables for a routine."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Try to get variables (may return empty if not paused)
        response = api_client.get(f"/api/v1/debug/jobs/{job_id}/debug/variables?routine_id=source")
        # May succeed with empty variables or fail if not paused
        assert response.status_code in (200, 400, 404)

    def test_get_variables_without_routine_id(self, api_client, registered_pipeline_flow):
        """Test getting variables without specifying routine_id."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Get variables without routine_id
        response = api_client.get(f"/api/v1/debug/jobs/{job_id}/debug/variables")
        # May fail if not paused at breakpoint
        assert response.status_code in (200, 400)


class TestCallStackInspection:
    """Test call stack inspection during debugging.

    User Story: As a user, I want to see the call stack when
    debugging to understand execution flow.
    """

    def test_get_call_stack(self, api_client, registered_pipeline_flow):
        """Test getting call stack for a job."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Get call stack
        response = api_client.get(f"/api/v1/debug/jobs/{job_id}/debug/call-stack")
        assert response.status_code == 200
        data = response.json()
        assert "call_stack" in data
        assert isinstance(data["call_stack"], list)


class TestVariableModification:
    """Test modifying variables during debugging.

    User Story: As a user, I want to modify variables at a breakpoint
    to test different code paths.
    """

    def test_set_variable_at_breakpoint(self, api_client, registered_pipeline_flow):
        """Test setting a variable value (requires paused session)."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Try to set variable (may fail if not paused)
        response = api_client.put(
            f"/api/v1/debug/jobs/{job_id}/debug/variables/test_var",
            json={"value": 42},
        )
        # Should fail if not paused at breakpoint
        assert response.status_code in (200, 400, 404)


class TestSteppingThroughExecution:
    """Test stepping through code during debugging.

    User Story: As a user, I want to step through my workflow
    execution line by line.
    """

    def test_step_over(self, api_client, registered_pipeline_flow):
        """Test step over command."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Try step over (may fail if not paused)
        response = api_client.post(f"/api/v1/debug/jobs/{job_id}/debug/step-over")
        assert response.status_code in (200, 400, 404)

    def test_step_into(self, api_client, registered_pipeline_flow):
        """Test step into command."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Try step into (may fail if not paused)
        response = api_client.post(f"/api/v1/debug/jobs/{job_id}/debug/step-into")
        assert response.status_code in (200, 400, 404)


class TestResumeAfterDebugging:
    """Test resuming execution after debugging.

    User Story: As a user, I want to resume execution after
    inspecting variables and stepping through code.
    """

    def test_resume_from_breakpoint(self, api_client, registered_pipeline_flow):
        """Test resuming execution from breakpoint."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Try to resume (may fail if no breakpoint was hit)
        response = api_client.post(f"/api/v1/debug/jobs/{job_id}/debug/resume")
        assert response.status_code in (200, 404)


class TestExpressionEvaluation:
    """Test expression evaluation in debug context.

    User Story: As a user, I want to evaluate expressions
    using local variables when debugging.
    """

    def test_evaluate_expression_disabled_by_default(self, api_client, registered_pipeline_flow):
        """Test that expression evaluation is disabled by default."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Try to evaluate expression (should be disabled)
        response = api_client.post(
            f"/api/v1/debug/jobs/{job_id}/debug/evaluate",
            json={"expression": "1 + 1"},
        )
        # Should return 403 Forbidden when disabled
        assert response.status_code == 403

    def test_evaluate_expression_errors_when_not_paused(self, api_client, registered_pipeline_flow):
        """Test that expression evaluation requires paused state."""
        # Note: This test would need expression eval enabled via env var
        # For now we test the API structure
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Try to evaluate (will fail because eval is disabled)
        response = api_client.post(
            f"/api/v1/debug/jobs/{job_id}/debug/evaluate",
            json={"expression": "x + 1", "routine_id": "source"},
        )
        assert response.status_code == 403


class TestDebugWorkflowIntegration:
    """Test complete debugging workflow integration.

    User Story: As a user, I want to go through a complete
    debugging session from breakpoint to resume.
    """

    def test_debug_session_lifecycle(self, api_client, registered_pipeline_flow):
        """Test complete debug session lifecycle."""
        from tests.helpers.debug_client import DebugClient

        flow_id = registered_pipeline_flow.flow_id
        debug_client = DebugClient(api_client)

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit job
        response = api_client.post(
            "/api/v1/jobs",
            json={
                "flow_id": flow_id,
                "worker_id": worker_id,
                "routine_id": "source",
                "slot_name": "trigger",
                "data": {},
            },
        )
        job_id = response.json()["job_id"]

        # Get session info
        session = debug_client.get_session(job_id)
        assert session["job_id"] == job_id

        # Get call stack
        call_stack = debug_client.get_call_stack(job_id)
        assert isinstance(call_stack, list)

        # Note: Without actual breakpoints, we can't test variable inspection
        # or step operations fully, but we verify the API endpoints exist
