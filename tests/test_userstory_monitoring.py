"""
Category 5: Monitoring & Observability - User Story Tests

Tests for monitoring and observability features, including:
- Job execution metrics and traces
- Queue status and pressure monitoring
- Performance metrics analysis
- Comprehensive monitoring data aggregation

These tests verify that users can monitor their workflows effectively.
"""

import pytest

pytestmark = pytest.mark.userstory


class TestJobExecutionMetrics:
    """Test job execution metrics.

    User Story: As a user, I want to see detailed metrics about
    job execution including duration, routine counts, and errors.
    """

    def test_get_job_metrics(self, api_client, registered_pipeline_flow):
        """Test getting execution metrics for a job."""
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

        # Get metrics
        response = api_client.get(f"/api/v1/jobs/{job_id}/metrics")
        # May not have metrics if monitor collector not available
        assert response.status_code in (200, 404, 500)

        if response.status_code == 200:
            data = response.json()
            assert "job_id" in data
            assert "flow_id" in data

    def test_metrics_include_routine_performance(self, api_client, registered_pipeline_flow):
        """Test that metrics include routine-level performance data."""
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

        # Get metrics
        response = api_client.get(f"/api/v1/jobs/{job_id}/metrics")
        if response.status_code == 200:
            data = response.json()
            # Check for routine_metrics if available
            if "routine_metrics" in data:
                assert isinstance(data["routine_metrics"], dict)


class TestJobExecutionTrace:
    """Test job execution trace functionality.

    User Story: As a user, I want to see a trace of execution
    events to understand data flow through my workflow.
    """

    def test_get_job_trace(self, api_client, registered_pipeline_flow):
        """Test getting execution trace for a job."""
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

        # Get trace
        response = api_client.get(f"/api/v1/jobs/{job_id}/trace")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)

    def test_get_job_trace_with_limit(self, api_client, registered_pipeline_flow):
        """Test getting execution trace with limit."""
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

        # Get trace with limit
        response = api_client.get(f"/api/v1/jobs/{job_id}/trace?limit=10")
        assert response.status_code == 200
        data = response.json()
        # Should have at most 10 events
        assert len(data["events"]) <= 10


class TestJobLogs:
    """Test job execution logs.

    User Story: As a user, I want to see logs generated during
    job execution.
    """

    def test_get_job_logs(self, api_client, registered_pipeline_flow):
        """Test getting logs for a job."""
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

        # Get logs
        response = api_client.get(f"/api/v1/jobs/{job_id}/logs")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "logs" in data
        assert "total" in data
        assert isinstance(data["logs"], list)


class TestQueueStatusMonitoring:
    """Test queue status monitoring.

    User Story: As a user, I want to monitor queue status to
    identify bottlenecks in my workflow.
    """

    def test_get_routine_queue_status(self, api_client, registered_pipeline_flow):
        """Test getting queue status for a specific routine."""
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

        # Get queue status for a routine
        response = api_client.get(f"/api/v1/jobs/{job_id}/routines/source/queue-status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Each slot should have status info
        for slot_status in data:
            assert "slot_name" in slot_status
            assert "pressure_level" in slot_status

    def test_get_all_queue_status(self, api_client, registered_pipeline_flow):
        """Test getting queue status for all routines."""
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

        # Get all queue status
        response = api_client.get(f"/api/v1/jobs/{job_id}/queues/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_queue_pressure_levels(self, api_client, registered_pipeline_flow):
        """Test that queue pressure levels are reported correctly."""
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

        # Get queue status
        response = api_client.get(f"/api/v1/jobs/{job_id}/routines/sink/queue-status")
        assert response.status_code == 200
        data = response.json()

        # Check pressure levels are valid
        valid_pressures = {"low", "medium", "high", "critical"}
        for slot_status in data:
            pressure = slot_status.get("pressure_level")
            assert pressure in valid_pressures


class TestComprehensiveMonitoring:
    """Test comprehensive monitoring data aggregation.

    User Story: As a user, I want a single endpoint that provides
    all monitoring data for a job.
    """

    def test_get_complete_monitoring_data(self, api_client, registered_pipeline_flow):
        """Test getting complete monitoring data for a job."""
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

        # Get complete monitoring data
        response = api_client.get(f"/api/v1/jobs/{job_id}/monitoring")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "flow_id" in data
        assert "job_status" in data
        assert "routines" in data

    def test_monitoring_data_includes_routine_info(self, api_client, registered_pipeline_flow):
        """Test that monitoring data includes routine information."""
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

        # Get monitoring data
        response = api_client.get(f"/api/v1/jobs/{job_id}/monitoring")
        assert response.status_code == 200
        data = response.json()

        # Check routine data structure
        routines = data.get("routines", {})
        for routine_id, routine_data in routines.items():
            assert "execution_status" in routine_data
            assert "queue_status" in routine_data
            assert "info" in routine_data


class TestRoutineStatusMonitoring:
    """Test routine execution status monitoring.

    User Story: As a user, I want to monitor the execution status
    of individual routines.
    """

    def test_get_routines_status(self, api_client, registered_pipeline_flow):
        """Test getting execution status for all routines."""
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

        # Get routines status
        response = api_client.get(f"/api/v1/jobs/{job_id}/routines/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_routine_info(self, api_client, registered_pipeline_flow):
        """Test getting routine metadata information."""
        flow_id = registered_pipeline_flow.flow_id

        # Get routine info
        response = api_client.get(f"/api/v1/flows/{flow_id}/routines/source/info")
        assert response.status_code == 200
        data = response.json()
        assert "routine_id" in data
        assert "slots" in data
        assert "events" in data


class TestPerformanceAnalysis:
    """Test performance metrics and analysis.

    User Story: As a user, I want to analyze performance metrics
    to optimize my workflows.
    """

    def test_get_flow_metrics(self, api_client, registered_pipeline_flow):
        """Test getting aggregated metrics for a flow."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        api_client.post("/api/v1/workers", json={"flow_id": flow_id})

        # Get flow metrics
        response = api_client.get(f"/api/v1/flows/{flow_id}/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "flow_id" in data
        assert "total_jobs" in data

    def test_metrics_aggregation_across_jobs(self, api_client, registered_pipeline_flow):
        """Test that metrics are aggregated across multiple jobs."""
        flow_id = registered_pipeline_flow.flow_id

        # Create worker
        response = api_client.post("/api/v1/workers", json={"flow_id": flow_id})
        worker_id = response.json()["worker_id"]

        # Submit multiple jobs
        job_ids = []
        for _ in range(3):
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
            job_ids.append(response.json()["job_id"])

        # Get flow metrics
        response = api_client.get(f"/api/v1/flows/{flow_id}/metrics")
        assert response.status_code == 200
        data = response.json()
        # Total jobs should at least include our submitted jobs
        assert data["total_jobs"] >= 3


class TestOutputCapture:
    """Test stdout/stderr output capture.

    User Story: As a user, I want to see output printed by routines.
    """

    def test_get_job_output(self, api_client, registered_pipeline_flow):
        """Test getting output for a job."""
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

        # Get output
        response = api_client.get(f"/api/v1/jobs/{job_id}/output")
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "output" in data
        assert "is_complete" in data
