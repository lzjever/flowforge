"""Custom assertion functions for user story tests.

Provides specialized assertion functions for validating
complex system behaviors in integration tests.
"""

from typing import Any, Dict, List, Optional


def assert_execution_order(trace: List[Dict[str, Any]], expected_order: List[str]) -> None:
    """Assert that routines executed in the expected order.

    Args:
        trace: Execution trace from job
        expected_order: List of routine IDs in expected order

    Raises:
        AssertionError: If execution order doesn't match
    """
    executed_routines = []
    for event in trace:
        if event.get("event_type") == "routine_start":
            routine_id = event.get("routine_id")
            if routine_id and routine_id not in executed_routines:
                executed_routines.append(routine_id)

    assert executed_routines == expected_order, (
        f"Execution order mismatch.\nExpected: {expected_order}\nActual: {executed_routines}"
    )


def assert_queue_pressure_progression(
    queue_snapshots: List[Dict[str, Any]], expected_progression: List[str]
) -> None:
    """Assert that queue pressure progressed through expected levels.

    Args:
        queue_snapshots: List of queue status snapshots over time
        expected_progression: List of expected pressure levels (e.g., ["low", "medium", "high"])

    Raises:
        AssertionError: If pressure didn't progress as expected
    """
    actual_progression = []
    for snapshot in queue_snapshots:
        # Get the max pressure level across all slots
        pressures = []
        for slot_status in snapshot:
            pressure = slot_status.get("pressure_level", "unknown")
            pressures.append(pressure)

        if pressures:
            # Order: critical > high > medium > low
            pressure_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
            max_pressure = max(pressures, key=lambda p: pressure_order.get(p, 0))
            if not actual_progression or actual_progression[-1] != max_pressure:
                actual_progression.append(max_pressure)

    assert actual_progression == expected_progression, (
        f"Queue pressure progression mismatch.\n"
        f"Expected: {expected_progression}\n"
        f"Actual: {actual_progression}"
    )


def assert_metrics_consistency(job_metrics: Dict[str, Any], worker_metrics: Dict[str, Any]) -> None:
    """Assert that job and worker metrics are consistent.

    Args:
        job_metrics: Metrics from job endpoint
        worker_metrics: Metrics from worker endpoint

    Raises:
        AssertionError: If metrics are inconsistent
    """
    # For worker metrics, check that processed/failed add up correctly
    processed = worker_metrics.get("jobs_processed", 0)
    failed = worker_metrics.get("jobs_failed", 0)

    # Basic sanity checks
    assert processed >= 0, "jobs_processed cannot be negative"
    assert failed >= 0, "jobs_failed cannot be negative"

    # If job completed successfully, it should be counted
    if job_metrics.get("status") == "completed":
        assert processed >= 1, "Job completed but worker shows 0 processed"


def assert_resource_cleanup(
    client,
    flow_id: str,
    worker_id: Optional[str] = None,
) -> None:
    """Assert that resources were properly cleaned up.

    Args:
        client: FastAPI TestClient
        flow_id: Flow ID to check
        worker_id: Optional worker ID to check

    Raises:
        AssertionError: If resources weren't cleaned up
    """
    # Check flow doesn't exist
    response = client.get(f"/api/v1/flows/{flow_id}")
    assert response.status_code == 404, f"Flow {flow_id} still exists after deletion"

    # Check worker doesn't exist (if provided)
    if worker_id:
        response = client.get(f"/api/v1/workers/{worker_id}")
        assert response.status_code == 404, f"Worker {worker_id} still exists after deletion"

    # No orphaned jobs should reference this flow
    response = client.get(f"/api/v1/jobs?flow_id={flow_id}")
    assert response.status_code == 200
    jobs_data = response.json()
    assert jobs_data["total"] == 0, f"Found {jobs_data['total']} orphaned jobs for flow {flow_id}"


def assert_error_recovery(
    job_metrics: Dict[str, Any],
    error_strategy: str,
    expected_error_count: int = 0,
) -> None:
    """Assert that error recovery worked as expected.

    Args:
        job_metrics: Job metrics including errors
        error_strategy: Error strategy used ("stop", "continue", "retry")
        expected_error_count: Expected number of errors

    Raises:
        AssertionError: If error recovery didn't work as expected
    """
    errors = job_metrics.get("errors", [])
    actual_error_count = len(errors)

    assert actual_error_count == expected_error_count, (
        f"Error count mismatch for strategy '{error_strategy}'.\n"
        f"Expected: {expected_error_count}, Actual: {actual_error_count}\n"
        f"Errors: {errors}"
    )

    # For "stop" strategy, job should fail immediately
    if error_strategy == "stop" and expected_error_count > 0:
        assert job_metrics.get("status") in ("failed", "FAILED"), (
            f"Job should have failed with 'stop' strategy, got status: {job_metrics.get('status')}"
        )

    # For "continue" strategy, job should complete despite errors
    if error_strategy == "continue":
        assert job_metrics.get("status") in ("completed", "COMPLETED"), (
            f"Job should have completed with 'continue' strategy, got status: {job_metrics.get('status')}"
        )


