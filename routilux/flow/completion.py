"""
Execution completion detection and waiting mechanism.

This module provides a robust, systematic approach to waiting for flow execution
to complete, handling race conditions, long-running tasks, and edge cases.
"""

import time
import logging
from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from routilux.flow.flow import Flow
    from routilux.job_state import JobState

logger = logging.getLogger(__name__)


class ExecutionCompletionChecker:
    """Systematic execution completion checker.

    This class provides a robust mechanism to check if flow execution has completed,
    handling race conditions and edge cases properly.

    Key Features:
    - Multiple verification passes to avoid race conditions
    - Configurable stability requirements
    - Support for long-running tasks
    - Proper handling of paused/cancelled states
    """

    def __init__(
        self,
        flow: "Flow",
        job_state: "JobState",
        stability_checks: int = 5,
        check_interval: float = 0.1,
        stability_delay: float = 0.05,
    ):
        """Initialize completion checker.

        Args:
            flow: Flow object to check.
            job_state: JobState object to check.
            stability_checks: Number of consecutive checks required for stability.
            check_interval: Interval between checks in seconds.
            stability_delay: Delay between stability checks in seconds.
        """
        self.flow = flow
        self.job_state = job_state
        self.stability_checks = stability_checks
        self.check_interval = check_interval
        self.stability_delay = stability_delay

    def is_complete(self) -> bool:
        """Check if execution is complete.

        Returns:
            True if execution is complete, False otherwise.
        """
        # Check if execution was paused or cancelled
        if self.job_state.status in ["paused", "cancelled"]:
            return True

        # Check if execution failed
        if self.job_state.status == "failed":
            return True

        # Check queue and active tasks
        queue_empty = self.flow._task_queue.empty()
        with self.flow._execution_lock:
            active_tasks = [f for f in self.flow._active_tasks if not f.done()]
            active_count = len(active_tasks)

        # Execution is complete if:
        # 1. Queue is empty
        # 2. No active tasks
        # 3. JobState status is completed, failed, paused, or cancelled
        # OR if queue is empty and no active tasks (even if status is still "running")
        #    This handles the case where all tasks are done but status hasn't been updated yet
        if queue_empty and active_count == 0:
            # If status is already final, definitely complete
            if self.job_state.status in ["completed", "failed", "paused", "cancelled"]:
                return True
            # If status is "running" but queue is empty and no active tasks,
            # execution is effectively complete (tasks are done, just status not updated)
            if self.job_state.status == "running":
                return True

        return False

    def check_with_stability(self) -> bool:
        """Check completion with stability verification.

        Performs multiple checks to avoid race conditions where tasks might be
        enqueued between checks.

        Returns:
            True if execution is consistently complete across all checks.
        """
        for _ in range(self.stability_checks):
            if not self.is_complete():
                return False
            time.sleep(self.stability_delay)

        return True


def wait_for_execution_completion(
    flow: "Flow",
    job_state: "JobState",
    timeout: Optional[float] = None,
    stability_checks: int = 5,
    check_interval: float = 0.1,
    stability_delay: float = 0.05,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> bool:
    """Wait for flow execution to complete.

    This function provides a robust, systematic way to wait for flow execution
    to complete, handling:
    - Race conditions where tasks are enqueued after initial check
    - Long-running tasks (e.g., LLM calls)
    - Edge cases where event loop might exit prematurely

    Args:
        flow: Flow object to wait for.
        job_state: JobState object to monitor.
        timeout: Maximum time to wait in seconds. None for no timeout.
        stability_checks: Number of consecutive checks required for stability.
        check_interval: Interval between checks in seconds.
        stability_delay: Delay between stability checks in seconds.
        progress_callback: Optional callback function called periodically with
            (queue_size, active_count, status) tuple.

    Returns:
        True if execution completed before timeout, False if timeout occurred.

    Examples:
        Basic usage:
            >>> job_state = flow.execute(entry_routine_id, entry_params)
            >>> completed = wait_for_execution_completion(flow, job_state, timeout=300.0)
            >>> if completed:
            ...     print("Execution completed successfully")

        With progress callback:
            >>> def progress(queue_size, active_count, status):
            ...     print(f"Queue: {queue_size}, Active: {active_count}, Status: {status}")
            >>> wait_for_execution_completion(flow, job_state, progress_callback=progress)
    """
    checker = ExecutionCompletionChecker(
        flow=flow,
        job_state=job_state,
        stability_checks=stability_checks,
        check_interval=check_interval,
        stability_delay=stability_delay,
    )

    start_time = time.time()
    last_progress_time = 0.0
    progress_interval = 5.0  # Report progress every 5 seconds

    while True:
        # Check timeout
        if timeout is not None:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                logger.warning(
                    f"Execution completion wait timed out after {timeout} seconds. "
                    f"Queue size: {flow._task_queue.qsize()}, "
                    f"Active tasks: {len([f for f in flow._active_tasks if not f.done()])}, "
                    f"Status: {job_state.status}"
                )
                return False

        # Check completion with stability verification
        if checker.check_with_stability():
            logger.debug("Execution completed successfully")
            return True

        # Report progress if callback provided
        if progress_callback is not None:
            current_time = time.time()
            if current_time - last_progress_time >= progress_interval:
                queue_size = flow._task_queue.qsize()
                with flow._execution_lock:
                    active_count = len([f for f in flow._active_tasks if not f.done()])
                progress_callback(queue_size, active_count, job_state.status)
                last_progress_time = current_time

        # Wait before next check
        time.sleep(check_interval)


def ensure_event_loop_running(flow: "Flow") -> bool:
    """Ensure event loop is running, restart if needed.

    This function checks if the event loop is running and restarts it if:
    - Event loop thread is not alive
    - There are tasks in the queue

    Args:
        flow: Flow object to check.

    Returns:
        True if event loop is running (or was restarted), False otherwise.
    """
    from routilux.flow.event_loop import start_event_loop

    queue_size = flow._task_queue.qsize()
    is_running = flow._execution_thread is not None and flow._execution_thread.is_alive()

    # If there are tasks but event loop is not running, restart it
    if queue_size > 0 and not is_running:
        logger.warning(
            f"Event loop stopped but {queue_size} tasks in queue. Restarting event loop."
        )
        start_event_loop(flow)
        return True

    return is_running
