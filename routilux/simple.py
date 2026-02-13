"""
Routilux simplified API for quick workflow creation.

This module provides a minimal API surface for common use cases,
reducing the number of concepts users need to learn.

Key features:
- One-liner pipeline creation
- Simple execution and result retrieval
- Minimal boilerplate
"""

from __future__ import annotations

import threading
from typing import Any, Callable

from routilux.core.flow import Flow
from routilux.core.runtime import Runtime


def pipeline(*functions: Callable[..., Any]) -> Flow:
    """Create a pipeline flow from a sequence of functions.

    Each function becomes a routine in the pipeline, connected in order.
    Functions should accept one argument and return one value.

    Args:
        *functions: Functions to chain together

    Returns:
        A Flow ready for execution

    Examples:
        Simple pipeline:

        >>> from routilux.simple import pipeline, run_sync
        >>>
        >>> def validate(data):
        ...     if not data.get("name"):
        ...         raise ValueError("name required")
        ...     return data
        >>>
        >>> def transform(data):
        ...     return {"processed": data["name"].upper()}
        >>>
        >>> def save(data):
        ...     print(f"Saving: {data}")
        ...     return {"status": "saved", "data": data}
        >>>
        >>> flow = pipeline(validate, transform, save)
        >>> result = run_sync(flow, {"name": "test"})
        >>> print(result)
        {'status': 'saved', 'data': {'processed': 'TEST'}}

        Using with lambdas:

        >>> flow = pipeline(
        ...     lambda x: x * 2,
        ...     lambda x: x + 10,
        ...     lambda x: {"result": x}
        ... )

    Note:
        Functions are connected using default "input" slot and "output" event.
        For more control, use the @routine decorator and Flow.pipe() directly.
    """
    if not functions:
        raise ValueError("At least one function is required")

    from routilux.decorators import routine

    flow = Flow("simple_pipeline")
    prev_id = None

    for i, func in enumerate(functions):
        # Create a routine from the function
        routine_class = routine(name=func.__name__ or f"step_{i}")(func)
        routine_instance = routine_class()

        # Generate ID
        routine_id = func.__name__ if func.__name__ != "<lambda>" else f"step_{i}"

        # Add to flow
        flow.add_routine(routine_instance, routine_id)

        # Connect to previous
        if prev_id is not None:
            flow.connect(prev_id, "output", routine_id, "input")

        prev_id = routine_id

    return flow


def run_sync(flow: Flow, data: Any, timeout: float = 30.0) -> Any:
    """Run a flow synchronously and return the final result.

    This is a convenience function that creates a runtime, executes
    the flow with the given data, and collects the final output.

    Args:
        flow: Flow to execute
        data: Input data to feed into the first routine
        timeout: Maximum execution time in seconds (default: 30)

    Returns:
        The result from the final routine's output event

    Raises:
        TimeoutError: If execution exceeds timeout
        RuntimeError: If flow has no routines or no output

    Examples:
        >>> from routilux.simple import pipeline, run_sync
        >>>
        >>> flow = pipeline(
        ...     lambda x: x * 2,
        ...     lambda x: x + 10
        ... )
        >>> result = run_sync(flow, 5)
        >>> print(result)
        20

    Note:
        This function is designed for simple, linear pipelines.
        For complex flows with multiple outputs, use Runtime directly.
    """
    if not flow.routines:
        raise RuntimeError("Flow has no routines")

    # Find the first routine (entry point)
    first_routine_id = list(flow.routines.keys())[0]
    first_routine = flow.routines[first_routine_id]

    # Check for input slot
    if not first_routine.slots:
        raise RuntimeError(f"First routine '{first_routine_id}' has no input slots")

    first_slot_name = list(first_routine.slots.keys())[0]

    # Result storage
    result_holder: dict[str, Any] = {"result": None, "done": threading.Event()}

    def collect_result(**kwargs: Any) -> None:
        """Callback to collect the final result."""
        result_holder["result"] = kwargs.get("result")
        result_holder["done"].set()

    # Create runtime
    runtime = Runtime()
    runtime.register_flow(flow)

    # Post the job
    worker_state, job_context = runtime.post(
        flow_id=flow.flow_id,
        routine_id=first_routine_id,
        slot_name=first_slot_name,
        data=data,
    )

    # Wait for completion
    if not result_holder["done"].wait(timeout=timeout):
        raise TimeoutError(f"Flow execution timed out after {timeout} seconds")

    # Get result from job output or worker state
    # Try to get the last routine's output
    from routilux.core.context import get_job_output

    job_output = get_job_output(job_context.job_id)
    if job_output:
        # Get the last output
        lines = job_output.strip().split("\n")
        if lines:
            result_holder["result"] = lines[-1]

    # If we couldn't get output, try reading from job data
    if result_holder["result"] is None:
        result_holder["result"] = job_context.get_data("result")

    return result_holder["result"]


def run_async(flow: Flow, data: Any, callback: Callable[[Any], None] | None = None) -> str:
    """Run a flow asynchronously.

    This function starts flow execution and returns immediately.
    Use callback to handle the result when execution completes.

    Args:
        flow: Flow to execute
        data: Input data
        callback: Optional callback function for result

    Returns:
        Job ID for tracking

    Examples:
        >>> from routilux.simple import pipeline, run_async
        >>>
        >>> def on_complete(result):
        ...     print(f"Done: {result}")
        >>>
        >>> flow = pipeline(lambda x: x * 2)
        >>> job_id = run_async(flow, 5, callback=on_complete)
    """
    if not flow.routines:
        raise RuntimeError("Flow has no routines")

    # Find the first routine (entry point)
    first_routine_id = list(flow.routines.keys())[0]
    first_routine = flow.routines[first_routine_id]

    # Check for input slot
    if not first_routine.slots:
        raise RuntimeError(f"First routine '{first_routine_id}' has no input slots")

    first_slot_name = list(first_routine.slots.keys())[0]

    # Create runtime
    runtime = Runtime()
    runtime.register_flow(flow)

    # Post the job
    worker_state, job_context = runtime.post(
        flow_id=flow.flow_id,
        routine_id=first_routine_id,
        slot_name=first_slot_name,
        data=data,
    )

    # If callback provided, set up result collection
    if callback:

        def wait_and_callback() -> None:
            """Wait for execution and call callback."""
            # Wait for worker to complete
            import time

            max_wait = 30.0
            start = time.time()
            while time.time() - start < max_wait:
                # Check if worker has finished processing
                if hasattr(worker_state, "history") and worker_state.history:
                    # Get result from job
                    result = job_context.get_data("result")
                    callback(result)
                    return
                time.sleep(0.1)

        thread = threading.Thread(target=wait_and_callback, daemon=True)
        thread.start()

    return job_context.job_id


# Convenience exports
__all__ = [
    "pipeline",
    "run_sync",
    "run_async",
]
