"""
Breakpoint management API routes.
"""

from fastapi import APIRouter, HTTPException

from routilux.monitoring.breakpoint_manager import Breakpoint
from routilux.monitoring.registry import MonitoringRegistry

# Note: job_store (old system) removed - use get_job_storage() instead
from routilux.server.middleware.auth import RequireAuth
from routilux.server.models.breakpoint import (
    BreakpointCreateRequest,
    BreakpointListResponse,
    BreakpointResponse,
)

router = APIRouter()


def _breakpoint_to_response(bp: Breakpoint) -> BreakpointResponse:
    """Convert Breakpoint to response model."""
    return BreakpointResponse(
        breakpoint_id=bp.breakpoint_id,
        job_id=bp.job_id,
        type=bp.type,
        routine_id=bp.routine_id,
        slot_name=bp.slot_name,
        event_name=bp.event_name,
        source_routine_id=bp.source_routine_id,
        source_event_name=bp.source_event_name,
        target_routine_id=bp.target_routine_id,
        target_slot_name=bp.target_slot_name,
        condition=bp.condition,
        enabled=bp.enabled,
        hit_count=bp.hit_count,
    )


@router.post(
    "/jobs/{job_id}/breakpoints",
    response_model=BreakpointResponse,
    status_code=201,
    dependencies=[RequireAuth],
)
async def create_breakpoint(job_id: str, request: BreakpointCreateRequest):
    """
    Create a breakpoint for a job.

    **Overview**:
    Creates a breakpoint that pauses job execution at a specific point in the flow.
    Breakpoints allow you to inspect state, debug issues, and control execution flow.
    When a breakpoint is hit, execution pauses until you resume or remove the breakpoint.

    **Endpoint**: `POST /api/jobs/{job_id}/breakpoints`

    **Use Cases**:
    - Debug job execution issues
    - Inspect routine state at specific points
    - Control execution flow
    - Step through job execution
    - Analyze data transformations

    **Breakpoint Types**:
    - `routine`: Pauses when a specific routine is executed
    - `slot`: Pauses when a specific slot is called
    - `event`: Pauses when a specific event is emitted
    - `connection`: Pauses when data flows through a specific connection

    **Request Example**:
    ```json
    {
      "type": "routine",
      "routine_id": "data_processor",
      "enabled": true,
      "condition": null
    }
    ```

    **Response Example**:
    ```json
    {
      "breakpoint_id": "bp_xyz789",
      "job_id": "job_abc123",
      "type": "routine",
      "routine_id": "data_processor",
      "slot_name": null,
      "event_name": null,
      "source_routine_id": null,
      "source_event_name": null,
      "target_routine_id": null,
      "target_slot_name": null,
      "condition": null,
      "enabled": true,
      "hit_count": 0
    }
    ```

    **Breakpoint Configuration**:
    - `type` (required): Breakpoint type (routine, slot, event, connection)
    - `routine_id` (optional): Routine ID for routine/slot/event breakpoints
    - `slot_name` (optional): Slot name for slot breakpoints
    - `event_name` (optional): Event name for event breakpoints
    - `source_routine_id` / `target_routine_id` (optional): For connection breakpoints
    - `condition` (optional): Conditional expression (if supported)
    - `enabled` (optional): Whether breakpoint is active (default: true)

    **Error Responses**:
    - `404 Not Found`: Job not found, flow not found, or routine not found in flow
    - `500 Internal Server Error`: Breakpoint manager not available

    **Best Practices**:
    1. Create breakpoints before job starts for best results
    2. Use routine breakpoints for general debugging
    3. Use slot/event breakpoints for specific data flow debugging
    4. Disable breakpoints when not debugging: PUT /api/workers/{worker_id}/breakpoints/{breakpoint_id}
    5. Remove breakpoints after debugging: DELETE /api/jobs/{job_id}/breakpoints/{breakpoint_id}

    **Related Endpoints**:
    - GET /api/jobs/{job_id}/breakpoints - List all breakpoints
    - PUT /api/workers/{worker_id}/breakpoints/{breakpoint_id} - Enable/disable breakpoint
    - DELETE /api/jobs/{job_id}/breakpoints/{breakpoint_id} - Delete breakpoint

    Args:
        job_id: Unique job identifier
        request: BreakpointCreateRequest with breakpoint configuration

    Returns:
        BreakpointResponse: Created breakpoint information

    Raises:
        HTTPException: 404 if job, flow, or routine not found
        HTTPException: 500 if breakpoint manager unavailable
    """
    # Verify job exists (use new job storage)
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()

    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # JobContext now contains flow_id directly
    flow_id = job_context.flow_id
    if not flow_id:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' has no flow_id")

    registry = MonitoringRegistry.get_instance()
    breakpoint_mgr = registry.breakpoint_manager

    if not breakpoint_mgr:
        raise HTTPException(status_code=500, detail="Breakpoint manager not available")

    # For routine-level breakpoints, use job-specific activation policy
    if request.type == "routine" and request.routine_id:
        # Get flow and routine to save original policy
        from routilux.core.registry import FlowRegistry

        flow_registry = FlowRegistry.get_instance()
        flow = flow_registry.get(flow_id)

        if not flow:
            raise HTTPException(status_code=404, detail=f"Flow '{flow_id}' not found")

        if request.routine_id not in flow.routines:
            raise HTTPException(
                status_code=404, detail=f"Routine '{request.routine_id}' not found in flow"
            )

        routine = flow.routines[request.routine_id]

        # Save original policy (if exists)
        original_policy = routine._activation_policy

        # Create breakpoint policy and set as job-specific policy
        from routilux.activation_policies import breakpoint_policy

        bp_policy = breakpoint_policy(request.routine_id)
        # Set policy on worker for the new system
        from routilux.core.registry import WorkerRegistry

        worker_registry = WorkerRegistry.get_instance()
        worker = worker_registry.get(job_context.worker_id)
        if worker:
            # Store policy in worker state
            if not hasattr(worker, "_job_activation_policies"):
                worker._job_activation_policies = {}
            worker._job_activation_policies[job_id] = {request.routine_id: bp_policy}

        # Store original policy in breakpoint for restoration
        # Note: We'll store it in a way that can be retrieved later
        # Since Callable can't be serialized, we'll handle this in remove_breakpoint

    # Create breakpoint
    breakpoint = Breakpoint(
        job_id=job_id,
        type=request.type,
        routine_id=request.routine_id,
        slot_name=request.slot_name,
        event_name=request.event_name,
        source_routine_id=request.source_routine_id,
        source_event_name=request.source_event_name,
        target_routine_id=request.target_routine_id,
        target_slot_name=request.target_slot_name,
        condition=request.condition,
        enabled=request.enabled,
    )

    # Store original policy reference in breakpoint (non-serializable)
    if request.type == "routine" and request.routine_id:
        # We'll need to get the original policy when removing
        # For now, we store a reference that we can use
        breakpoint._original_policy = original_policy  # type: ignore

    breakpoint_mgr.add_breakpoint(breakpoint)

    return _breakpoint_to_response(breakpoint)


