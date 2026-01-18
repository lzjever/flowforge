"""JobMonitor helper class for user story tests.

Provides utilities for monitoring job execution, waiting for completion,
and verifying job metrics and traces.
"""

import time
from typing import Any, Dict, List, Optional


class JobMonitor:
    """Helper class for monitoring job execution.

    Provides methods for waiting for job completion, getting metrics,
    traces, output, and verifying execution behavior.

    Example:
        monitor = JobMonitor(client)
        job_id = monitor.submit_job("my_flow", "processor", "input", {"value": 42})
        monitor.wait_for_completion(job_id, timeout=10)
        metrics = monitor.get_metrics(job_id)
        assert metrics["duration"] < 5.0
    """

    # Default timeout values
    DEFAULT_TIMEOUT = 30.0
    POLL_INTERVAL = 0.2

    # Terminal statuses
    TERMINAL_STATUSES = {"completed", "failed", "cancelled"}

    def __init__(self, client):
        """Initialize JobMonitor.

        Args:
            client: FastAPI TestClient instance
        """
        self.client = client

    def submit_job(
        self,
        flow_id: str,
        routine_id: str,
        slot_name: str,
        data: Dict[str, Any],
        worker_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit a job and return the job ID.

        Args:
            flow_id: Flow identifier
            routine_id: Routine to target
            slot_name: Slot to send data to
            data: Data to send
            worker_id: Optional specific worker ID
            metadata: Optional job metadata

        Returns:
            Job ID
        """
        request = {
            "flow_id": flow_id,
            "routine_id": routine_id,
            "slot_name": slot_name,
            "data": data,
        }
        if worker_id:
            request["worker_id"] = worker_id
        if metadata:
            request["metadata"] = metadata

        response = self.client.post("/api/v1/jobs", json=request)
        assert response.status_code == 201, f"Failed to submit job: {response.text}"
        return response.json()["job_id"]

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get job information.

        Args:
            job_id: Job identifier

        Returns:
            Job information dictionary
        """
        response = self.client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200, f"Failed to get job: {response.text}"
        return response.json()

    def get_status(self, job_id: str) -> str:
        """Get job status (lightweight call).

        Args:
            job_id: Job identifier

        Returns:
            Job status string
        """
        response = self.client.get(f"/api/v1/jobs/{job_id}/status")
        assert response.status_code == 200, f"Failed to get job status: {response.text}"
        return response.json()["status"]

    def wait_for_completion(
        self,
        job_id: str,
        timeout: float = DEFAULT_TIMEOUT,
        expected_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Wait for job to complete.

        Args:
            job_id: Job identifier
            timeout: Maximum time to wait in seconds
            expected_status: Optional expected final status

        Returns:
            Final job information

        Raises:
            TimeoutError: If job doesn't complete within timeout
            AssertionError: If job completes with unexpected status
        """
        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            status = self.get_status(job_id)
            last_status = status

            if status in self.TERMINAL_STATUSES:
                job_info = self.get_job(job_id)
                if expected_status and status != expected_status:
                    raise AssertionError(
                        f"Job {job_id} completed with status '{status}', "
                        f"expected '{expected_status}'. Error: {job_info.get('error', 'N/A')}"
                    )
                return job_info

            time.sleep(self.POLL_INTERVAL)

        raise TimeoutError(
            f"Job {job_id} did not complete within {timeout}s. Last status: '{last_status}'"
        )

    def wait_for_status(
        self,
        job_id: str,
        target_status: str,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> bool:
        """Wait for job to reach a specific status.

        Args:
            job_id: Job identifier
            target_status: Status to wait for
            timeout: Maximum time to wait in seconds

        Returns:
            True if status reached, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_status(job_id)
            if status == target_status:
                return True
            time.sleep(self.POLL_INTERVAL)

        return False

    def get_output(self, job_id: str) -> Dict[str, Any]:
        """Get job output.

        Args:
            job_id: Job identifier

        Returns:
            Output dictionary with 'output' and 'is_complete' keys
        """
        response = self.client.get(f"/api/v1/jobs/{job_id}/output")
        assert response.status_code == 200, f"Failed to get job output: {response.text}"
        return response.json()

    def get_trace(self, job_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get job execution trace.

        Args:
            job_id: Job identifier
            limit: Optional maximum number of trace events

        Returns:
            List of trace event dictionaries
        """
        url = f"/api/v1/jobs/{job_id}/trace"
        if limit is not None:
            url += f"?limit={limit}"
        response = self.client.get(url)
        assert response.status_code == 200, f"Failed to get job trace: {response.text}"
        return response.json()["events"]

    def get_metrics(self, job_id: str) -> Dict[str, Any]:
        """Get job execution metrics.

        Args:
            job_id: Job identifier

        Returns:
            Metrics dictionary with duration, routine_metrics, etc.
        """
        response = self.client.get(f"/api/v1/jobs/{job_id}/metrics")
        assert response.status_code == 200, f"Failed to get job metrics: {response.text}"
        return response.json()

    def get_logs(self, job_id: str) -> List[Dict[str, Any]]:
        """Get job execution logs.

        Args:
            job_id: Job identifier

        Returns:
            List of log entry dictionaries
        """
        response = self.client.get(f"/api/v1/jobs/{job_id}/logs")
        assert response.status_code == 200, f"Failed to get job logs: {response.text}"
        return response.json()["logs"]

    def get_queue_status(self, job_id: str, routine_id: str) -> List[Dict[str, Any]]:
        """Get queue status for a specific routine.

        Args:
            job_id: Job identifier
            routine_id: Routine identifier

        Returns:
            List of queue status dictionaries
        """
        response = self.client.get(f"/api/v1/jobs/{job_id}/routines/{routine_id}/queue-status")
        assert response.status_code == 200, f"Failed to get queue status: {response.text}"
        return response.json()

    def get_all_queues_status(self, job_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get queue status for all routines.

        Args:
            job_id: Job identifier

        Returns:
            Dictionary mapping routine_id to queue status list
        """
        response = self.client.get(f"/api/v1/jobs/{job_id}/queues/status")
        assert response.status_code == 200, f"Failed to get all queues status: {response.text}"
        return response.json()

    def verify_execution_order(self, job_id: str, expected_order: List[str]) -> bool:
        """Verify that routines executed in expected order.

        Args:
            job_id: Job identifier
            expected_order: List of routine IDs in expected execution order

        Returns:
            True if execution order matches expected
        """
        trace = self.get_trace(job_id)

        # Extract routine execution order from trace
        executed_routines = []
        for event in trace:
            if event["event_type"] == "routine_start":
                routine_id = event["routine_id"]
                if routine_id not in executed_routines:
                    executed_routines.append(routine_id)

        return executed_routines == expected_order

    def get_routine_metrics(self, job_id: str, routine_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific routine.

        Args:
            job_id: Job identifier
            routine_id: Routine identifier

        Returns:
            Routine metrics dictionary or None if not found
        """
        metrics = self.get_metrics(job_id)
        return metrics.get("routine_metrics", {}).get(routine_id)

    def assert_execution_count(self, job_id: str, routine_id: str, expected_count: int) -> None:
        """Assert that a routine executed expected number of times.

        Args:
            job_id: Job identifier
            routine_id: Routine identifier
            expected_count: Expected execution count

        Raises:
            AssertionError: If count doesn't match
        """
        routine_metrics = self.get_routine_metrics(job_id, routine_id)
        actual_count = routine_metrics.get("execution_count", 0) if routine_metrics else 0
        assert actual_count == expected_count, (
            f"Routine {routine_id} executed {actual_count} times, expected {expected_count}"
        )

    def assert_duration_less_than(self, job_id: str, max_duration: float) -> None:
        """Assert that job completed within max duration.

        Args:
            job_id: Job identifier
            max_duration: Maximum expected duration in seconds

        Raises:
            AssertionError: If duration exceeds max
        """
        metrics = self.get_metrics(job_id)
        duration = metrics.get("duration", 0)
        assert duration < max_duration, f"Job duration {duration}s exceeded {max_duration}s"

    def assert_no_errors(self, job_id: str) -> None:
        """Assert that job completed without errors.

        Args:
            job_id: Job identifier

        Raises:
            AssertionError: If job had errors
        """
        metrics = self.get_metrics(job_id)
        errors = metrics.get("errors", [])
        assert len(errors) == 0, f"Job had {len(errors)} errors: {errors}"

    def list_jobs(
        self,
        worker_id: Optional[str] = None,
        flow_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """List jobs with optional filters.

        Args:
            worker_id: Filter by worker ID
            flow_id: Filter by flow ID
            status: Filter by status
            limit: Max results
            offset: Pagination offset

        Returns:
            Dictionary with 'jobs' list and 'total' count
        """
        params = []
        if worker_id:
            params.append(f"worker_id={worker_id}")
        if flow_id:
            params.append(f"flow_id={flow_id}")
        if status:
            params.append(f"status={status}")
        params.append(f"limit={limit}")
        params.append(f"offset={offset}")

        url = f"/api/v1/jobs?{'&'.join(params)}"
        response = self.client.get(url)
        assert response.status_code == 200, f"Failed to list jobs: {response.text}"
        return response.json()
