"""
Job management API routes.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from routilux.server.middleware.auth import RequireAuth
from routilux.server.models.job import JobListResponse, JobResponse, JobStartRequest, PostToJobRequest
from routilux.server.validators import validate_flow_exists
from routilux.job_state import JobState
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.monitoring.storage import flow_store, job_store
from routilux.runtime import get_runtime_instance
from routilux.status import ExecutionStatus

logger = logging.getLogger(__name__)

router = APIRouter()


def _job_to_response(job_state: JobState) -> JobResponse:
    """Convert JobState to response model."""

    def dt_to_int(dt: Optional[datetime]) -> Optional[int]:
        if dt is None:
            return None
        return int(dt.timestamp())

    # Extract error from job_state.error or execution history
    error = None
    if hasattr(job_state, "error") and job_state.error:
        error = job_state.error
    elif job_state.status in (ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
        # Try to extract from execution history
        for record in reversed(job_state.execution_history):
            if hasattr(record, "error") and record.error:
                error = record.error
                break
        # Fall back to shared_data
        if not error:
            error = job_state.shared_data.get("error")

    return JobResponse(
        job_id=job_state.job_id,
        flow_id=job_state.flow_id,
        status=job_state.status.value
        if hasattr(job_state.status, "value")
        else str(job_state.status),
        created_at=dt_to_int(getattr(job_state, "created_at", datetime.now())),
        started_at=dt_to_int(getattr(job_state, "started_at", None)),
        completed_at=dt_to_int(getattr(job_state, "completed_at", None)),
        error=error,
    )


@router.post("/jobs", response_model=JobResponse, status_code=201, dependencies=[RequireAuth])
async def start_job(request: JobStartRequest):
    """Start a new job execution from a flow.

    **Overview**:
    This endpoint creates a new job and starts executing the specified flow asynchronously.
    The endpoint returns immediately with a job_id - execution happens in the background.
    All routines in the flow start in IDLE state, waiting for external data via the post endpoint.

    **Execution Model**:
    - Job is created with status PENDING
    - Job immediately transitions to RUNNING
    - All routines start in IDLE state (waiting for data)
    - Use POST /api/jobs/{job_id}/post to send data to routine slots
    - Job will transition to COMPLETED when all routines are idle and no more work is pending
    - Use POST /api/jobs/{job_id}/complete to manually mark job as complete

    **Request Example**:
    ```json
    {
      "flow_id": "data_processing_flow",
      "runtime_id": "production",
      "timeout": 3600.0
    }
    ```

    **Response Example**:
    ```json
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "flow_id": "data_processing_flow",
      "status": "running",
      "created_at": 1705312800,
      "started_at": 1705312801,
      "completed_at": null,
      "error": null
    }
    ```

    **Error Responses**:
    - `400 Bad Request`: Flow not found, invalid timeout, or execution failed to start
    - `422 Validation Error`: Invalid request parameters

    **Usage Flow**:
    1. Create/select a flow: GET /api/flows or POST /api/flows
    2. Start job: POST /api/jobs (this endpoint)
    3. Send data to routines: POST /api/jobs/{job_id}/post
    4. Monitor progress: GET /api/jobs/{job_id}/status or GET /api/jobs/{job_id}/monitoring
    5. Complete job: POST /api/jobs/{job_id}/complete (when done)

    **Runtime Selection**:
    - If `runtime_id` is provided, the specified runtime will be used
    - If `runtime_id` is not provided, the default runtime will be used
    - Use GET /api/runtimes to see available runtimes

    **Timeout Behavior**:
    - If timeout is reached, job is automatically cancelled
    - Timeout applies to the entire job execution
    - Maximum timeout: 86400 seconds (24 hours)

    Args:
        request: JobStartRequest containing flow_id, optional runtime_id, and optional timeout

    Returns:
        JobResponse: Job details including job_id, flow_id, and initial status

    Raises:
        HTTPException: 400 if flow not found or execution failed
        HTTPException: 422 if request validation fails
    """
    # Validate flow exists
    flow = validate_flow_exists(request.flow_id)

    # Create job state immediately (before execution)
    job_state = JobState(flow.flow_id)

    # Store job immediately so it can be queried
    job_store.add(job_state)

    # Ensure flow is registered in FlowRegistry (required for Runtime)
    flow_registry = FlowRegistry.get_instance()
    if not flow_registry.get(flow.flow_id) and not flow_registry.get_by_name(flow.flow_id):
        # Register flow (register() takes only the flow as argument)
        flow_registry.register(flow)
        if hasattr(flow, "name") and flow.name:
            flow_registry.register_by_name(flow.name, flow)

    # Get Runtime from registry based on runtime_id
    from routilux.monitoring.runtime_registry import RuntimeRegistry
    
    runtime_registry = RuntimeRegistry.get_instance()
    
    # If no runtime_id specified, use default runtime (create if needed)
    if request.runtime_id is None:
        runtime = runtime_registry.get_or_create_default()
    else:
        # Get specified runtime
        runtime = runtime_registry.get(request.runtime_id)
        if runtime is None:
            raise HTTPException(
                status_code=404,
                detail=f"Runtime '{request.runtime_id}' not found. Use GET /api/runtimes to see available runtimes."
            )

    # Start flow execution asynchronously using Runtime.exec()
    # This returns immediately without blocking
    try:
        # Execute via Runtime
        started_job_state = runtime.exec(
            flow_name=flow.flow_id,  # Use flow_id as flow_name
            job_state=job_state,
        )

        # Update stored job with the started state
        job_store.add(started_job_state)

        return _job_to_response(started_job_state)
    except Exception as e:
        # If exec() fails, mark job as failed
        job_state.status = ExecutionStatus.FAILED
        job_state.shared_data["error"] = str(e)
        job_store.add(job_state)
        raise HTTPException(status_code=400, detail=f"Failed to start job: {str(e)}") from e


@router.get(
    "/jobs",
    response_model=JobListResponse,
    summary="List all jobs",
    description="Retrieve a paginated list of jobs with optional filters",
    dependencies=[RequireAuth],
)
async def list_jobs(
    flow_id: Optional[str] = Query(
        None,
        description="Filter jobs by flow ID. Only jobs executing this flow will be returned. "
        "Example: 'data_processing_flow'. Leave empty to get jobs from all flows.",
        example="data_processing_flow",
    ),
    status: Optional[str] = Query(
        None,
        description="Filter jobs by execution status. Valid values: "
        "'pending', 'running', 'idle', 'completed', 'failed', 'paused', 'cancelled'. "
        "Case-sensitive. Leave empty to get jobs with any status.",
        example="running",
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of jobs to return in this response. "
        "Range: 1-1000. Default: 100. Use this for pagination.",
        example=100,
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of jobs to skip before returning results. "
        "Use this for pagination: offset = (page - 1) * limit. "
        "Example: Page 1 (offset=0), Page 2 (offset=100), Page 3 (offset=200).",
        example=0,
    ),
):
    """List jobs with optional filters and pagination.

    **Overview**:
    Returns a paginated list of jobs that match the specified filter criteria.
    The response includes total count for building pagination UI.

    **Filtering**:
    - **By Flow**: Use `flow_id` to get only jobs for a specific flow
    - **By Status**: Use `status` to get only jobs in a specific state
    - **Combined**: You can use both filters together

    **Pagination**:
    - Use `limit` to control page size (1-1000, default 100)
    - Use `offset` to skip jobs (for pagination)
    - Response includes `total` count for calculating total pages

    **Request Examples**:
    ```
    # Get all jobs (first page)
    GET /api/jobs?limit=100&offset=0

    # Get jobs for a specific flow
    GET /api/jobs?flow_id=data_processing_flow

    # Get only running jobs
    GET /api/jobs?status=running

    # Get running jobs for a specific flow (page 2)
    GET /api/jobs?flow_id=data_processing_flow&status=running&limit=50&offset=50
    ```

    **Response Example**:
    ```json
    {
      "jobs": [
        {
          "job_id": "job-123",
          "flow_id": "data_processing_flow",
          "status": "running",
          "created_at": 1705312800,
          "started_at": 1705312801,
          "completed_at": null,
          "error": null
        }
      ],
      "total": 150,
      "limit": 100,
      "offset": 0
    }
    ```

    **Pagination Calculation**:
    ```javascript
    const totalPages = Math.ceil(response.total / response.limit);
    const currentPage = Math.floor(response.offset / response.limit) + 1;
    const hasNextPage = response.offset + response.limit < response.total;
    const hasPrevPage = response.offset > 0;
    ```

    **Status Values**:
    - `pending`: Job created but not started
    - `running`: Job is executing
    - `idle`: All routines idle, waiting for data
    - `completed`: Job finished successfully
    - `failed`: Job failed with error
    - `paused`: Job execution paused
    - `cancelled`: Job was cancelled

    **Performance Notes**:
    - Large result sets are paginated for performance
    - Default limit of 100 is optimal for most use cases
    - Maximum limit of 1000 prevents excessive memory usage

    Args:
        flow_id: Optional flow ID filter. Only jobs for this flow are returned.
        status: Optional status filter. Only jobs with this status are returned.
        limit: Maximum number of jobs per page (1-1000, default 100).
        offset: Number of jobs to skip for pagination (default 0).

    Returns:
        JobListResponse: Paginated list of jobs with total count, limit, and offset.

    Raises:
        HTTPException: 422 if query parameters are invalid
    """
    all_jobs = job_store.list_all()

    # Apply filters
    filtered_jobs = all_jobs
    if flow_id:
        filtered_jobs = [j for j in filtered_jobs if j.flow_id == flow_id]
    if status:
        filtered_jobs = [
            j
            for j in filtered_jobs
            if (j.status.value == status if hasattr(j.status, "value") else str(j.status) == status)
        ]

    # Get total before pagination
    total = len(filtered_jobs)

    # Apply pagination
    jobs = filtered_jobs[offset : offset + limit]

    return JobListResponse(
        jobs=[_job_to_response(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse, dependencies=[RequireAuth])
async def get_job(job_id: str):
    """Get detailed information about a specific job.

    **Overview**:
    Returns complete information about a job including its current status, timestamps, and error information.

    **Response Fields**:
    - `job_id`: Unique identifier (use this for all job operations)
    - `flow_id`: The flow being executed
    - `status`: Current execution status
    - `created_at`: When job was created (Unix timestamp)
    - `started_at`: When execution started (Unix timestamp, null if not started)
    - `completed_at`: When execution completed (Unix timestamp, null if still running)
    - `error`: Error message if job failed (null if successful or still running)

    **Request Example**:
    ```
    GET /api/jobs/550e8400-e29b-41d4-a716-446655440000
    ```

    **Response Example**:
    ```json
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "flow_id": "data_processing_flow",
      "status": "running",
      "created_at": 1705312800,
      "started_at": 1705312801,
      "completed_at": null,
      "error": null
    }
    ```

    **Status Interpretation**:
    - `running`: Job is actively executing. Check routine status for details.
    - `idle`: All routines are idle. Send data via POST /api/jobs/{job_id}/post to continue.
    - `completed`: Job finished successfully. Check completed_at timestamp.
    - `failed`: Job failed. Check error field for details.
    - `paused`: Job execution is paused. Use POST /api/jobs/{job_id}/resume to continue.
    - `cancelled`: Job was cancelled. Cannot be resumed.

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist

    **Related Endpoints**:
    - GET /api/jobs/{job_id}/status - Get only status (lighter weight)
    - GET /api/jobs/{job_id}/monitoring - Get complete monitoring data
    - GET /api/jobs/{job_id}/state - Get full serialized job state

    Args:
        job_id: Unique job identifier (UUID format)

    Returns:
        JobResponse: Complete job information

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 422 if job_id format is invalid
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return _job_to_response(job_state)