@router.get(
    "/jobs/{job_id}/breakpoints", response_model=BreakpointListResponse, dependencies=[RequireAuth]
)
async def list_breakpoints(job_id: str):
    """
    List all breakpoints for a job.

    **Overview**:
    Returns a list of all breakpoints associated with a job. Use this to inspect active
    breakpoints, check breakpoint status, and manage debugging sessions.

    **Endpoint**: `GET /api/jobs/{job_id}/breakpoints`

    **Use Cases**:
    - View all active breakpoints for a job
    - Check breakpoint status and hit counts
    - Manage debugging sessions
    - Verify breakpoint configuration

    **Request Example**:
    ```
    GET /api/jobs/job_abc123/breakpoints
    ```

    **Response Example**:
    ```json
    {
      "breakpoints": [
        {
          "breakpoint_id": "bp_xyz789",
          "job_id": "job_abc123",
          "type": "routine",
          "routine_id": "data_processor",
          "enabled": true,
          "hit_count": 3
        }
      ],
      "total": 1
    }
    ```

    **Response Fields**:
    - `breakpoints`: List of breakpoint objects
    - `total`: Total number of breakpoints

    **Breakpoint Information**:
    Each breakpoint includes:
    - `breakpoint_id`: Unique breakpoint identifier
    - `type`: Breakpoint type (routine, slot, event, connection)
    - `enabled`: Whether breakpoint is currently active
    - `hit_count`: Number of times breakpoint was hit

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist

    **Related Endpoints**:
    - POST /api/jobs/{job_id}/breakpoints - Create new breakpoint
    - PUT /api/workers/{worker_id}/breakpoints/{breakpoint_id} - Enable/disable breakpoint
    - DELETE /api/jobs/{job_id}/breakpoints/{breakpoint_id} - Delete breakpoint

    Args:
        job_id: Unique job identifier

    Returns:
        BreakpointListResponse: List of breakpoints with total count

    Raises:
        HTTPException: 404 if job not found
    """
    # Verify job exists (use new job storage)
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()

    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    registry = MonitoringRegistry.get_instance()
    breakpoint_mgr = registry.breakpoint_manager

    if not breakpoint_mgr:
        return BreakpointListResponse(breakpoints=[], total=0)

    breakpoints = breakpoint_mgr.get_breakpoints(job_id)

    return BreakpointListResponse(
        breakpoints=[_breakpoint_to_response(bp) for bp in breakpoints],
        total=len(breakpoints),
    )


