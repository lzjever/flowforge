"""
Execution logic for Flow.

Handles sequential and concurrent execution of workflows.
"""

import time
import logging
from datetime import datetime
from typing import Dict, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from routilux.flow.flow import Flow
    from routilux.job_state import JobState


def execute_flow(
    flow: "Flow",
    entry_routine_id: str,
    entry_params: Optional[Dict[str, Any]] = None,
    execution_strategy: Optional[str] = None,
    timeout: Optional[float] = None,
) -> "JobState":
    """Execute the flow starting from the specified entry routine.

    Args:
        flow: Flow object.
        entry_routine_id: Identifier of the routine to start execution from.
        entry_params: Optional dictionary of parameters to pass to the entry routine's trigger slot.
        execution_strategy: Optional execution strategy override.
        timeout: Optional timeout for execution completion in seconds.
            If None, uses flow.execution_timeout (default: 300.0 seconds).

    Returns:
        JobState object.

    Raises:
        ValueError: If entry_routine_id does not exist in the flow.
    """
    if entry_routine_id not in flow.routines:
        raise ValueError(f"Entry routine '{entry_routine_id}' not found in flow")

    # Note: Multiple executions are allowed and independent
    # Each execute() creates a new JobState and execution context

    strategy = execution_strategy or flow.execution_strategy
    execution_timeout = timeout if timeout is not None else flow.execution_timeout

    if strategy == "concurrent":
        return execute_concurrent(flow, entry_routine_id, entry_params, timeout=execution_timeout)
    else:
        return execute_sequential(flow, entry_routine_id, entry_params, timeout=execution_timeout)