def assert_queue_not_full(queue_status: List[Dict[str, Any]]) -> None:
    """Assert that no queues are full.

    Args:
        queue_status: List of slot queue statuses

    Raises:
        AssertionError: If any queue is full
    """
    for slot in queue_status:
        assert not slot.get("is_full", False), (
            f"Queue {slot.get('slot_name')} is full "
            f"(usage: {slot.get('usage_percentage', 0) * 100:.1f}%)"
        )


def assert_all_routines_executed(job_metrics: Dict[str, Any], expected_routines: List[str]) -> None:
    """Assert that all expected routines executed.

    Args:
        job_metrics: Job metrics with routine_metrics
        expected_routines: List of expected routine IDs

    Raises:
        AssertionError: If any routine didn't execute
    """
    routine_metrics = job_metrics.get("routine_metrics", {})

    for routine_id in expected_routines:
        assert routine_id in routine_metrics, f"Routine {routine_id} not found in metrics"

        metrics = routine_metrics[routine_id]
        exec_count = metrics.get("execution_count", 0)
        assert exec_count > 0, f"Routine {routine_id} has execution_count={exec_count}"


def assert_data_flow(
    trace: List[Dict[str, Any]],
    expected_flow: List[tuple],
) -> None:
    """Assert that data flowed through expected connections.

    Args:
        trace: Execution trace
        expected_flow: List of (source_routine, source_event, target_routine) tuples

    Raises:
        AssertionError: If data flow doesn't match
    """
    # Extract event emissions
    emissions = []
    for event in trace:
        if event.get("event_type") == "event_emit":
            data = event.get("data", {})
            if "event" in data:
                emissions.append(
                    {
                        "routine_id": event.get("routine_id"),
                        "event": data.get("event"),
                    }
                )

    # Extract slot calls
    slot_calls = []
    for event in trace:
        if event.get("event_type") == "slot_call":
            slot_calls.append(
                {
                    "routine_id": event.get("routine_id"),
                    "slot": event.get("data", {}).get("slot"),
                }
            )

    # Verify each expected connection has data flowing
    for source_routine, source_event, target_routine in expected_flow:
        # Check source emitted the event
        source_emitted = any(
            e["routine_id"] == source_routine and e["event"] == source_event for e in emissions
        )
        assert source_emitted, (
            f"Expected {source_routine}.{source_event} to emit, but no emission found"
        )

        # Check target received data
        target_received = any(s["routine_id"] == target_routine for s in slot_calls)
        assert target_received, f"Expected {target_routine} to receive data, but no slot call found"


def assert_breakpoint_hit(session: Dict[str, Any], expected_routine: str) -> None:
    """Assert that breakpoint was hit at expected routine.

    Args:
        session: Debug session info
        expected_routine: Expected routine ID

    Raises:
        AssertionError: If breakpoint not hit at expected location
    """
    assert session.get("status") == "paused", "Job is not paused at breakpoint"

    paused_at = session.get("paused_at", {})
    actual_routine = paused_at.get("routine_id")

    assert actual_routine == expected_routine, (
        f"Breakpoint hit at wrong routine.\nExpected: {expected_routine}\nActual: {actual_routine}"
    )


def assert_variable_exists(variables: Dict[str, Any], name: str) -> None:
    """Assert that a variable exists.

    Args:
        variables: Variables dictionary
        name: Variable name

    Raises:
        AssertionError: If variable doesn't exist
    """
    assert name in variables, f"Variable '{name}' not found. Available: {list(variables.keys())}"


def assert_monitoring_data_complete(monitoring_data: Dict[str, Any]) -> None:
    """Assert that monitoring data is complete and valid.

    Args:
        monitoring_data: Job monitoring data

    Raises:
        AssertionError: If monitoring data is incomplete
    """
    assert "job_id" in monitoring_data, "Missing job_id in monitoring data"
    assert "flow_id" in monitoring_data, "Missing flow_id in monitoring data"
    assert "job_status" in monitoring_data, "Missing job_status in monitoring data"
    assert "routines" in monitoring_data, "Missing routines in monitoring data"

    # Check each routine has required data
    routines = monitoring_data["routines"]
    for routine_id, routine_data in routines.items():
        assert "execution_status" in routine_data, f"Missing execution_status for {routine_id}"
        assert "queue_status" in routine_data, f"Missing queue_status for {routine_id}"
        assert "info" in routine_data, f"Missing info for {routine_id}"
