"""
Event loop and task queue management for Flow execution.

Handles task queuing, event loop execution, and task execution.
"""

import queue
import threading
import time
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from routilux.flow.task import SlotActivationTask
    from routilux.flow.flow import Flow


def start_event_loop(flow: "Flow") -> None:
    """Start the event loop thread.

    Args:
        flow: Flow object.
    """
    # Check if event loop thread is already running
    if flow._running and flow._execution_thread is not None and flow._execution_thread.is_alive():
        return

    # If thread exists but is not alive, reset _running flag
    if flow._execution_thread is not None and not flow._execution_thread.is_alive():
        flow._running = False

    flow._running = True
    flow._execution_thread = threading.Thread(target=event_loop, args=(flow,), daemon=True)
    flow._execution_thread.start()


def event_loop(flow: "Flow") -> None:
    """Event loop main logic.

    Args:
        flow: Flow object.
    """
    while flow._running:
        try:
            if flow._paused:
                time.sleep(0.01)
                continue

            try:
                task = flow._task_queue.get(timeout=0.1)
            except queue.Empty:
                # Check if all tasks are complete using systematic verification
                # This avoids race conditions where tasks are enqueued between checks
                from routilux.flow.completion import ExecutionCompletionChecker

                job_state = getattr(flow._current_execution_job_state, "value", None)
                if job_state is None:
                    # No job state available, continue waiting
                    continue

                # Use systematic completion checker
                # For test environments, use faster checks
                import os

                is_test_env = os.getenv("PYTEST_CURRENT_TEST") is not None
                if is_test_env:
                    stability_checks = 2
                    check_interval = 0.01
                    stability_delay = 0.005
                else:
                    stability_checks = 3
                    check_interval = 0.05
                    stability_delay = 0.02

                checker = ExecutionCompletionChecker(
                    flow=flow,
                    job_state=job_state,
                    stability_checks=stability_checks,
                    check_interval=check_interval,
                    stability_delay=stability_delay,
                )

                if checker.check_with_stability():
                    # Update JobState if still running
                    if job_state.status == "running":
                        job_state.status = "completed"
                    break
                continue

            # Check if executor is still available (not shut down)
            executor = flow._get_executor()
            if executor is None:
                # Executor was shut down, stop event loop
                logging.warning("Executor was shut down, stopping event loop")
                flow._running = False
                break

            try:
                future = executor.submit(execute_task, task, flow)
            except RuntimeError as e:
                # Executor was shut down, stop event loop
                if "cannot schedule new futures after shutdown" in str(e):
                    logging.warning("Executor was shut down, stopping event loop")
                    flow._running = False
                    break
                raise

            with flow._execution_lock:
                flow._active_tasks.add(future)

            def on_task_done(fut=future):
                with flow._execution_lock:
                    flow._active_tasks.discard(fut)
                flow._task_queue.task_done()

            future.add_done_callback(on_task_done)

        except Exception as e:
            logging.exception(f"Error in event loop: {e}")
            # Continue loop even on error to prevent silent failures


def execute_task(task: "SlotActivationTask", flow: "Flow") -> None:
    """Execute a single task.

    Args:
        task: SlotActivationTask to execute.
        flow: Flow object.
    """
    # Set JobState in thread-local storage for this task execution
    # This allows handlers and error handlers to access JobState even in worker threads
    if task.job_state:
        flow._current_execution_job_state.value = task.job_state

    try:
        if task.connection:
            mapped_data = task.connection._apply_mapping(task.data)
        else:
            mapped_data = task.data

        task.slot.receive(mapped_data)

    except Exception as e:
        from routilux.flow.error_handling import handle_task_error

        handle_task_error(task, e, flow)
    finally:
        # Clear thread-local storage after task execution
        # This ensures that if the same worker thread executes a task from a different
        # execution, it won't accidentally access the previous execution's JobState
        flow._current_execution_job_state.value = None


def enqueue_task(task: "SlotActivationTask", flow: "Flow") -> None:
    """Enqueue a task for execution.

    Args:
        task: SlotActivationTask to enqueue.
        flow: Flow object.
    """
    if flow._paused:
        flow._pending_tasks.append(task)
    else:
        flow._task_queue.put(task)


def is_all_tasks_complete(flow: "Flow") -> bool:
    """Check if all tasks are complete.

    Args:
        flow: Flow object.

    Returns:
        True if queue is empty and no active tasks.
    """
    if not flow._task_queue.empty():
        return False

    with flow._execution_lock:
        active = [f for f in flow._active_tasks if not f.done()]
        return len(active) == 0