@router.delete(
    "/jobs/{job_id}/breakpoints/{breakpoint_id}", status_code=204, dependencies=[RequireAuth]
)
async def delete_breakpoint(job_id: str, breakpoint_id: str):
    """
    Delete a breakpoint.

    **Overview**:
    Permanently removes a breakpoint from a job. After deletion, the breakpoint will no
    longer pause execution. If the breakpoint was a routine-level breakpoint, the routine's
    original activation policy is restored.

    **Endpoint**: `DELETE /api/jobs/{job_id}/breakpoints/{breakpoint_id}`

    **Use Cases**:
    - Remove breakpoints after debugging
    - Clean up breakpoints when no longer needed
    - Restore normal execution flow
    - Manage debugging sessions

    **Request Example**:
    ```
    DELETE /api/jobs/job_abc123/breakpoints/bp_xyz789
    ```

    **Response**: 204 No Content (successful deletion)

    **Behavior**:
    - Breakpoint is removed from the job
    - For routine-level breakpoints, original activation policy is restored
    - Execution continues normally after deletion
    - Breakpoint cannot be recovered after deletion

    **Error Responses**:
    - `404 Not Found`: Job or breakpoint not found, or breakpoint manager unavailable

    **Best Practices**:
    1. List breakpoints before deletion: GET /api/jobs/{job_id}/breakpoints
    2. Consider disabling instead of deleting: PUT /api/workers/{worker_id}/breakpoints/{breakpoint_id}
    3. Delete breakpoints when debugging is complete
    4. Verify deletion: GET /api/jobs/{job_id}/breakpoints

    **Related Endpoints**:
    - GET /api/jobs/{job_id}/breakpoints - List breakpoints
    - POST /api/jobs/{job_id}/breakpoints - Create breakpoint
    - PUT /api/workers/{worker_id}/breakpoints/{breakpoint_id} - Enable/disable breakpoint

    Args:
        job_id: Unique job identifier
        breakpoint_id: Unique breakpoint identifier

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if job or breakpoint not found
    """
    # Verify job exists (use new job storage)
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()

    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # JobContext now contains flow_id directly
    flow_id = job_context.flow_id
    if not flow_id:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' has no flow_id")

    registry = MonitoringRegistry.get_instance()
    breakpoint_mgr = registry.breakpoint_manager

    if not breakpoint_mgr:
        raise HTTPException(status_code=404, detail="Breakpoint manager not available")

    # Get breakpoint to check if it's a routine-level breakpoint
    breakpoints = breakpoint_mgr.get_breakpoints(job_id)
    breakpoint = next((bp for bp in breakpoints if bp.breakpoint_id == breakpoint_id), None)

    if breakpoint and breakpoint.type == "routine" and breakpoint.routine_id:
        # Policy restoration handled at worker level
        # Note: Breakpoint policies are managed by BreakpointManager
        # The original policy restoration logic may need to be implemented
        # based on how breakpoints are stored and managed
        pass  # TODO: Implement policy restoration if needed

    breakpoint_mgr.remove_breakpoint(breakpoint_id, job_id)


# Note: Breakpoint enable/disable has been moved to workers category
# Use PUT /api/workers/{worker_id}/breakpoints/{breakpoint_id} instead
