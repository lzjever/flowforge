"""
Event loop and task queue management for Flow execution.

Handles task queuing, event loop execution, and task execution.
"""

import logging
import queue
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from routilux.flow.flow import Flow
    from routilux.flow.task import SlotActivationTask


def start_event_loop(flow: "Flow") -> None:
    """Start the event loop thread.

    Args:
        flow: Flow object.
    """
    # CRITICAL fix: Check if required attributes exist before accessing them
    if not hasattr(flow, "_running") or not hasattr(flow, "_execution_thread"):
        raise AttributeError("Flow is missing required attributes: _running or _execution_thread. Ensure Flow.__init__() has been called properly.")

    # CRITICAL fix: Use lock to prevent race condition in thread creation
    with flow._execution_lock:
        # Check if event loop thread is already running (double-checked locking)
        if flow._running and flow._execution_thread is not None and flow._execution_thread.is_alive():
            return

        # If thread exists but is not alive, reset _running flag
        if flow._execution_thread is not None and not flow._execution_thread.is_alive():
            flow._running = False

        # Only create new thread if not running
        if not flow._running:
            flow._running = True
            flow._execution_thread = threading.Thread(target=event_loop, args=(flow,), daemon=True)
            flow._execution_thread.start()


def event_loop(flow: "Flow") -> None:
    """Event loop main logic.

    Args:
        flow: Flow object.
    """
    # CRITICAL fix: Validate required attributes exist before loop
    required_attrs = ["_running", "_paused", "_task_queue", "_execution_lock", "_active_tasks"]
    for attr in required_attrs:
        if not hasattr(flow, attr):
            raise AttributeError(f"Flow is missing required attribute: {attr}. Ensure Flow.__init__() has been called properly.")

    while flow._running:
        try:
            # HIGH fix: Read _paused flag atomically within lock
            with flow._execution_lock:
                is_paused = flow._paused

            if is_paused:
                time.sleep(0.01)
                continue

            try:
                task = flow._task_queue.get(timeout=0.1)
            except queue.Empty:
                # Check if all tasks are complete
                # Since tasks carry JobState, we check completion by examining active tasks
                # If queue is empty and no active tasks, execution is complete
                queue_empty = flow._task_queue.empty()
                with flow._execution_lock:
                    active_tasks = [f for f in flow._active_tasks if not f.done()]
                    active_count = len(active_tasks)

                if queue_empty and active_count == 0:
                    # All tasks completed, break event loop
                    break
                continue

            # Check if executor is still available (not shut down)
            executor = flow._get_executor()
            # HIGH fix: Remove dead code - _get_executor() always returns a valid executor
            # The None check is unreachable since _get_executor creates executor if None
            # Instead, check if executor has been shut down
            try:
                # Try to submit a task to verify executor is still running
                future = executor.submit(execute_task, task, flow)
            except RuntimeError as e:
                # HIGH fix: More robust error handling for executor shutdown
                if "cannot schedule new futures after shutdown" in str(e) or "shutdown" in str(e).lower():
                    logging.warning(f"Executor was shut down, stopping event loop: {e}")
                    flow._running = False
                    break
                # Re-raise unexpected RuntimeError
                logging.error(f"Unexpected RuntimeError submitting task: {e}")
                raise

            with flow._execution_lock:
                flow._active_tasks.add(future)

            # CRITICAL fix: Add exception handling to callback to prevent silent failures
            def on_task_done(fut=future):
                try:
                    with flow._execution_lock:
                        flow._active_tasks.discard(fut)
                    flow._task_queue.task_done()
                except Exception as e:
                    # Log but don't raise - callback exceptions are ignored by Future
                    logging.getLogger(__name__).error(f"Error in task done callback: {e}", exc_info=True)

            future.add_done_callback(on_task_done)

        except Exception as e:
            logging.exception(f"Error in event loop: {e}")


def execute_task(task: "SlotActivationTask", flow: "Flow") -> None:
    """Execute a single task.

    Args:
        task: SlotActivationTask to execute.
        flow: Flow object.
    """
    try:
        if task.connection:
            mapped_data = task.connection._apply_mapping(task.data)
        else:
            mapped_data = task.data

        # CRITICAL fix: Add comprehensive None checks for task.slot.routine
        if task.slot is None:
            raise ValueError(f"Task slot is None, cannot execute task")
        if task.slot.routine is None:
            raise ValueError(f"Task slot {task.slot} has no routine attached")
        # Set routine._current_flow for slot.receive() to find routine_id
        if hasattr(task.slot.routine, '_current_flow'):
            task.slot.routine._current_flow = flow

        task.slot.receive(mapped_data, job_state=task.job_state, flow=flow)

    except Exception as e:
        from routilux.flow.error_handling import handle_task_error

        handle_task_error(task, e, flow)


def enqueue_task(task: "SlotActivationTask", flow: "Flow") -> None:
    """Enqueue a task for execution.

    Args:
        task: SlotActivationTask to enqueue.
        flow: Flow object.
    """
    # CRITICAL fix: Validate required attributes exist
    if not hasattr(flow, "_paused") or not hasattr(flow, "_pending_tasks") or not hasattr(flow, "_task_queue"):
        raise AttributeError("Flow is missing required attributes: _paused, _pending_tasks, or _task_queue. Ensure Flow.__init__() has been called properly.")

    # HIGH fix: Acquire lock to prevent race condition when checking _paused and enqueuing
    with flow._execution_lock:
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
    # CRITICAL fix: Validate required attributes exist
    if not hasattr(flow, "_task_queue") or not hasattr(flow, "_execution_lock") or not hasattr(flow, "_active_tasks"):
        raise AttributeError("Flow is missing required attributes: _task_queue, _execution_lock, or _active_tasks. Ensure Flow.__init__() has been called properly.")

    if not flow._task_queue.empty():
        return False

    with flow._execution_lock:
        active = [f for f in flow._active_tasks if not f.done()]
        return len(active) == 0