def execute_sequential(
    flow: "Flow",
    entry_routine_id: str,
    entry_params: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
) -> "JobState":
    """Execute Flow using unified queue-based mechanism.

    Args:
        flow: Flow object.
        entry_routine_id: Entry routine identifier.
        entry_params: Entry parameters.

    Returns:
        JobState object.
    """
    from routilux.job_state import JobState
    from routilux.execution_tracker import ExecutionTracker
    from routilux.flow.event_loop import start_event_loop
    from routilux.flow.error_handling import get_error_handler_for_routine

    job_state = JobState(flow.flow_id)
    job_state.status = "running"
    job_state.current_routine_id = entry_routine_id

    # Store JobState in thread-local storage for access during execution
    # This allows event loop and error handlers to access the current JobState
    flow._current_execution_job_state.value = job_state

    flow.execution_tracker = ExecutionTracker(flow.flow_id)

    entry_params = entry_params or {}
    entry_routine = flow.routines[entry_routine_id]

    try:
        for routine in flow.routines.values():
            routine._current_flow = flow

        start_time = datetime.now()
        job_state.record_execution(entry_routine_id, "start", entry_params)
        flow.execution_tracker.record_routine_start(entry_routine_id, entry_params)

        start_event_loop(flow)

        trigger_slot = entry_routine.get_slot("trigger")
        if trigger_slot is None:
            raise ValueError(
                f"Entry routine '{entry_routine_id}' must have a 'trigger' slot. "
                f"Define it using: routine.define_slot('trigger', handler=your_handler)"
            )

        trigger_slot.call_handler(entry_params or {}, propagate_exceptions=True)

        # Wait for all tasks to be processed using systematic completion checking
        from routilux.flow.completion import (
            wait_for_execution_completion,
            ensure_event_loop_running,
        )

        # Use provided timeout or flow's default timeout
        execution_timeout = timeout if timeout is not None else flow.execution_timeout

        # Ensure event loop is running before waiting
        ensure_event_loop_running(flow)

        # Use systematic completion waiting mechanism
        # For test environments, use faster checks; for production, use more robust checks
        import os

        is_test_env = os.getenv("PYTEST_CURRENT_TEST") is not None
        if is_test_env:
            # Faster checks for testing
            stability_checks = 2
            check_interval = 0.01
            stability_delay = 0.005
        else:
            # More robust checks for production
            stability_checks = 5
            check_interval = 0.1
            stability_delay = 0.05

        completed = wait_for_execution_completion(
            flow=flow,
            job_state=job_state,
            timeout=execution_timeout,
            stability_checks=stability_checks,
            check_interval=check_interval,
            stability_delay=stability_delay,
        )

        if not completed:
            logging.warning(
                f"Execution did not complete within timeout. "
                f"Queue size: {flow._task_queue.qsize()}, "
                f"Status: {job_state.status}"
            )
            # If timeout occurred, mark as failed (unless already in a final state)
            if job_state.status == "running":
                job_state.status = "failed"
                job_state.update_routine_state(
                    entry_routine_id, {"status": "timeout", "error": "Execution timed out"}
                )

        # Shutdown event loop after completion check
        # This ensures the event loop stops properly
        flow._running = False

        # Wait for event loop thread to finish
        # Use a shorter timeout for test environments
        if flow._execution_thread:
            if is_test_env:
                join_timeout = 2.0  # Shorter timeout for tests
            else:
                join_timeout = 10.0  # Longer timeout for production
            flow._execution_thread.join(timeout=join_timeout)
            if flow._execution_thread.is_alive():
                logging.warning(f"Event loop thread did not finish within {join_timeout}s timeout")

        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        job_state.update_routine_state(
            entry_routine_id,
            {
                "status": "completed",
                "execution_time": execution_time,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

        # Only mark as completed if not paused and not already failed (e.g., due to timeout)
        if job_state.status not in ["paused", "failed"]:
            job_state.record_execution(
                entry_routine_id, "completed", {"execution_time": execution_time}
            )
            flow.execution_tracker.record_routine_end(entry_routine_id, "completed")
            job_state.status = "completed"

        # Clear thread-local storage after execution completes
        if hasattr(flow._current_execution_job_state, "value"):
            flow._current_execution_job_state.value = None

    except Exception as e:
        error_handler = get_error_handler_for_routine(entry_routine, entry_routine_id, flow)
        if error_handler:
            should_continue = error_handler.handle_error(e, entry_routine, entry_routine_id, flow)

            if error_handler.strategy.value == "continue":
                job_state.status = "completed"
                job_state.update_routine_state(
                    entry_routine_id,
                    {
                        "status": "error_continued",
                        "error": str(e),
                    },
                )
                return job_state

            if error_handler.strategy.value == "skip":
                job_state.status = "completed"
                return job_state

            if should_continue and error_handler.strategy.value == "retry":
                retry_success = False
                remaining_retries = error_handler.max_retries
                trigger_slot = entry_routine.get_slot("trigger")
                if trigger_slot is None:
                    raise ValueError(
                        f"Entry routine '{entry_routine_id}' must have a 'trigger' slot. "
                        f"Define it using: routine.define_slot('trigger', handler=your_handler)"
                    )
                for attempt in range(remaining_retries):
                    try:
                        trigger_slot.call_handler(entry_params or {}, propagate_exceptions=True)
                        retry_success = True
                        break
                    except Exception as retry_error:
                        should_continue_retry = error_handler.handle_error(
                            retry_error, entry_routine, entry_routine_id, flow
                        )
                        if not should_continue_retry:
                            e = retry_error
                            break
                        if attempt >= remaining_retries - 1:
                            e = retry_error
                            break

                if retry_success:
                    end_time = datetime.now()
                    execution_time = (end_time - start_time).total_seconds()
                    job_state.update_routine_state(
                        entry_routine_id,
                        {
                            "status": "completed",
                            "execution_time": execution_time,
                            "retry_count": error_handler.retry_count,
                        },
                    )
                    job_state.record_execution(
                        entry_routine_id,
                        "completed",
                        {"execution_time": execution_time, "retried": True},
                    )
                    if flow.execution_tracker:
                        flow.execution_tracker.record_routine_end(entry_routine_id, "completed")
                    job_state.status = "completed"
                    return job_state

        error_time = datetime.now()
        job_state.status = "failed"
        job_state.update_routine_state(
            entry_routine_id,
            {"status": "failed", "error": str(e), "error_time": error_time.isoformat()},
        )
        job_state.record_execution(
            entry_routine_id, "error", {"error": str(e), "error_type": type(e).__name__}
        )
        if flow.execution_tracker:
            flow.execution_tracker.record_routine_end(entry_routine_id, "failed", error=str(e))

        logging.exception(f"Error executing flow: {e}")

    # Clear thread-local storage after execution completes (success or failure)
    if hasattr(flow._current_execution_job_state, "value"):
        flow._current_execution_job_state.value = None

    return job_state


def execute_concurrent(
    flow: "Flow",
    entry_routine_id: str,
    entry_params: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
) -> "JobState":
    """Execute Flow concurrently using unified queue-based mechanism.

    In concurrent mode, max_workers > 1, allowing parallel task execution.
    The queue-based mechanism handles concurrency automatically.

    Args:
        flow: Flow object.
        entry_routine_id: Entry routine identifier.
        entry_params: Entry parameters.
        timeout: Optional timeout for execution completion in seconds.

    Returns:
        JobState object.
    """
    return execute_sequential(flow, entry_routine_id, entry_params, timeout=timeout)