@router.post("/jobs/{job_id}/post", status_code=200, dependencies=[RequireAuth])
async def post_to_job(job_id: str, request: PostToJobRequest):
    """Post data to a routine's input slot in a running or paused job.

    **Overview**:
    This is the primary mechanism for triggering routine execution in Routilux.
    In the new architecture, all routines start in IDLE state and wait for external data.
    Use this endpoint to send data to a routine's input slot, which will trigger execution
    according to the routine's activation policy.

    **When to Use**:
    - Job is in RUNNING or PAUSED status
    - You want to send data to a routine's input slot
    - You want to trigger routine execution
    - You're implementing an interactive workflow

    **Execution Flow**:
    1. Data is queued in the routine's slot
    2. Routine's activation policy is checked
    3. If policy conditions are met, routine executes
    4. Routine emits events to connected slots
    5. Process continues downstream

    **Request Example**:
    ```json
    {
      "routine_id": "data_source",
      "slot_name": "trigger",
      "data": {
        "input": "test_data",
        "index": 1,
        "metadata": {
          "source": "api",
          "timestamp": "2025-01-15T10:00:00Z"
        }
      }
    }
    ```

    **Response Example**:
    ```json
    {
      "status": "posted",
      "job_id": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```

    **Data Format**:
    - `data` can be any JSON-serializable object
    - If `data` is null or not provided, an empty dictionary `{}` is sent
    - The data structure should match what the routine expects
    - Use GET /api/factory/objects/{name}/interface to discover expected data format

    **Activation Policies**:
    - **Immediate**: Routine executes as soon as data arrives
    - **Batch Size**: Routine waits for N items before executing
    - **All Slots Ready**: Routine waits for all input slots to have data
    - **Time Interval**: Routine executes at most once per time interval

    **Error Responses**:
    - `404 Not Found`: Job, flow, routine, or slot not found
    - `409 Conflict`: Job is not in RUNNING or PAUSED status
    - `400 Bad Request`: Invalid data format or routine configuration
    - `422 Validation Error`: Invalid request parameters

    **Best Practices**:
    1. Check job status before posting: GET /api/jobs/{job_id}/status
    2. Verify routine and slot exist: GET /api/flows/{flow_id}/routines
    3. Use consistent data format across posts
    4. Monitor queue status: GET /api/jobs/{job_id}/routines/{routine_id}/queue-status
    5. Handle errors gracefully (job might complete/fail between status check and post)

    **Concurrent Posting**:
    - Multiple posts to the same slot are queued safely
    - Posts to different slots/routines can happen concurrently
    - Queue pressure is monitored automatically

    Args:
        job_id: Unique job identifier
        request: PostToJobRequest containing routine_id, slot_name, and optional data

    Returns:
        dict: Status confirmation with job_id

    Raises:
        HTTPException: 404 if job, flow, routine, or slot not found
        HTTPException: 409 if job is not in RUNNING or PAUSED status
        HTTPException: 400 if data format is invalid
        HTTPException: 422 if request validation fails
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    if job_state.status not in (ExecutionStatus.RUNNING, ExecutionStatus.PAUSED):
        raise HTTPException(
            status_code=409,
            detail="Job is not running or paused; cannot post",
        )

    flow = flow_store.get(job_state.flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{job_state.flow_id}' not found")

    routine = flow.routines.get(request.routine_id)
    if not routine:
        raise HTTPException(status_code=404, detail=f"Routine '{request.routine_id}' not found in flow")

    slot = routine.get_slot(request.slot_name)
    if slot is None:
        raise HTTPException(
            status_code=404,
            detail=f"Slot '{request.slot_name}' not found in routine '{request.routine_id}'",
        )

    data = request.data if request.data is not None else {}
    runtime = get_runtime_instance()

    try:
        runtime.post(
            flow_name=flow.flow_id,
            routine_name=request.routine_id,
            slot_name=request.slot_name,
            data=data,
            job_id=job_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {"status": "posted", "job_id": job_id}


@router.post("/jobs/{job_id}/pause", status_code=200, dependencies=[RequireAuth])
async def pause_job(job_id: str):
    """Pause job execution.

    **Overview**:
    Pauses a running job, stopping all routine execution. The job state is preserved,
    allowing you to resume execution later. Paused jobs can receive data via POST endpoint,
    but routines will not execute until the job is resumed.

    **When to Use**:
    - You need to temporarily stop execution for debugging
    - You want to inspect job state without it changing
    - You need to modify the flow before continuing
    - You're implementing a manual approval step

    **Behavior**:
    - Job status changes to PAUSED
    - Currently executing routines complete their current task
    - New routine activations are blocked
    - Job state is preserved (can be resumed)
    - Data can still be posted to slots (queued, not processed)

    **Request Example**:
    ```
    POST /api/jobs/550e8400-e29b-41d4-a716-446655440000/pause
    ```

    **Response Example**:
    ```json
    {
      "status": "paused",
      "job_id": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```

    **Resuming**:
    - Use POST /api/jobs/{job_id}/resume to continue execution
    - Queued data will be processed when resumed
    - Execution continues from where it was paused

    **Error Responses**:
    - `404 Not Found`: Job or flow not found
    - `400 Bad Request`: Failed to pause (e.g., job already paused or completed)

    **Related Endpoints**:
    - POST /api/jobs/{job_id}/resume - Resume paused job
    - POST /api/jobs/{job_id}/cancel - Cancel job (cannot be resumed)
    - GET /api/jobs/{job_id}/status - Check current status

    Args:
        job_id: Unique job identifier

    Returns:
        dict: Status confirmation with job_id

    Raises:
        HTTPException: 404 if job or flow not found
        HTTPException: 400 if pause operation fails
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    flow = flow_store.get(job_state.flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{job_state.flow_id}' not found")

    try:
        flow.pause(job_state, reason="Paused via API")
        return {"status": "paused", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to pause job: {str(e)}") from e


@router.post("/jobs/{job_id}/resume", status_code=200, dependencies=[RequireAuth])
async def resume_job(job_id: str):
    """Resume execution of a paused job.

    **Overview**:
    Resumes a paused job, allowing routine execution to continue. All queued data
    in slots will be processed according to each routine's activation policy.

    **When to Use**:
    - Job is in PAUSED status
    - You've finished debugging or inspection
    - You want to continue execution after a manual step
    - You've modified the flow and want to continue

    **Behavior**:
    - Job status changes from PAUSED to RUNNING
    - Queued data in slots is processed
    - Routines resume execution based on activation policies
    - Execution continues from where it was paused

    **Request Example**:
    ```
    POST /api/jobs/550e8400-e29b-41d4-a716-446655440000/resume
    ```

    **Response Example**:
    ```json
    {
      "status": "resumed",
      "job_id": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```

    **Error Responses**:
    - `404 Not Found`: Job or flow not found
    - `409 Conflict`: Job is not paused (cannot resume a running/completed job)
    - `400 Bad Request`: Failed to resume (e.g., job executor not available)

    **Note**: You can only resume jobs that are in PAUSED status. Jobs that are
    COMPLETED, FAILED, or CANCELLED cannot be resumed.

    **Related Endpoints**:
    - POST /api/jobs/{job_id}/pause - Pause a running job
    - GET /api/jobs/{job_id}/status - Check current status

    Args:
        job_id: Unique job identifier

    Returns:
        dict: Status confirmation with job_id

    Raises:
        HTTPException: 404 if job or flow not found
        HTTPException: 409 if job is not paused
        HTTPException: 400 if resume operation fails
    """
    from routilux.flow.flow import JobNotRunningError

    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    flow = flow_store.get(job_state.flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{job_state.flow_id}' not found")

    try:
        job_state = flow.resume(job_state)
        job_store.add(job_state)  # Update stored job
        return {"status": "resumed", "job_id": job_id}
    except JobNotRunningError:
        raise HTTPException(status_code=409, detail="Job is not running; cannot resume.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to resume job: {str(e)}") from e


@router.post("/jobs/{job_id}/cancel", status_code=200, dependencies=[RequireAuth])
async def cancel_job(job_id: str):
    """Cancel job execution.

    **Overview**:
    Cancels a running or paused job, stopping all execution immediately.
    Cancelled jobs cannot be resumed - this is a permanent action.

    **When to Use**:
    - Job is taking too long and you want to stop it
    - Job is in an error state and you want to abort
    - You no longer need the job results
    - You want to free up resources

    **Behavior**:
    - Job status changes to CANCELLED
    - All active routine executions are stopped
    - Event loop is terminated
    - Job state is preserved (for inspection)
    - Job cannot be resumed (use a new job if needed)

    **Request Example**:
    ```
    POST /api/jobs/550e8400-e29b-41d4-a716-446655440000/cancel
    ```

    **Response Example**:
    ```json
    {
      "status": "cancelled",
      "job_id": "550e8400-e29b-41d4-a716-446655440000"
    }
    ```

    **Error Responses**:
    - `404 Not Found`: Job or flow not found
    - `400 Bad Request`: Failed to cancel (e.g., job already completed)

    **Note**: Cancelled jobs are still visible in the job list and can be queried,
    but they cannot be resumed or restarted. Create a new job if you need to
    re-execute the flow.

    **Related Endpoints**:
    - POST /api/jobs/{job_id}/pause - Pause job (can be resumed)
    - GET /api/jobs/{job_id}/status - Check current status

    Args:
        job_id: Unique job identifier

    Returns:
        dict: Status confirmation with job_id

    Raises:
        HTTPException: 404 if job or flow not found
        HTTPException: 400 if cancel operation fails
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    flow = flow_store.get(job_state.flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{job_state.flow_id}' not found")

    try:
        flow.cancel(job_state, reason="Cancelled via API")
        return {"status": "cancelled", "job_id": job_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to cancel job: {str(e)}") from e


@router.get("/jobs/{job_id}/status", dependencies=[RequireAuth])
async def get_job_status(job_id: str):
    """Get current status of a job (lightweight endpoint).

    **Overview**:
    Returns only the essential status information about a job. This is a lightweight
    endpoint optimized for frequent polling. For complete job details, use GET /api/jobs/{job_id}.

    **Use Cases**:
    - Polling job status in a UI (lightweight, fast)
    - Checking if job is still running before posting data
    - Quick status checks without full job details

    **Request Example**:
    ```
    GET /api/jobs/550e8400-e29b-41d4-a716-446655440000/status
    ```

    **Response Example**:
    ```json
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "running",
      "flow_id": "data_processing_flow"
    }
    ```

    **Status Values**:
    - `pending`: Job created but not started
    - `running`: Job is executing
    - `idle`: All routines idle, waiting for data
    - `completed`: Job finished successfully
    - `failed`: Job failed with error
    - `paused`: Job execution paused
    - `cancelled`: Job was cancelled

    **Polling Recommendations**:
    - Use reasonable polling intervals (e.g., 1-5 seconds)
    - Stop polling when status is `completed`, `failed`, or `cancelled`
    - Consider using WebSocket for real-time updates: WS /api/ws/jobs/{job_id}/monitor

    **Error Responses**:
    - `404 Not Found`: Job not found

    **Related Endpoints**:
    - GET /api/jobs/{job_id} - Get complete job details
    - GET /api/jobs/{job_id}/monitoring - Get full monitoring data
    - WS /api/ws/jobs/{job_id}/monitor - Real-time status updates

    Args:
        job_id: Unique job identifier

    Returns:
        dict: Job ID, status, and flow ID

    Raises:
        HTTPException: 404 if job not found
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    return {
        "job_id": job_id,
        "status": job_state.status.value
        if hasattr(job_state.status, "value")
        else str(job_state.status),
        "flow_id": job_state.flow_id,
    }


@router.get("/jobs/{job_id}/state", dependencies=[RequireAuth])
async def get_job_state(job_id: str):
    """Get complete serialized job state.

    **Overview**:
    Returns the full serialized state of a job, including all routine states, execution history,
    shared data, and internal state. This is useful for debugging, state inspection, or
    implementing state persistence/resumption.

    **Warning**: This endpoint returns a large amount of data. Use only when you need complete state.
    For most use cases, use GET /api/jobs/{job_id} or GET /api/jobs/{job_id}/monitoring instead.

    **Response Structure**:
    The response is a complete serialization of the JobState object, including:
    - `job_id`: Unique identifier
    - `flow_id`: Flow being executed
    - `status`: Current status
    - `routine_states`: State for each routine (Dict[routine_id, state])
    - `execution_history`: Complete execution history (List[ExecutionRecord])
    - `shared_data`: Shared data dictionary
    - `shared_log`: Execution log entries
    - `created_at`, `started_at`, `completed_at`: Timestamps
    - `error`, `error_traceback`: Error information if failed
    - And more internal state fields

    **Request Example**:
    ```
    GET /api/jobs/550e8400-e29b-41d4-a716-446655440000/state
    ```

    **Response Example** (simplified):
    ```json
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "flow_id": "data_processing_flow",
      "status": "running",
      "routine_states": {
        "data_source": {
          "counter": 5,
          "status": "completed"
        },
        "processor": {
          "processed_count": 3,
          "status": "running"
        }
      },
      "execution_history": [...],
      "shared_data": {
        "total_processed": 8
      },
      "shared_log": [...],
      "created_at": "2025-01-15T10:00:00",
      "started_at": "2025-01-15T10:00:01",
      "completed_at": null,
      "error": null
    }
    ```

    **Use Cases**:
    - Debugging: Inspect complete job state
    - State persistence: Save state for later resumption
    - Analysis: Analyze execution patterns
    - Troubleshooting: Understand job behavior

    **Performance Note**:
    - This endpoint can return large responses for long-running jobs
    - Execution history may be truncated (default limit: 1000 records)
    - Consider using GET /api/jobs/{job_id}/execution-history for just history

    **Error Responses**:
    - `404 Not Found`: Job not found

    **Related Endpoints**:
    - GET /api/jobs/{job_id} - Get job summary (lighter)
    - GET /api/jobs/{job_id}/execution-history - Get just execution history
    - GET /api/jobs/{job_id}/monitoring - Get monitoring data (structured)

    Args:
        job_id: Unique job identifier

    Returns:
        dict: Complete serialized job state

    Raises:
        HTTPException: 404 if job not found
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # Serialize job state
    return job_state.serialize()


@router.post("/jobs/{job_id}/complete", status_code=200, dependencies=[RequireAuth])
async def complete_job(job_id: str, reason: Optional[str] = Query(None, description="Optional reason for completion")):
    """Manually mark a job as completed.

    **Overview**:
    Manually completes a job that is in IDLE or RUNNING status. This is useful when:
    - All work is done but the job is still in IDLE state
    - You want to explicitly mark the job as complete
    - The job is waiting but you've confirmed all processing is finished

    **When to Use**:
    - Job is in IDLE status and you've confirmed all work is done
    - Job is in RUNNING status but you want to force completion
    - Implementing manual approval workflows
    - Testing and development scenarios

    **Behavior**:
    - Job status changes to COMPLETED
    - `completed_at` timestamp is set
    - Event loop is stopped
    - All routine execution stops
    - Job cannot be resumed (create new job if needed)

    **Request Example**:
    ```
    POST /api/jobs/550e8400-e29b-41d4-a716-446655440000/complete?reason=All%20processing%20finished
    ```

    **Response Example**:
    ```json
    {
      "status": "completed",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "reason": "All processing finished"
    }
    ```

    **Error Responses**:
    - `404 Not Found`: Job not found
    - `400 Bad Request`: Job is already in a terminal state (completed/failed/cancelled)

    **Note**: This is different from automatic completion. Automatic completion happens
    when all routines are idle and no more work is pending. This endpoint allows you
    to manually trigger completion.

    **Related Endpoints**:
    - POST /api/jobs/{job_id}/fail - Mark job as failed
    - GET /api/jobs/{job_id}/status - Check current status

    Args:
        job_id: Unique job identifier
        reason: Optional reason for completion (for logging/audit)

    Returns:
        dict: Status confirmation with job_id and reason

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 400 if job is in terminal state
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    from routilux.job_manager import get_job_manager
    from routilux.status import ExecutionStatus

    job_manager = get_job_manager()
    executor = job_manager.get_job(job_id)

    if executor:
        executor.complete()
    else:
        # Job not running, directly mark as completed
        if job_state.status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
            raise HTTPException(
                status_code=400,
                detail=f"Job is already in terminal state: {job_state.status}"
            )
        job_state.status = ExecutionStatus.COMPLETED
        job_state.completed_at = datetime.now()
        job_store.add(job_state)

    return {"status": "completed", "job_id": job_id, "reason": reason}


@router.post("/jobs/{job_id}/fail", status_code=200, dependencies=[RequireAuth])
async def fail_job(
    job_id: str,
    error: Optional[str] = Query(None, description="Error message describing the failure"),
):
    """Manually mark a job as failed.

    **Overview**:
    Manually marks a job as failed with an optional error message. This is useful when:
    - External system detects an error condition
    - Manual intervention determines the job should fail
    - Testing error handling scenarios

    **When to Use**:
    - External validation fails
    - Manual review determines job should fail
    - Implementing error workflows
    - Testing error scenarios

    **Behavior**:
    - Job status changes to FAILED
    - Error message is stored in job_state.error
    - Error is also stored in shared_data["error"]
    - Job execution stops
    - Job cannot be resumed (create new job if needed)

    **Request Example**:
    ```
    POST /api/jobs/550e8400-e29b-41d4-a716-446655440000/fail?error=External%20validation%20failed
    ```

    **Response Example**:
    ```json
    {
      "status": "failed",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "error": "External validation failed"
    }
    ```

    **Error Responses**:
    - `404 Not Found`: Job not found
    - `400 Bad Request`: Job is already in a terminal state

    **Related Endpoints**:
    - POST /api/jobs/{job_id}/complete - Mark job as completed
    - GET /api/jobs/{job_id} - Get job details (includes error field)

    Args:
        job_id: Unique job identifier
        error: Optional error message describing the failure

    Returns:
        dict: Status confirmation with job_id and error message

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 400 if job is in terminal state
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    from routilux.status import ExecutionStatus

    if job_state.status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail=f"Job is already in terminal state: {job_state.status}"
        )

    job_state.status = ExecutionStatus.FAILED
    if error:
        job_state.error = error
        job_state.shared_data["error"] = error
    job_store.add(job_state)

    return {"status": "failed", "job_id": job_id, "error": error}


@router.post("/jobs/{job_id}/wait", status_code=200, dependencies=[RequireAuth])
async def wait_for_job(
    job_id: str,
    timeout: Optional[float] = Query(
        None,
        ge=1.0,
        le=3600.0,
        description="Maximum time to wait in seconds. Range: 1-3600. Default: 60 seconds.",
        example=60.0,
    ),
):
    """Wait for a job to complete (blocking endpoint).

    **Overview**:
    Blocks until the job reaches a terminal state (completed, failed, or cancelled),
    or until the timeout is reached. This is useful for synchronous workflows where
    you need to wait for job completion before proceeding.

    **When to Use**:
    - Synchronous workflows
    - Scripts that need to wait for completion
    - Testing scenarios
    - Simple automation

    **Behavior**:
    - Blocks the request until job completes or timeout
    - Polls job status at regular intervals
    - Returns immediately if job is already in terminal state
    - Returns timeout status if timeout is reached

    **Request Example**:
    ```
    POST /api/jobs/550e8400-e29b-41d4-a716-446655440000/wait?timeout=120
    ```

    **Response Example (Completed)**:
    ```json
    {
      "status": "completed",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "final_status": "completed",
      "waited_seconds": 45.2
    }
    ```

    **Response Example (Timeout)**:
    ```json
    {
      "status": "timeout",
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "final_status": "running",
      "waited_seconds": 120.0,
      "message": "Job did not complete within timeout period"
    }
    ```

    **Timeout Behavior**:
    - If timeout is reached, returns with status "timeout"
    - Job continues running (not cancelled)
    - You can call this endpoint again to wait more

    **Performance Note**:
    - This endpoint blocks the HTTP connection
    - Use for scripts/automation, not for interactive UIs
    - For UIs, use polling: GET /api/jobs/{job_id}/status
    - For real-time updates, use WebSocket: WS /api/ws/jobs/{job_id}/monitor

    **Error Responses**:
    - `404 Not Found`: Job not found
    - `422 Validation Error`: Invalid timeout value

    **Related Endpoints**:
    - GET /api/jobs/{job_id}/status - Non-blocking status check
    - WS /api/ws/jobs/{job_id}/monitor - Real-time status updates

    Args:
        job_id: Unique job identifier
        timeout: Maximum time to wait in seconds (1-3600, default: 60)

    Returns:
        dict: Final status and wait duration

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 422 if timeout is invalid
    """
    from routilux.job_manager import get_job_manager
    from routilux.status import ExecutionStatus

    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # Check if already in terminal state
    if job_state.status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED):
        return {
            "status": "already_complete",
            "job_id": job_id,
            "final_status": str(job_state.status),
            "waited_seconds": 0.0,
        }

    # Wait for completion
    job_manager = get_job_manager()
    effective_timeout = timeout if timeout is not None else 60.0
    import time

    start_time = time.time()
    check_interval = 0.5  # Check every 500ms

    while True:
        elapsed = time.time() - start_time
        if elapsed >= effective_timeout:
            # Timeout reached
            current_status = job_store.get(job_id)
            return {
                "status": "timeout",
                "job_id": job_id,
                "final_status": str(current_status.status) if current_status else "unknown",
                "waited_seconds": elapsed,
                "message": f"Job did not complete within {effective_timeout} seconds",
            }

        # Check if job is in terminal state
        current_job = job_store.get(job_id)
        if current_job and current_job.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        ):
            return {
                "status": "completed",
                "job_id": job_id,
                "final_status": str(current_job.status),
                "waited_seconds": time.time() - start_time,
            }

        # Wait before next check
        import asyncio

        await asyncio.sleep(check_interval)


@router.get("/jobs/{job_id}/execution-history", dependencies=[RequireAuth])
async def get_execution_history(
    job_id: str,
    routine_id: Optional[str] = Query(
        None,
        description="Optional routine ID filter. If provided, only execution records for this routine are returned.",
        example="data_processor",
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=10000,
        description="Maximum number of execution records to return. Range: 1-10000. "
        "If not provided, returns all records (may be large). "
        "Records are returned in chronological order (oldest first).",
        example=100,
    ),
):
    """Get execution history for a job.

    **Overview**:
    Returns a formatted list of execution records showing the complete execution history
    of a job. Each record represents a routine execution, event emission, or slot call.

    **Use Cases**:
    - Debugging: Understand execution flow
    - Analysis: Analyze execution patterns
    - Audit: Track what happened during execution
    - Troubleshooting: Identify where errors occurred

    **Request Examples**:
    ```
    # Get all execution history
    GET /api/jobs/job-123/execution-history

    # Get history for a specific routine
    GET /api/jobs/job-123/execution-history?routine_id=data_processor

    # Get last 100 records
    GET /api/jobs/job-123/execution-history?limit=100
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job-123",
      "routine_id": null,
      "history": [
        {
          "routine_id": "data_source",
          "event_name": "output",
          "timestamp": "2025-01-15T10:00:00.100Z",
          "data": {
            "data": "test_data",
            "index": 1
          },
          "status": "completed"
        },
        {
          "routine_id": "data_processor",
          "event_name": "slot_call",
          "timestamp": "2025-01-15T10:00:05.200Z",
          "data": {
            "slot": "input",
            "data": {"data": "test_data", "index": 1}
          },
          "status": "completed"
        }
      ],
      "total": 2
    }
    ```

    **Record Types**:
    - `routine_start`: Routine execution started
    - `routine_end`: Routine execution ended
    - `slot_call`: Data received in a slot
    - `event_emit`: Event emitted from a routine

    **Performance Note**:
    - Execution history can be large for long-running jobs
    - Default limit in JobState is 1000 records
    - Use `limit` parameter to control response size
    - Consider using GET /api/jobs/{job_id}/trace for structured trace data

    **Error Responses**:
    - `404 Not Found`: Job not found

    **Related Endpoints**:
    - GET /api/jobs/{job_id}/trace - Get structured execution trace
    - GET /api/jobs/{job_id}/state - Get complete job state (includes history)

    Args:
        job_id: Unique job identifier
        routine_id: Optional routine ID filter
        limit: Maximum number of records to return

    Returns:
        dict: Execution history with total count

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 422 if parameters are invalid
    """
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    history = job_state.execution_history
    if routine_id:
        history = [h for h in history if h.routine_id == routine_id]

    if limit:
        history = history[-limit:]  # Get last N records

    return {
        "job_id": job_id,
        "routine_id": routine_id,
        "history": [
            {
                "routine_id": h.routine_id,
                "event_name": h.event_name,
                "timestamp": h.timestamp.isoformat() if hasattr(h.timestamp, "isoformat") else str(h.timestamp),
                "data": h.data,
                "status": h.status if hasattr(h, "status") else None,
            }
            for h in history
        ],
        "total": len(history),
    }


@router.post("/jobs/cleanup", dependencies=[RequireAuth])
async def cleanup_jobs(
    max_age_hours: int = Query(
        24,
        ge=1,
        le=720,
        description="Maximum age in hours. Jobs older than this will be removed. "
        "Range: 1-720 hours (1 hour to 30 days). Default: 24 hours.",
        example=24,
    ),
    status: Optional[List[str]] = Query(
        None,
        description="Optional list of statuses to clean up. Only jobs with these statuses will be removed. "
        "If not provided, all jobs older than max_age_hours are removed regardless of status. "
        "Valid status values: 'pending', 'running', 'idle', 'completed', 'failed', 'paused', 'cancelled'. "
        "Example: ['completed', 'failed'] to clean up only finished jobs.",
        example=["completed", "failed"],
    ),
):
    """Clean up old jobs from the system.

    **Overview**:
    Removes jobs that are older than the specified age, optionally filtered by status.
    This is useful for maintaining system performance and freeing up storage space.

    **When to Use**:
    - Regular maintenance (e.g., daily cleanup of completed jobs)
    - Free up storage space
    - Remove old failed jobs
    - Clean up test jobs

    **Safety**:
    - Only removes jobs older than max_age_hours
    - Can filter by status to preserve important jobs
    - Returns count of removed jobs for confirmation
    - Operation is logged for audit purposes

    **Request Examples**:
    ```
    # Remove all jobs older than 24 hours
    POST /api/jobs/cleanup?max_age_hours=24

    # Remove only completed/failed jobs older than 7 days
    POST /api/jobs/cleanup?max_age_hours=168&status=completed&status=failed

    # Remove all old jobs (any status) older than 30 days
    POST /api/jobs/cleanup?max_age_hours=720
    ```

    **Response Example**:
    ```json
    {
      "removed_count": 45,
      "max_age_hours": 24,
      "status_filter": ["completed", "failed"]
    }
    ```

    **Best Practices**:
    1. **Regular Cleanup**: Set up a cron job to run cleanup daily
    2. **Status Filtering**: Use status filter to preserve running/paused jobs
    3. **Age Limits**: Use appropriate age limits (24h for dev, 7-30 days for production)
    4. **Backup**: Consider backing up important job states before cleanup
    5. **Monitoring**: Monitor removed_count to track cleanup effectiveness

    **Warning**: This operation is **irreversible**. Deleted jobs cannot be recovered.
    Make sure you don't need the job data before running cleanup.

    **Error Responses**:
    - `422 Validation Error`: Invalid max_age_hours or status values

    Args:
        max_age_hours: Maximum age in hours (1-720, default: 24)
        status: Optional list of statuses to clean up (can specify multiple times)

    Returns:
        dict: Number of jobs removed, max_age_hours, and status_filter

    Raises:
        HTTPException: 422 if parameters are invalid
    """
    max_age_seconds = max_age_hours * 3600
    removed_count = job_store.cleanup_old_jobs(
        max_age_seconds=max_age_seconds,
        status_filter=status,
    )

    return {
        "removed_count": removed_count,
        "max_age_hours": max_age_hours,
        "status_filter": status,
    }
