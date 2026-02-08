"""Protocol-based interfaces for breaking circular dependencies.

This module defines Protocol interfaces that allow modules to depend on
abstractions rather than concrete implementations, following the
Dependency Inversion Principle (SOLID).

The key insight: Python's structural typing means any class with the
right methods satisfies the Protocol, regardless of inheritance.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from routilux.core.event import Event
    from routilux.core.worker import WorkerState


class IEventRouter(Protocol):
    """Something that can route events to slots.

    This is implemented by Flow (has connections) and Runtime (does routing).
    """

    def get_connections_for_event(self, event: Event) -> list[Any]:
        """Get all connections for a given event."""
        ...

    def get_routine(self, routine_id: str) -> Any:
        """Get a routine by ID."""
        ...


class IRoutineExecutor(Protocol):
    """Something that can execute routine tasks."""

    def enqueue_task(self, task: Any) -> None:
        """Add a task to the execution queue."""
        ...


class IEventHandler(Protocol):
    """Something that can handle emitted events."""

    def handle_event_emit(
        self, event: Event, event_data: dict[str, Any], worker_state: WorkerState
    ) -> None:
        """Process an emitted event."""
        ...
