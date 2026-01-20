"""
Execution hooks interface for Routilux.

Defines abstract hook interface for execution lifecycle events.
Core module defines the interface, monitoring module provides implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from routilux.core.context import JobContext
    from routilux.core.event import Event
    from routilux.core.flow import Flow
    from routilux.core.slot import Slot
    from routilux.core.worker import WorkerState


class ExecutionHooksInterface(ABC):
    """Abstract interface for execution lifecycle hooks.

    Core module defines this interface, monitoring module provides implementation.
    If no implementation is registered, NullExecutionHooks is used (no-op).

    Hook Methods:
        - on_worker_start: Worker begins execution
        - on_worker_stop: Worker stops execution
        - on_job_start: Job begins processing
        - on_job_end: Job finishes processing
        - on_routine_start: Routine begins execution
        - on_routine_end: Routine finishes execution
        - on_event_emit: Event is emitted
        - on_slot_before_enqueue: Before data is enqueued to a slot
    """

    @abstractmethod
    def on_worker_start(self, flow: Flow, worker_state: WorkerState) -> None:
        """Called when a worker starts execution.

        Args:
            flow: Flow being executed
            worker_state: Worker state
        """
        pass

    @abstractmethod
    def on_worker_stop(self, flow: Flow, worker_state: WorkerState, status: str) -> None:
        """Called when a worker stops execution.

        Args:
            flow: Flow being executed
            worker_state: Worker state
            status: Final status ("completed", "failed", "cancelled")
        """
        pass

    @abstractmethod
    def on_job_start(self, job_context: JobContext, worker_state: WorkerState) -> None:
        """Called when a job starts processing.

        Args:
            job_context: Job context
            worker_state: Worker state
        """
        pass

    @abstractmethod
    def on_job_end(
        self,
        job_context: JobContext,
        worker_state: WorkerState,
        status: str = "completed",
        error: Exception | None = None,
    ) -> None:
        """Called when a job finishes processing.

        Args:
            job_context: Job context
            worker_state: Worker state
            status: Final status ("completed", "failed")
            error: Error if failed
        """
        pass

    @abstractmethod
    def on_routine_start(
        self,
        routine_id: str,
        worker_state: WorkerState,
        job_context: JobContext | None = None,
    ) -> bool:
        """Called when a routine starts execution.

        Args:
            routine_id: Routine identifier
            worker_state: Worker state
            job_context: Optional job context

        Returns:
            True to continue execution, False to pause (e.g., breakpoint)
        """
        return True

    @abstractmethod
    def on_routine_end(
        self,
        routine_id: str,
        worker_state: WorkerState,
        job_context: JobContext | None = None,
        status: str = "completed",
        error: Exception | None = None,
    ) -> None:
        """Called when a routine finishes execution.

        Args:
            routine_id: Routine identifier
            worker_state: Worker state
            job_context: Optional job context
            status: Final status
            error: Error if failed
        """
        pass

    @abstractmethod
    def on_event_emit(
        self,
        event: Event,
        source_routine_id: str,
        worker_state: WorkerState,
        job_context: JobContext | None = None,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Called when an event is emitted.

        Args:
            event: Event being emitted
            source_routine_id: Source routine ID
            worker_state: Worker state
            job_context: Optional job context
            data: Event data

        Returns:
            True to continue propagation, False to block
        """
        return True

    @abstractmethod
    def on_slot_before_enqueue(
        self,
        slot: Slot,
        routine_id: str,
        job_context: JobContext | None,
        data: dict[str, Any],
        flow_id: str,
    ) -> tuple[bool, str | None]:
        """Called before enqueueing data to a slot.

        This hook allows intercepting slot enqueue operations, for example
        to implement breakpoints or data validation.

        Args:
            slot: Slot that will receive the data
            routine_id: ID of the routine that owns the slot
            job_context: Current job context (may be None)
            data: Data dictionary that will be enqueued
            flow_id: ID of the flow containing the routine

        Returns:
            Tuple of (should_enqueue, reason):
            - should_enqueue: True to proceed with enqueue, False to skip
            - reason: Optional reason string if enqueue is skipped (for logging)

        Examples:
            >>> hooks = get_execution_hooks()
            >>> should_enqueue, reason = hooks.on_slot_before_enqueue(
            ...     slot, "routine_1", job_context, {"key": "value"}, "flow_1"
            ... )
            >>> if not should_enqueue:
            ...     logger.info(f"Skipping enqueue: {reason}")
        """
        return True, None


class NullExecutionHooks(ExecutionHooksInterface):
    """Null implementation of execution hooks (no-op).

    Used when no monitoring is enabled. All methods do nothing.
    """

    def on_worker_start(self, flow: Flow, worker_state: WorkerState) -> None:
        pass

    def on_worker_stop(self, flow: Flow, worker_state: WorkerState, status: str) -> None:
        pass

    def on_job_start(self, job_context: JobContext, worker_state: WorkerState) -> None:
        pass

    def on_job_end(
        self,
        job_context: JobContext,
        worker_state: WorkerState,
        status: str = "completed",
        error: Exception | None = None,
    ) -> None:
        pass

    def on_routine_start(
        self,
        routine_id: str,
        worker_state: WorkerState,
        job_context: JobContext | None = None,
    ) -> bool:
        return True

    def on_routine_end(
        self,
        routine_id: str,
        worker_state: WorkerState,
        job_context: JobContext | None = None,
        status: str = "completed",
        error: Exception | None = None,
    ) -> None:
        pass

    def on_event_emit(
        self,
        event: Event,
        source_routine_id: str,
        worker_state: WorkerState,
        job_context: JobContext | None = None,
        data: dict[str, Any] | None = None,
    ) -> bool:
        return True

    def on_slot_before_enqueue(
        self,
        slot: Slot,
        routine_id: str,
        job_context: JobContext | None,
        data: dict[str, Any],
        flow_id: str,
    ) -> tuple[bool, str | None]:
        """Null implementation - always allows enqueue."""
        return True, None


# Global hooks instance (default: null implementation)
_execution_hooks: ExecutionHooksInterface = NullExecutionHooks()


def get_execution_hooks() -> ExecutionHooksInterface:
    """Get the current execution hooks instance.

    Returns:
        Current ExecutionHooksInterface implementation
    """
    return _execution_hooks


def set_execution_hooks(hooks: ExecutionHooksInterface) -> None:
    """Set the execution hooks instance.

    Called by monitoring module when enabling monitoring.

    Args:
        hooks: ExecutionHooksInterface implementation
    """
    global _execution_hooks
    _execution_hooks = hooks


def reset_execution_hooks() -> None:
    """Reset execution hooks to null implementation.

    Useful for testing or disabling monitoring.
    """
    global _execution_hooks
    _execution_hooks = NullExecutionHooks()
