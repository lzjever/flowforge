"""
Job executor for managing individual job execution context.

Each job has its own JobExecutor instance with:
- Independent task queue
- Independent event loop thread
- Reference to global thread pool
- Bound to a specific JobState
"""

import logging
import queue
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from concurrent.futures import Future, ThreadPoolExecutor

    from routilux.execution_tracker import ExecutionTracker
    from routilux.flow.flow import Flow
    from routilux.flow.task import SlotActivationTask
    from routilux.job_state import JobState

logger = logging.getLogger(__name__)


class JobExecutor:
    """Manages execution context for a single job.

    Each job has its own JobExecutor with:
    - Independent task queue (tasks are processed in order)
    - Independent event loop thread (processes tasks from queue)
    - Reference to global thread pool (shared by all jobs)
    - Bound to a specific JobState (tracks execution state)

    The JobExecutor is responsible for:
    - Starting job execution
    - Processing tasks via event loop
    - Handling timeouts
    - Detecting completion
    - Cleaning up resources

    Attributes:
        flow: Flow being executed.
        job_state: JobState for this execution.
        global_thread_pool: Global thread pool for task execution.
        timeout: Execution timeout in seconds.
        task_queue: Queue of tasks to execute.
        pending_tasks: Tasks that are paused/pending serialization.
        event_loop_thread: Thread running the event loop.
        active_tasks: Set of currently executing futures.
        execution_tracker: Tracks execution history for this job.
    """

    def __init__(
        self,
        flow: "Flow",
        job_state: "JobState",
        global_thread_pool: "ThreadPoolExecutor",
        timeout: float | None = None,
    ):
        """Initialize job executor.

        Args:
            flow: Flow to execute.
            job_state: JobState for this execution.
            global_thread_pool: Global thread pool to use.
            timeout: Execution timeout in seconds.
        """
        self.flow = flow
        self.job_state = job_state
        self.global_thread_pool = global_thread_pool
        self.timeout = timeout

        # Independent execution context
        # Task queue can contain both SlotActivationTask and EventRoutingTask
        self.task_queue: queue.Queue = queue.Queue()
        self.pending_tasks: list[SlotActivationTask] = []
        self.event_loop_thread: Optional[threading.Thread] = None
        self.active_tasks: set[Future] = set()
        self._running = False
        self._paused = False
        self._lock = threading.Lock()
        self._start_time: Optional[float] = None

        # Execution tracker (one per job)
        self.execution_tracker: Optional[ExecutionTracker] = None

        # Set JobExecutor reference in JobState
        job_state._job_executor = self

        # Set flow context for all routines
        for routine in flow.routines.values():
            routine._current_flow = flow
            # Runtime will be set when job starts via job_state._current_runtime

    def start(self) -> None:
        """Start job execution.

        This method starts the event loop thread. All routines start in IDLE state,
        waiting for external events via Runtime.post().

        It returns immediately without waiting for execution to complete.

        Raises:
            RuntimeError: If job is already running.
        """
        # CRITICAL fix: Acquire lock before checking _running flag
        with self._lock:
            if self._running:
                raise RuntimeError(f"Job {self.job_state.job_id} is already running")

        from routilux.execution_tracker import ExecutionTracker
        from routilux.status import ExecutionStatus, RoutineStatus

        # Update job state
        self.job_state.status = ExecutionStatus.RUNNING
        # Set started_at timestamp
        self.job_state.started_at = datetime.now()
        self._start_time = time.time()

        # Initialize all routines to IDLE state
        for routine_id in self.flow.routines.keys():
            self.job_state.update_routine_state(
                routine_id, {"status": RoutineStatus.IDLE.value}
            )

        # Create execution tracker (one per job)
        self.execution_tracker = ExecutionTracker(self.flow.flow_id)

        # Monitoring hook: Flow start
        from routilux.monitoring.hooks import execution_hooks

        try:
            execution_hooks.on_flow_start(self.flow, self.job_state)
        except Exception as e:
            # Hook exceptions should not crash Runtime
            logger.warning(f"Exception in on_flow_start hook: {e}", exc_info=True)

        # Start event loop
        # CRITICAL fix: Acquire lock before setting _running flag
        with self._lock:
            self._running = True
        self.event_loop_thread = threading.Thread(
            target=self._event_loop, daemon=True, name=f"JobExecutor-{self.job_state.job_id[:8]}"
        )
        self.event_loop_thread.start()

        logger.debug(f"Started job {self.job_state.job_id}, all routines in IDLE state")

    def _event_loop(self) -> None:
        """Event loop main logic.

        This runs in a separate thread and processes tasks from the queue.
        Tasks are submitted to the global thread pool for execution.
        """
        while self._running:
            try:
                # Check timeout
                if self._check_timeout():
                    break

                # Check if paused
                # CRITICAL fix: Read _paused flag atomically to avoid race condition
                # Use getattr for thread-safe read (simple attribute reads are atomic in CPython)
                current_paused = getattr(self, '_paused', False)
                if current_paused:
                    time.sleep(0.01)
                    continue

                # Get task from queue
                try:
                    task = self.task_queue.get(timeout=0.1)
                except queue.Empty:
                    # Check if complete
                    if self._is_complete():
                        self._handle_idle()  # Changed from _handle_completion
                        # Don't break - continue running to wait for new tasks
                        continue
                    continue

                # Check task type
                from routilux.flow.task import EventRoutingTask, SlotActivationTask

                if isinstance(task, EventRoutingTask):
                    # Route event in event loop thread
                    try:
                        task.runtime.handle_event_emit(
                            task.event, task.event_data, task.job_state
                        )
                    except Exception as e:
                        logger.exception(
                            f"Error routing event in event loop for job {self.job_state.job_id}: {e}"
                        )
                    finally:
                        self.task_queue.task_done()
                elif isinstance(task, SlotActivationTask):
                    # Submit routine execution to global thread pool
                    future = self.global_thread_pool.submit(self._execute_task, task)

                    with self._lock:
                        self.active_tasks.add(future)

                    def on_done(fut: "Future" = future) -> None:
                        with self._lock:
                            self.active_tasks.discard(fut)
                        try:
                            self.task_queue.task_done()
                        except ValueError:
                            # task_done() called more times than put()
                            pass

                    future.add_done_callback(on_done)
                else:
                    # Unknown task type - log and mark as done
                    logger.warning(
                        f"Unknown task type in event loop: {type(task).__name__}"
                    )
                    self.task_queue.task_done()

            except Exception as e:
                logger.exception(f"Error in event loop for job {self.job_state.job_id}: {e}")
                self._handle_error(e)
                break

        # Cleanup
        self._cleanup()

    def _execute_task(self, task: "SlotActivationTask") -> None:
        """Execute a single task.

        Args:
            task: SlotActivationTask to execute.
        """
        from routilux.routine import _current_job_state

        # Set job_state in context variable
        old_job_state = _current_job_state.get(None)
        try:
            _current_job_state.set(self.job_state)
        except Exception:
            # Critical: If set fails, still try to restore in finally
            old_job_state = None

        try:
            mapped_data = task.data

            # Set routine context
            if task.slot.routine:
                task.slot.routine._current_flow = self.flow
                # Set runtime from job_state for event routing
                runtime = getattr(self.job_state, "_current_runtime", None)
                if runtime:
                    task.slot.routine._current_runtime = runtime

            # Enqueue data to slot
            from datetime import datetime
            task.slot.enqueue(
                data=mapped_data,
                emitted_from="external" if task.connection is None else (task.connection.source_routine_id or "external"),
                emitted_at=datetime.now(),
            )

            # Get routine and trigger activation check
            routine = task.slot.routine
            if routine is not None:
                runtime = getattr(self.job_state, "_current_runtime", None)
                if runtime:
                    # Trigger routine activation check
                    runtime._check_routine_activation(routine, self.job_state)

            # After slot execution, check if routine should be marked as IDLE
            if task.slot.routine:
                routine_id = self.flow._get_routine_id(task.slot.routine)
                if routine_id:
                    # Check if routine has no pending data in any slot
                    has_pending_data = False
                    for slot in task.slot.routine.slots.values():
                        if slot.get_unconsumed_count() > 0:
                            has_pending_data = True
                            break

                    if not has_pending_data:
                        # Mark routine as IDLE
                        from routilux.status import RoutineStatus

                        self.job_state.update_routine_state(
                            routine_id, {"status": RoutineStatus.IDLE.value}
                        )

                        # Check if all routines are IDLE
                        if self._all_routines_idle() and self._is_complete():
                            self._handle_idle()

        except Exception as e:
            from routilux.flow.error_handling import handle_task_error

            handle_task_error(task, e, self.flow)
        finally:
            # HIGH fix: Ensure context is restored even if set() fails
            try:
                if old_job_state is not None:
                    _current_job_state.set(old_job_state)
                else:
                    _current_job_state.set(None)
            except Exception:
                # Log but don't raise - cleanup is critical
                import logging
                logging.getLogger(__name__).exception("Failed to restore job_state context variable")
                pass


    def enqueue_task(self, task: Any) -> None:
        """Enqueue a task for execution.

        Supports both SlotActivationTask and EventRoutingTask.

        If the job is paused, the task is added to pending_tasks instead.

        Args:
            task: SlotActivationTask or EventRoutingTask to enqueue.
        """
        # CRITICAL fix: Read _paused flag atomically to avoid race condition
        current_paused = getattr(self, '_paused', False)
        if current_paused:
            # HIGH fix: Acquire lock before modifying pending_tasks
            with self._lock:
                self.pending_tasks.append(task)
        else:
            self.task_queue.put(task)

    def _check_timeout(self) -> bool:
        """Check if job has timed out.

        Returns:
            True if timed out, False otherwise.
        """
        if self.timeout is not None and self._start_time is not None:
            elapsed = time.time() - self._start_time
            if elapsed >= self.timeout:
                logger.warning(f"Job {self.job_state.job_id} timed out after {self.timeout}s")
                self._handle_timeout()
                return True
        return False

    def _is_complete(self) -> bool:
        """Check if job has no pending work.

        A job has no pending work when:
        - Task queue is empty
        - No active tasks are running

        Returns:
            True if queue is empty and no active tasks.
        """
        # CRITICAL fix: Acquire lock before checking queue and active_tasks to prevent race condition
        with self._lock:
            if not self.task_queue.empty():
                return False
            active = [f for f in self.active_tasks if not f.done()]
            return len(active) == 0

    def _all_routines_idle(self) -> bool:
        """Check if all routines are in IDLE state.

        Returns:
            True if all routines are IDLE, False otherwise.
        """
        from routilux.status import RoutineStatus

        for routine_id in self.flow.routines.keys():
            routine_state = self.job_state.get_routine_state(routine_id)
            if routine_state is None:
                # Routine hasn't been executed yet - not idle
                return False
            status = routine_state.get("status")
            if status not in (RoutineStatus.IDLE, RoutineStatus.COMPLETED):
                return False
        return True

    def _handle_idle(self) -> None:
        """Handle job going idle (all routines completed, waiting for new tasks).

        This marks the job as IDLE but keeps the event loop running to wait for new tasks.
        """
        from routilux.status import ExecutionStatus

        # Only mark as idle if not already in a terminal state
        if self.job_state.status not in (
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
            ExecutionStatus.COMPLETED,
        ):
            # Check if all routines are idle
            if self._all_routines_idle() and self._is_complete():
                if self.job_state.status != ExecutionStatus.IDLE:
                    self.job_state.status = ExecutionStatus.IDLE
                    logger.debug(f"Job {self.job_state.job_id} is now IDLE")

    def _handle_completion(self) -> None:
        """Handle job completion (deprecated - use _handle_idle instead).

        This method is kept for backward compatibility but should not be called
        in the new model where jobs go to IDLE instead of COMPLETED automatically.
        """
        # This method is no longer used - jobs go to IDLE instead
        pass

    def complete(self) -> None:
        """User-initiated job completion.

        This stops the event loop thread and marks the job as COMPLETED.
        The job will be cleaned up from the registry after the retention period.
        """
        from routilux.monitoring.hooks import execution_hooks
        from routilux.status import ExecutionStatus

        # Stop event loop
        with self._lock:
            self._running = False

        # Wait for event loop thread to finish
        if self.event_loop_thread and self.event_loop_thread.is_alive():
            self.event_loop_thread.join(timeout=5.0)

        # Mark as completed
        with self.job_state._status_lock:
            if self.job_state.status not in (
                ExecutionStatus.FAILED,
                ExecutionStatus.CANCELLED,
            ):
                self.job_state.status = ExecutionStatus.COMPLETED
                self.job_state.completed_at = datetime.now()

                # Record execution end
                if self.execution_tracker:
                    # Find any routine that was executed
                    for routine_id in self.flow.routines.keys():
                        routine_state = self.job_state.get_routine_state(routine_id)
                        if routine_state:
                            self.execution_tracker.record_routine_end(
                                routine_id, "completed"
                            )
                            break

                try:
                    execution_hooks.on_flow_end(self.flow, self.job_state, "completed")
                except Exception as e:
                    # Hook exceptions should not crash Runtime
                    logger.warning(f"Exception in on_flow_end hook: {e}", exc_info=True)
                logger.debug(f"Job {self.job_state.job_id} completed by user")

                # Mark as completed in registry for cleanup tracking
                try:
                    from routilux.monitoring.job_registry import JobRegistry

                    registry = JobRegistry.get_instance()
                    registry.mark_completed(self.job_state.job_id)
                except Exception:
                    # Ignore errors in registry marking
                    pass

        # Cleanup
        self._cleanup()

    def _handle_timeout(self) -> None:
        """Handle job timeout."""
        from routilux.monitoring.hooks import execution_hooks
        from routilux.status import ExecutionStatus

        self.job_state.status = ExecutionStatus.FAILED
        # Set completed_at timestamp
        self.job_state.completed_at = datetime.now()
        self.job_state.error = f"Job timed out after {self.timeout}s"
        self.job_state.shared_data["error"] = f"Job timed out after {self.timeout}s"

        # Record execution end
        if self.execution_tracker:
            entry_routine_id = self.job_state.current_routine_id
            if entry_routine_id:
                self.execution_tracker.record_routine_end(
                    entry_routine_id, "failed", error=f"Timeout after {self.timeout}s"
                )

        try:
            execution_hooks.on_flow_end(self.flow, self.job_state, "failed")
        except Exception as e:
            # Hook exceptions should not crash Runtime
            logger.warning(f"Exception in on_flow_end hook: {e}", exc_info=True)
        logger.warning(f"Job {self.job_state.job_id} failed due to timeout")

    def _handle_error(self, error: Exception) -> None:
        """Handle job error.

        Args:
            error: Exception that occurred.
        """
        from routilux.monitoring.hooks import execution_hooks
        from routilux.status import ExecutionStatus

        self.job_state.status = ExecutionStatus.FAILED
        # Set completed_at timestamp
        self.job_state.completed_at = datetime.now()
        if "error" not in self.job_state.shared_data:
            self.job_state.shared_data["error"] = str(error)
        self.job_state.error = str(error)

        # Record execution end
        if self.execution_tracker:
            entry_routine_id = self.job_state.current_routine_id
            if entry_routine_id:
                self.execution_tracker.record_routine_end(
                    entry_routine_id, "failed", error=str(error)
                )

        try:
            execution_hooks.on_flow_end(self.flow, self.job_state, "failed")
        except Exception as e:
            # Hook exceptions should not crash Runtime
            logger.warning(f"Exception in on_flow_end hook: {e}", exc_info=True)
        logger.error(f"Job {self.job_state.job_id} failed with error: {error}")

    def _cleanup(self) -> None:
        """Cleanup job executor."""
        # CRITICAL fix: Acquire lock before modifying _running flag
        with self._lock:
            self._running = False

        # Remove from global job manager
        from routilux.job_manager import get_job_manager

        job_manager = get_job_manager()
        job_manager.remove_job(self.job_state.job_id)

        logger.debug(f"Cleaned up job {self.job_state.job_id}")

    def pause(self, reason: str = "", checkpoint: dict[str, Any] | None = None) -> None:
        """Pause job execution.

        Args:
            reason: Reason for pausing.
            checkpoint: Optional checkpoint data.
        """
        from routilux.flow.job_state_management import pause_job_executor

        pause_job_executor(self, reason, checkpoint)

    def resume(self) -> "JobState":
        """Resume job execution.

        Returns:
            Updated JobState.
        """
        from routilux.flow.job_state_management import resume_job_executor

        return resume_job_executor(self)

    def cancel(self, reason: str = "") -> None:
        """Cancel job execution.

        Args:
            reason: Reason for cancellation.
        """
        from routilux.flow.job_state_management import cancel_job_executor

        cancel_job_executor(self, reason)

    def is_running(self) -> bool:
        """Check if job is running.

        Returns:
            True if running, False otherwise.
        """
        return self._running and not self._paused

    def is_paused(self) -> bool:
        """Check if job is paused.

        Returns:
            True if paused, False otherwise.
        """
        return self._paused

    def stop(self) -> None:
        """Stop job execution.

        This immediately stops the event loop and cleans up resources.
        """
        # CRITICAL fix: Acquire lock before modifying _running flag
        with self._lock:
            self._running = False

        # Cancel active tasks
        with self._lock:
            for future in list(self.active_tasks):
                if not future.done():
                    future.cancel()
            self.active_tasks.clear()

        # Wait for event loop thread
        if self.event_loop_thread and self.event_loop_thread.is_alive():
            self.event_loop_thread.join(timeout=1.0)

        logger.debug(f"Stopped job {self.job_state.job_id}")

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for job to complete.

        Args:
            timeout: Maximum time to wait in seconds. None for infinite wait.

        Returns:
            True if job completed, False if timeout.
        """
        if self.event_loop_thread is None:
            return True

        self.event_loop_thread.join(timeout=timeout)
        return not self.event_loop_thread.is_alive()
