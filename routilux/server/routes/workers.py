"""
Worker management API routes.

Workers are long-running execution instances of Flows.
One Worker can process multiple Jobs.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from routilux.server.dependencies import (
    get_flow_registry,
    get_job_storage,
    get_runtime,
    get_worker_registry,
)
from routilux.server.errors import ErrorCode, create_error_response
from routilux.server.middleware.auth import RequireAuth
from routilux.server.models.breakpoint import BreakpointUpdateRequest
from routilux.server.models.job import JobListResponse, JobResponse
from routilux.server.models.worker import (
    WorkerCreateRequest,
    WorkerListResponse,
    WorkerResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _dt_to_int(dt: Optional[datetime]) -> Optional[int]:
    """Convert datetime to Unix timestamp."""
    if dt is None:
        return None
    return int(dt.timestamp())


def _worker_to_response(worker_state) -> WorkerResponse:
    """Convert WorkerState to API response."""
    return WorkerResponse(
        worker_id=worker_state.worker_id,
        flow_id=worker_state.flow_id,
        status=worker_state.status.value
        if hasattr(worker_state.status, "value")
        else str(worker_state.status),
        created_at=_dt_to_int(getattr(worker_state, "created_at", None)),
        started_at=_dt_to_int(getattr(worker_state, "started_at", None)),
        jobs_processed=getattr(worker_state, "jobs_processed", 0),
        jobs_failed=getattr(worker_state, "jobs_failed", 0),
    )


def _job_to_response(job_context, flow_id: str = "") -> JobResponse:
    """Convert JobContext to API response."""
    return JobResponse(
        job_id=job_context.job_id,
        worker_id=job_context.worker_id,
        flow_id=flow_id,
        status=job_context.status,
        created_at=_dt_to_int(getattr(job_context, "created_at", None)),
        started_at=_dt_to_int(getattr(job_context, "created_at", None))
        if job_context.status != "pending"
        else None,
        completed_at=_dt_to_int(getattr(job_context, "completed_at", None)),
        error=job_context.error,
        metadata=job_context.metadata,
    )


@router.post("/workers", response_model=WorkerResponse, status_code=201, dependencies=[RequireAuth])
async def create_worker(request: WorkerCreateRequest):
    """
    Create and start a new Worker for a Flow.

    **Overview**:
    Creates a long-running Worker instance that can process multiple Jobs for a specific Flow.
    Workers provide persistent processing capacity and maintain state across multiple job executions.
    Use this when you need to process multiple jobs with the same flow configuration.

    **Endpoint**: `POST /api/v1/workers`

    **Use Cases**:
    - Create persistent workers for high-throughput processing
    - Maintain worker state across multiple job executions
    - Process multiple jobs with the same flow without recreating the flow each time
    - Build worker pools for load distribution

    **Request Example**:
    ```json
    {
      "flow_id": "data_processing_flow"
    }
    ```

    **Response Example**:
    ```json
    {
      "worker_id": "worker_abc123",
      "flow_id": "data_processing_flow",
      "status": "running",
      "created_at": 1705312800,
      "started_at": 1705312800,
      "jobs_processed": 0,
      "jobs_failed": 0
    }
    ```

    **Worker Lifecycle**:
    1. Worker is created and started immediately
    2. Worker can accept jobs via POST /api/v1/jobs
    3. Worker processes jobs sequentially or in parallel (depending on flow configuration)
    4. Worker maintains state until explicitly stopped (DELETE /api/v1/workers/{worker_id})

    **Worker vs One-Shot Execution**:
    - **Worker**: Use for multiple jobs, persistent state, long-running processes
    - **One-shot**: Use POST /api/v1/execute for single job execution without creating a worker

    **Error Responses**:
    - `404 Not Found`: Flow with this ID does not exist
    - `500 Internal Server Error`: Failed to create worker (runtime error)

    **Best Practices**:
    1. Create workers for flows that will process multiple jobs
    2. Monitor worker status: GET /api/v1/workers/{worker_id}
    3. Stop workers when no longer needed: DELETE /api/v1/workers/{worker_id}
    4. Use worker statistics to monitor performance: GET /api/v1/workers/{worker_id}/statistics

    **Related Endpoints**:
    - GET /api/v1/workers/{worker_id} - Get worker details
    - POST /api/v1/jobs - Submit job to worker
    - GET /api/v1/workers/{worker_id}/jobs - List jobs for worker
    - DELETE /api/v1/workers/{worker_id} - Stop worker

    Args:
        request: WorkerCreateRequest with flow_id

    Returns:
        WorkerResponse: Created worker information with status and metadata

    Raises:
        HTTPException: 404 if flow not found
        HTTPException: 500 if worker creation fails
    """
    runtime = get_runtime()
    flow_registry = get_flow_registry()

    # Validate flow exists
    flow = flow_registry.get_by_name(request.flow_id)
    if flow is None:
        flow = flow_registry.get(request.flow_id)
    if flow is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.FLOW_NOT_FOUND, f"Flow '{request.flow_id}' not found"
            ),
        )

    try:
        # Validate custom worker_id if provided
        if request.worker_id:
            # Check if worker_id already exists in Runtime active workers
            with runtime._worker_lock:
                if request.worker_id in runtime._active_workers:
                    raise HTTPException(
                        status_code=409,
                        detail=create_error_response(
                            ErrorCode.WORKER_ALREADY_EXISTS,
                            f"Worker '{request.worker_id}' already exists",
                        ),
                    )

            # Also check WorkerRegistry
            worker_registry = get_worker_registry()
            existing_worker = worker_registry.get(request.worker_id)
            if existing_worker is not None:
                raise HTTPException(
                    status_code=409,
                    detail=create_error_response(
                        ErrorCode.WORKER_ALREADY_EXISTS,
                        f"Worker '{request.worker_id}' already exists",
                    ),
                )

        # Create worker via Runtime.exec()
        worker_state = runtime.exec(flow_name=request.flow_id, worker_id=request.worker_id)

        logger.info(f"Created worker {worker_state.worker_id} for flow {request.flow_id}")
        return _worker_to_response(worker_state)

    except HTTPException:
        # Re-raise HTTPException to preserve status code and error details
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=404, detail=create_error_response(ErrorCode.FLOW_NOT_FOUND, str(e))
        )
    except Exception as e:
        logger.exception(f"Failed to create worker: {e}")
        raise HTTPException(
            status_code=500,
            detail=create_error_response(
                ErrorCode.INTERNAL_ERROR, f"Failed to create worker: {str(e)}"
            ),
        )


@router.get("/workers", response_model=WorkerListResponse, dependencies=[RequireAuth])
async def list_workers(
    flow_id: Optional[str] = Query(
        None,
        description="Filter by flow ID. Only workers executing this flow will be returned.",
        examples=["data_processing_flow"],
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by worker status. Valid values: 'running', 'paused', 'completed', 'failed', 'cancelled'.",
        examples=["running"],
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of workers to return. Range: 1-1000. Default: 100.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of workers to skip for pagination. Default: 0.",
    ),
):
    """
    List all Workers with optional filters.

    **Overview**:
    Returns a paginated list of all active Workers in the system, with optional filtering
    by flow_id and status. Use this to discover workers, monitor system load, and track
    worker distribution across flows.

    **Endpoint**: `GET /api/v1/workers`

    **Use Cases**:
    - Monitor all active workers in the system
    - Find workers for a specific flow
    - Check worker status distribution
    - Build worker management dashboards
    - Track system capacity and load

    **Query Parameters**:
    - `flow_id` (optional): Filter workers by flow ID
    - `status` (optional): Filter workers by status (running, paused, completed, failed, cancelled)
    - `limit` (optional): Maximum results (1-1000, default: 100)
    - `offset` (optional): Skip first N results for pagination (default: 0)

    **Request Examples**:
    ```
    # Get all workers
    GET /api/v1/workers

    # Get workers for a specific flow
    GET /api/v1/workers?flow_id=data_processing_flow

    # Get only running workers
    GET /api/v1/workers?status=running

    # Get workers for a flow with pagination
    GET /api/v1/workers?flow_id=data_processing_flow&limit=50&offset=0
    ```

    **Response Example**:
    ```json
    {
      "workers": [
        {
          "worker_id": "worker_abc123",
          "flow_id": "data_processing_flow",
          "status": "running",
          "created_at": 1705312800,
          "started_at": 1705312800,
          "jobs_processed": 15,
          "jobs_failed": 1
        },
        {
          "worker_id": "worker_def456",
          "flow_id": "data_processing_flow",
          "status": "paused",
          "created_at": 1705312700,
          "started_at": 1705312700,
          "jobs_processed": 5,
          "jobs_failed": 0
        }
      ],
      "total": 2,
      "limit": 100,
      "offset": 0
    }
    ```

    **Pagination**:
    - Use `limit` and `offset` for pagination
    - `total` indicates the total number of workers matching filters
    - Results are ordered by creation time (newest first)

    **Worker Status Values**:
    - `running`: Worker is active and processing jobs
    - `paused`: Worker is paused (not processing new jobs)
    - `completed`: Worker has completed all jobs and stopped
    - `failed`: Worker encountered an error and stopped
    - `cancelled`: Worker was manually cancelled

    **Performance Note**:
    - Returns workers from both Runtime active list and WorkerRegistry
    - For large numbers of workers, use pagination
    - Filtering by flow_id or status reduces response size

    **Related Endpoints**:
    - GET /api/v1/workers/{worker_id} - Get specific worker details
    - POST /api/v1/workers - Create new worker
    - GET /api/v1/workers/{worker_id}/statistics - Get worker statistics

    Args:
        flow_id: Optional flow ID filter
        status: Optional status filter
        limit: Maximum workers to return (1-1000)
        offset: Number of workers to skip

    Returns:
        WorkerListResponse: Paginated list of workers with total count

    Raises:
        HTTPException: 500 if runtime or registry is not accessible
    """
    runtime = get_runtime()

    # Get all active workers from Runtime
    with runtime._worker_lock:
        all_workers = list(runtime._active_workers.values())

    # Also check WorkerRegistry for workers not in active list
    worker_registry = get_worker_registry()
    for worker in worker_registry.list_all():
        if worker.worker_id not in [w.worker_id for w in all_workers]:
            all_workers.append(worker)

    # Apply filters
    if flow_id:
        all_workers = [w for w in all_workers if w.flow_id == flow_id]
    if status:
        all_workers = [
            w
            for w in all_workers
            if (w.status.value if hasattr(w.status, "value") else str(w.status)) == status
        ]

    total = len(all_workers)
    workers = all_workers[offset : offset + limit]

    return WorkerListResponse(
        workers=[_worker_to_response(w) for w in workers],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/workers/{worker_id}", response_model=WorkerResponse, dependencies=[RequireAuth])
async def get_worker(worker_id: str):
    """
    Get Worker details by ID.

    **Overview**:
    Returns detailed information about a specific Worker, including its status, job statistics,
    and lifecycle timestamps. Use this to check worker health, monitor job processing,
    and track worker performance.

    **Endpoint**: `GET /api/v1/workers/{worker_id}`

    **Use Cases**:
    - Check worker status and health
    - Monitor job processing statistics
    - Track worker lifecycle (created_at, started_at)
    - Verify worker exists before submitting jobs
    - Build worker monitoring dashboards

    **Request Example**:
    ```
    GET /api/v1/workers/worker_abc123
    ```

    **Response Example**:
    ```json
    {
      "worker_id": "worker_abc123",
      "flow_id": "data_processing_flow",
      "status": "running",
      "created_at": 1705312800,
      "started_at": 1705312800,
      "jobs_processed": 15,
      "jobs_failed": 1
    }
    ```

    **Response Fields**:
    - `worker_id`: Unique worker identifier
    - `flow_id`: Flow this worker is executing
    - `status`: Current worker status (running, paused, completed, failed, cancelled)
    - `created_at`: Unix timestamp when worker was created
    - `started_at`: Unix timestamp when worker started processing
    - `jobs_processed`: Total number of jobs processed by this worker
    - `jobs_failed`: Total number of jobs that failed

    **Worker Status**:
    - `running`: Worker is active and can process jobs
    - `paused`: Worker is paused (use POST /api/v1/workers/{worker_id}/resume to resume)
    - `completed`: Worker finished all jobs and stopped
    - `failed`: Worker encountered an error
    - `cancelled`: Worker was manually stopped

    **Error Responses**:
    - `404 Not Found`: Worker with this ID does not exist

    **Related Endpoints**:
    - GET /api/v1/workers/{worker_id}/jobs - List jobs for this worker
    - GET /api/v1/workers/{worker_id}/statistics - Get detailed statistics
    - GET /api/v1/workers/{worker_id}/history - Get execution history
    - POST /api/v1/workers/{worker_id}/pause - Pause worker
    - POST /api/v1/workers/{worker_id}/resume - Resume worker
    - DELETE /api/v1/workers/{worker_id} - Stop worker

    Args:
        worker_id: Unique worker identifier

    Returns:
        WorkerResponse: Worker details with status and statistics

    Raises:
        HTTPException: 404 if worker not found
    """
    runtime = get_runtime()
    worker_registry = get_worker_registry()

    # Check active workers first
    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    # Fall back to registry
    if worker_state is None:
        worker_state = worker_registry.get(worker_id)

    if worker_state is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_FOUND, f"Worker '{worker_id}' not found"
            ),
        )

    return _worker_to_response(worker_state)


@router.delete("/workers/{worker_id}", status_code=204, dependencies=[RequireAuth])
async def stop_worker(worker_id: str):
    """
    Stop and remove a Worker.

    **Overview**:
    Stops a running Worker and removes it from the active workers list. This operation
    interrupts any jobs currently being processed by the worker. The worker cannot be
    restarted - you must create a new worker if needed.

    **Endpoint**: `DELETE /api/v1/workers/{worker_id}`

    **Use Cases**:
    - Stop workers that are no longer needed
    - Free up system resources
    - Gracefully shut down workers
    - Clean up completed workers

    **Request Example**:
    ```
    DELETE /api/v1/workers/worker_abc123
    ```

    **Response**: 204 No Content (successful deletion)

    **Warning**:
    - **Jobs in progress will be interrupted** when the worker is stopped
    - This operation is **irreversible** - the worker cannot be restarted
    - Consider pausing the worker first (POST /api/v1/workers/{worker_id}/pause) if you
      want to resume later

    **Behavior**:
    1. Stops the worker's executor (interrupts running jobs)
    2. Removes worker from active workers list
    3. Removes worker's job tracking
    4. Worker state is preserved in WorkerRegistry for historical queries

    **Error Responses**:
    - `404 Not Found`: Worker with this ID does not exist

    **Best Practices**:
    1. Check worker status before stopping: GET /api/v1/workers/{worker_id}
    2. Consider pausing instead if you might need to resume: POST /api/v1/workers/{worker_id}/pause
    3. Wait for jobs to complete before stopping if possible
    4. Check job status after stopping: GET /api/v1/workers/{worker_id}/jobs

    **Related Endpoints**:
    - POST /api/v1/workers/{worker_id}/pause - Pause worker (can resume later)
    - GET /api/v1/workers/{worker_id}/jobs - Check jobs before stopping
    - POST /api/v1/workers - Create new worker if needed

    Args:
        worker_id: Unique worker identifier

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if worker not found
    """
    runtime = get_runtime()

    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    if worker_state is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_FOUND, f"Worker '{worker_id}' not found"
            ),
        )

    # Get executor and stop it
    executor = getattr(worker_state, "_executor", None)
    if executor:
        try:
            executor.stop(status="completed")
        except Exception as e:
            logger.warning(f"Error stopping executor for worker {worker_id}: {e}")

    # Remove from active workers
    with runtime._worker_lock:
        runtime._active_workers.pop(worker_id, None)

    # Also remove from jobs tracking
    with runtime._jobs_lock:
        runtime._active_jobs.pop(worker_id, None)

    logger.info(f"Stopped worker {worker_id}")
    return None


@router.post(
    "/workers/{worker_id}/pause", response_model=WorkerResponse, dependencies=[RequireAuth]
)
async def pause_worker(worker_id: str):
    """
    Pause a running Worker.

    **Overview**:
    Pauses a running Worker, preventing it from processing new jobs. The worker remains
    in the system and can be resumed later. Jobs already in progress will complete,
    but no new jobs will be processed until the worker is resumed.

    **Endpoint**: `POST /api/v1/workers/{worker_id}/pause`

    **Use Cases**:
    - Temporarily stop processing without losing worker state
    - Pause for maintenance or debugging
    - Control job processing rate
    - Gracefully handle high load situations

    **Request Example**:
    ```
    POST /api/v1/workers/worker_abc123/pause
    ```

    **Response Example**:
    ```json
    {
      "worker_id": "worker_abc123",
      "flow_id": "data_processing_flow",
      "status": "paused",
      "created_at": 1705312800,
      "started_at": 1705312800,
      "jobs_processed": 15,
      "jobs_failed": 1
    }
    ```

    **Behavior**:
    - Worker status changes to "paused"
    - Jobs currently executing will complete
    - New jobs submitted to this worker will queue but not execute
    - Worker can be resumed with POST /api/v1/workers/{worker_id}/resume

    **Error Responses**:
    - `404 Not Found`: Worker with this ID does not exist
    - `400 Bad Request`: Worker is already paused or in terminal state (completed/failed/cancelled)

    **Worker States**:
    - Can pause: `running`
    - Cannot pause: `paused`, `completed`, `failed`, `cancelled`

    **Best Practices**:
    1. Check worker status before pausing: GET /api/v1/workers/{worker_id}
    2. Monitor queued jobs: GET /api/v1/workers/{worker_id}/jobs?status=pending
    3. Resume when ready: POST /api/v1/workers/{worker_id}/resume
    4. Use pause instead of stop if you plan to resume later

    **Related Endpoints**:
    - POST /api/v1/workers/{worker_id}/resume - Resume paused worker
    - GET /api/v1/workers/{worker_id} - Check worker status
    - GET /api/v1/workers/{worker_id}/jobs - Monitor queued jobs

    Args:
        worker_id: Unique worker identifier

    Returns:
        WorkerResponse: Updated worker information with paused status

    Raises:
        HTTPException: 404 if worker not found
        HTTPException: 400 if worker cannot be paused
    """

    runtime = get_runtime()

    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    if worker_state is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_FOUND, f"Worker '{worker_id}' not found"
            ),
        )

    # Validate worker state
    status_value = (
        worker_state.status.value
        if hasattr(worker_state.status, "value")
        else str(worker_state.status)
    )

    if status_value == "paused":
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_RUNNING, f"Worker '{worker_id}' is already paused"
            ),
        )

    if status_value in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                ErrorCode.WORKER_ALREADY_COMPLETED,
                f"Worker '{worker_id}' is in terminal state: {status_value}",
            ),
        )

    executor = getattr(worker_state, "_executor", None)
    if executor is None:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_RUNNING, f"Worker '{worker_id}' has no executor"
            ),
        )

    try:
        executor.pause()
        logger.info(f"Paused worker {worker_id}")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                ErrorCode.INTERNAL_ERROR, f"Failed to pause worker: {str(e)}"
            ),
        )

    # Refresh state
    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    return _worker_to_response(worker_state)


@router.post(
    "/workers/{worker_id}/resume", response_model=WorkerResponse, dependencies=[RequireAuth]
)
async def resume_worker(worker_id: str):
    """
    Resume a paused Worker.

    **Overview**:
    Resumes a paused Worker, allowing it to process queued jobs again. The worker
    will immediately start processing any pending jobs that were queued while paused.

    **Endpoint**: `POST /api/v1/workers/{worker_id}/resume`

    **Use Cases**:
    - Resume processing after maintenance
    - Continue processing after temporary pause
    - Restart job processing after debugging
    - Handle load spikes by resuming paused workers

    **Request Example**:
    ```
    POST /api/v1/workers/worker_abc123/resume
    ```

    **Response Example**:
    ```json
    {
      "worker_id": "worker_abc123",
      "flow_id": "data_processing_flow",
      "status": "running",
      "created_at": 1705312800,
      "started_at": 1705312800,
      "jobs_processed": 15,
      "jobs_failed": 1
    }
    ```

    **Behavior**:
    - Worker status changes from "paused" to "running"
    - Queued jobs will start processing immediately
    - Worker resumes normal operation

    **Error Responses**:
    - `404 Not Found`: Worker with this ID does not exist
    - `400 Bad Request`: Worker is not paused (must be in "paused" state)

    **Worker States**:
    - Can resume: `paused`
    - Cannot resume: `running`, `completed`, `failed`, `cancelled`

    **Best Practices**:
    1. Verify worker is paused before resuming: GET /api/v1/workers/{worker_id}
    2. Check queued jobs: GET /api/v1/workers/{worker_id}/jobs?status=pending
    3. Monitor worker after resuming to ensure jobs process correctly
    4. Use pause/resume for temporary stops instead of stop/restart

    **Related Endpoints**:
    - POST /api/v1/workers/{worker_id}/pause - Pause worker
    - GET /api/v1/workers/{worker_id} - Check worker status
    - GET /api/v1/workers/{worker_id}/jobs - Monitor job processing

    Args:
        worker_id: Unique worker identifier

    Returns:
        WorkerResponse: Updated worker information with running status

    Raises:
        HTTPException: 404 if worker not found
        HTTPException: 400 if worker is not paused
    """

    runtime = get_runtime()

    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    if worker_state is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_FOUND, f"Worker '{worker_id}' not found"
            ),
        )

    # Validate worker state
    status_value = (
        worker_state.status.value
        if hasattr(worker_state.status, "value")
        else str(worker_state.status)
    )

    if status_value != "paused":
        if status_value in ("completed", "failed", "cancelled"):
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    ErrorCode.WORKER_ALREADY_COMPLETED,
                    f"Worker '{worker_id}' is in terminal state: {status_value}",
                ),
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=create_error_response(
                    ErrorCode.WORKER_NOT_RUNNING,
                    f"Worker '{worker_id}' is not paused (current status: {status_value})",
                ),
            )

    executor = getattr(worker_state, "_executor", None)
    if executor is None:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_RUNNING, f"Worker '{worker_id}' has no executor"
            ),
        )

    try:
        executor.resume()
        logger.info(f"Resumed worker {worker_id}")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                ErrorCode.INTERNAL_ERROR, f"Failed to resume worker: {str(e)}"
            ),
        )

    # Refresh state
    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    return _worker_to_response(worker_state)


@router.get("/workers/{worker_id}/jobs", response_model=JobListResponse, dependencies=[RequireAuth])
async def list_worker_jobs(
    worker_id: str,
    status: Optional[str] = Query(
        None,
        description="Filter by job status. Valid values: 'pending', 'running', 'completed', 'failed'.",
        examples=["running"],
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of jobs to return. Range: 1-1000. Default: 100.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of jobs to skip for pagination. Default: 0.",
    ),
):
    """
    List all Jobs for a specific Worker.

    **Overview**:
    Returns a paginated list of all Jobs processed by a specific Worker, with optional
    filtering by status. Use this to monitor job execution, track worker performance,
    and debug job issues.

    **Endpoint**: `GET /api/v1/workers/{worker_id}/jobs`

    **Use Cases**:
    - Monitor all jobs processed by a worker
    - Track job success/failure rates
    - Debug worker performance issues
    - View job history for a worker
    - Check pending jobs before pausing/stopping worker

    **Query Parameters**:
    - `status` (optional): Filter jobs by status (pending, running, completed, failed)
    - `limit` (optional): Maximum results (1-1000, default: 100)
    - `offset` (optional): Skip first N results for pagination (default: 0)

    **Request Examples**:
    ```
    # Get all jobs for worker
    GET /api/v1/workers/worker_abc123/jobs

    # Get only running jobs
    GET /api/v1/workers/worker_abc123/jobs?status=running

    # Get completed jobs with pagination
    GET /api/v1/workers/worker_abc123/jobs?status=completed&limit=50&offset=0
    ```

    **Response Example**:
    ```json
    {
      "jobs": [
        {
          "job_id": "job_xyz789",
          "worker_id": "worker_abc123",
          "flow_id": "data_processing_flow",
          "status": "completed",
          "created_at": 1705312900,
          "started_at": 1705312901,
          "completed_at": 1705312950,
          "error": null,
          "metadata": {}
        },
        {
          "job_id": "job_abc456",
          "worker_id": "worker_abc123",
          "flow_id": "data_processing_flow",
          "status": "running",
          "created_at": 1705313000,
          "started_at": 1705313001,
          "completed_at": null,
          "error": null,
          "metadata": {}
        }
      ],
      "total": 2,
      "limit": 100,
      "offset": 0
    }
    ```

    **Job Status Values**:
    - `pending`: Job is queued but not yet started
    - `running`: Job is currently executing
    - `completed`: Job finished successfully
    - `failed`: Job encountered an error

    **Pagination**:
    - Use `limit` and `offset` for pagination
    - `total` indicates total number of jobs matching filters
    - Results are ordered by creation time (newest first)

    **Error Responses**:
    - `404 Not Found`: Worker with this ID does not exist

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id} - Get specific job details
    - GET /api/v1/workers/{worker_id} - Get worker information
    - POST /api/v1/jobs - Submit new job to worker

    Args:
        worker_id: Unique worker identifier
        status: Optional job status filter
        limit: Maximum jobs to return (1-1000)
        offset: Number of jobs to skip

    Returns:
        JobListResponse: Paginated list of jobs with total count

    Raises:
        HTTPException: 404 if worker not found
    """
    runtime = get_runtime()
    job_storage = get_job_storage()

    # Validate worker exists
    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    if worker_state is None:
        worker_registry = get_worker_registry()
        worker_state = worker_registry.get(worker_id)

    if worker_state is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_FOUND, f"Worker '{worker_id}' not found"
            ),
        )

    # Get jobs for this worker
    all_jobs = runtime.list_jobs(worker_id=worker_id)

    # Also check storage
    storage_jobs = job_storage.list_jobs(worker_id=worker_id)
    for job in storage_jobs:
        if job.job_id not in [j.job_id for j in all_jobs]:
            all_jobs.append(job)

    # Apply status filter
    if status:
        all_jobs = [j for j in all_jobs if j.status == status]

    total = len(all_jobs)
    jobs = all_jobs[offset : offset + limit]

    return JobListResponse(
        jobs=[_job_to_response(j, flow_id=worker_state.flow_id) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/workers/{worker_id}/statistics", dependencies=[RequireAuth])
async def get_worker_statistics(worker_id: str):
    """
    Get worker statistics including jobs processed, success rate, and routine statistics.

    **Overview**:
    Returns comprehensive statistics about a Worker's performance, including job counts,
    success rates, and per-routine execution statistics. Use this to monitor worker health,
    identify performance bottlenecks, and track execution patterns.

    **Endpoint**: `GET /api/v1/workers/{worker_id}/statistics`

    **Use Cases**:
    - Monitor worker performance and health
    - Calculate success rates and error rates
    - Identify slow or problematic routines
    - Track execution patterns over time
    - Build performance dashboards

    **Request Example**:
    ```
    GET /api/v1/workers/worker_abc123/statistics
    ```

    **Response Example**:
    ```json
    {
      "worker_id": "worker_abc123",
      "flow_id": "data_processing_flow",
      "jobs_processed": 100,
      "jobs_failed": 5,
      "success_rate": 0.95,
      "average_job_duration": null,
      "total_execution_time": null,
      "routine_statistics": {
        "data_source": {
          "execution_count": 100,
          "total_duration": 0.0,
          "avg_duration": 0.0,
          "error_count": 0
        },
        "data_processor": {
          "execution_count": 100,
          "total_duration": 0.0,
          "avg_duration": 0.0,
          "error_count": 2
        }
      }
    }
    ```

    **Response Fields**:
    - `worker_id`: Worker identifier
    - `flow_id`: Flow being executed
    - `jobs_processed`: Total number of jobs processed
    - `jobs_failed`: Total number of failed jobs
    - `success_rate`: Success rate (0.0 to 1.0)
    - `average_job_duration`: Average job duration in seconds (if available)
    - `total_execution_time`: Total execution time in seconds (if available)
    - `routine_statistics`: Per-routine statistics including execution count, duration, and errors

    **Routine Statistics**:
    Each routine includes:
    - `execution_count`: Number of times routine was executed
    - `total_duration`: Total execution time (if tracked)
    - `avg_duration`: Average execution time per call
    - `error_count`: Number of errors encountered

    **Error Responses**:
    - `404 Not Found`: Worker with this ID does not exist

    **Performance Note**:
    - Statistics are calculated from execution history
    - Some metrics (duration) may not be available if not tracked
    - Statistics reflect current worker state

    **Related Endpoints**:
    - GET /api/v1/workers/{worker_id} - Get worker details
    - GET /api/v1/workers/{worker_id}/history - Get detailed execution history
    - GET /api/v1/workers/{worker_id}/jobs - List jobs for worker

    Args:
        worker_id: Unique worker identifier

    Returns:
        dict: Worker statistics with job counts, success rate, and routine statistics

    Raises:
        HTTPException: 404 if worker not found
    """
    runtime = get_runtime()
    worker_registry = get_worker_registry()

    # Check active workers first
    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    # Fall back to registry
    if worker_state is None:
        worker_state = worker_registry.get(worker_id)

    if worker_state is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_FOUND, f"Worker '{worker_id}' not found"
            ),
        )

    # Calculate success rate
    total_jobs = worker_state.jobs_processed
    success_rate = (total_jobs - worker_state.jobs_failed) / total_jobs if total_jobs > 0 else 0.0

    # Get routine statistics from execution history
    routine_statistics = {}
    history = worker_state.get_execution_history()
    routine_counts = {}
    routine_durations = {}

    for record in history:
        rid = record.routine_id
        if rid not in routine_counts:
            routine_counts[rid] = 0
            routine_durations[rid] = []
        routine_counts[rid] += 1
        # Note: ExecutionRecord doesn't have duration, this is a placeholder
        # You may need to adjust based on actual ExecutionRecord structure

    for rid, count in routine_counts.items():
        routine_statistics[rid] = {
            "execution_count": count,
            "total_duration": sum(routine_durations.get(rid, [])),
            "avg_duration": (sum(routine_durations.get(rid, [])) / count if count > 0 else 0.0),
            "error_count": 0,  # Would need to track errors separately
        }

    return {
        "worker_id": worker_state.worker_id,
        "flow_id": worker_state.flow_id,
        "jobs_processed": worker_state.jobs_processed,
        "jobs_failed": worker_state.jobs_failed,
        "success_rate": success_rate,
        "average_job_duration": None,  # Would need to calculate from job history
        "total_execution_time": None,  # Would need to calculate from job history
        "routine_statistics": routine_statistics,
    }


@router.get("/workers/{worker_id}/history", dependencies=[RequireAuth])
async def get_worker_history(
    worker_id: str,
    routine_id: Optional[str] = Query(
        None,
        description="Filter by routine ID. Only execution records for this routine will be returned.",
        examples=["data_source"],
    ),
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of execution records to return. Range: 1-1000. Default: 100.",
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination. Default: 0.",
    ),
):
    """
    Get execution history for a worker.

    **Overview**:
    Returns a paginated list of execution history records for a Worker, showing all
    routine executions, events, and data flow. Use this to debug execution issues,
    trace data flow, and understand worker behavior.

    **Endpoint**: `GET /api/v1/workers/{worker_id}/history`

    **Use Cases**:
    - Debug execution issues
    - Trace data flow through routines
    - Understand worker behavior patterns
    - Audit routine executions
    - Analyze execution timing

    **Query Parameters**:
    - `routine_id` (optional): Filter by specific routine ID
    - `limit` (optional): Maximum records (1-1000, default: 100)
    - `offset` (optional): Skip first N records for pagination (default: 0)

    **Request Examples**:
    ```
    # Get all execution history
    GET /api/v1/workers/worker_abc123/history

    # Get history for specific routine
    GET /api/v1/workers/worker_abc123/history?routine_id=data_source

    # Get history with pagination
    GET /api/v1/workers/worker_abc123/history?limit=50&offset=0
    ```

    **Response Example**:
    ```json
    {
      "worker_id": "worker_abc123",
      "history": [
        {
          "routine_id": "data_source",
          "event_name": "routine_start",
          "data": {"input": "test"},
          "timestamp": "2025-01-15T10:00:00Z"
        },
        {
          "routine_id": "data_source",
          "event_name": "slot_call",
          "data": {"slot": "trigger", "value": "test"},
          "timestamp": "2025-01-15T10:00:01Z"
        },
        {
          "routine_id": "data_source",
          "event_name": "event_emit",
          "data": {"event": "output", "value": "processed"},
          "timestamp": "2025-01-15T10:00:02Z"
        }
      ],
      "total": 3,
      "limit": 100,
      "offset": 0
    }
    ```

    **History Record Fields**:
    - `routine_id`: Routine that generated this record
    - `event_name`: Type of event (routine_start, slot_call, event_emit, etc.)
    - `data`: Event-specific data payload
    - `timestamp`: ISO 8601 timestamp when event occurred

    **Event Types**:
    - `routine_start`: Routine execution started
    - `routine_end`: Routine execution completed
    - `slot_call`: Slot was called with data
    - `event_emit`: Event was emitted
    - Other event types as defined by routines

    **Pagination**:
    - Use `limit` and `offset` for pagination
    - `total` indicates total number of records matching filters
    - Results are ordered by timestamp (newest first)

    **Error Responses**:
    - `404 Not Found`: Worker with this ID does not exist

    **Performance Note**:
    - History is stored in worker state
    - Large histories may require pagination
    - Filtering by routine_id reduces response size

    **Related Endpoints**:
    - GET /api/v1/workers/{worker_id}/statistics - Get aggregated statistics
    - GET /api/v1/workers/{worker_id}/jobs - List jobs for worker
    - GET /api/v1/jobs/{job_id}/trace - Get job-specific trace

    Args:
        worker_id: Unique worker identifier
        routine_id: Optional routine ID filter
        limit: Maximum records to return (1-1000)
        offset: Number of records to skip

    Returns:
        dict: Execution history with pagination metadata

    Raises:
        HTTPException: 404 if worker not found
    """
    runtime = get_runtime()
    worker_registry = get_worker_registry()

    # Check active workers first
    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    # Fall back to registry
    if worker_state is None:
        worker_state = worker_registry.get(worker_id)

    if worker_state is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_FOUND, f"Worker '{worker_id}' not found"
            ),
        )

    history = worker_state.get_execution_history(routine_id=routine_id)
    total = len(history)
    history_page = history[offset : offset + limit]

    return {
        "worker_id": worker_id,
        "history": [
            {
                "routine_id": record.routine_id,
                "event_name": record.event_name,
                "data": record.data,
                "timestamp": record.timestamp.isoformat(),
            }
            for record in history_page
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/workers/{worker_id}/routines/states", dependencies=[RequireAuth])
async def get_worker_routine_states(worker_id: str):
    """
    Get routine states for all routines in a worker.

    **Overview**:
    Returns the current state of all routines in a Worker's flow. This includes routine
    configuration, activation status, and internal state. Use this to inspect routine
    state, debug issues, and understand routine behavior.

    **Endpoint**: `GET /api/v1/workers/{worker_id}/routines/states`

    **Use Cases**:
    - Inspect routine state during execution
    - Debug routine configuration issues
    - Monitor routine activation status
    - Understand routine internal state
    - Verify routine setup

    **Request Example**:
    ```
    GET /api/v1/workers/worker_abc123/routines/states
    ```

    **Response Example**:
    ```json
    {
      "data_source": {
        "routine_id": "data_source",
        "status": "active",
        "config": {"name": "Source"},
        "activation_policy": "immediate"
      },
      "data_processor": {
        "routine_id": "data_processor",
        "status": "active",
        "config": {"name": "Processor", "transformation": "uppercase"},
        "activation_policy": "immediate"
      }
    }
    ```

    **Response Structure**:
    - Dictionary mapping routine_id to routine state
    - Each routine state includes configuration, status, and activation policy
    - State structure depends on routine implementation

    **Error Responses**:
    - `404 Not Found`: Worker with this ID does not exist

    **Performance Note**:
    - Returns current state snapshot
    - State may change during execution
    - Large flows may return substantial data

    **Related Endpoints**:
    - GET /api/v1/workers/{worker_id} - Get worker details
    - GET /api/v1/flows/{flow_id}/routines - Get routine information from flow
    - GET /api/v1/workers/{worker_id}/history - Get execution history

    Args:
        worker_id: Unique worker identifier

    Returns:
        dict: Routine states indexed by routine_id

    Raises:
        HTTPException: 404 if worker not found
    """
    runtime = get_runtime()
    worker_registry = get_worker_registry()

    # Check active workers first
    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    # Fall back to registry
    if worker_state is None:
        worker_state = worker_registry.get(worker_id)

    if worker_state is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_FOUND, f"Worker '{worker_id}' not found"
            ),
        )

    return worker_state.routine_states


@router.put("/workers/{worker_id}/breakpoints/{breakpoint_id}", dependencies=[RequireAuth])
async def update_breakpoint_enabled(
    worker_id: str,
    breakpoint_id: str,
    request: BreakpointUpdateRequest,
):
    """
    Enable or disable a breakpoint for a worker.

    **Overview**:
    Enables or disables a breakpoint associated with a Worker. Breakpoints pause execution
    at specific points in the flow, allowing for debugging and inspection. This endpoint
    allows you to control breakpoint activation without removing the breakpoint.

    **Endpoint**: `PUT /api/v1/workers/{worker_id}/breakpoints/{breakpoint_id}`

    **Use Cases**:
    - Temporarily disable breakpoints without deleting them
    - Re-enable breakpoints for debugging
    - Control breakpoint activation during debugging sessions
    - Manage breakpoint state dynamically

    **Request Example**:
    ```json
    {
      "enabled": false
    }
    ```

    **Response Example**:
    ```json
    {
      "breakpoint_id": "bp_xyz789",
      "enabled": false,
      "updated_at": "2025-01-15T10:00:00Z"
    }
    ```

    **Breakpoint Types**:
    - `routine`: Pauses when routine is executed
    - `slot`: Pauses when slot is called
    - `event`: Pauses when event is emitted
    - `connection`: Pauses when data flows through connection

    **Behavior**:
    - When `enabled=true`: Breakpoint is active and will pause execution
    - When `enabled=false`: Breakpoint is inactive and execution continues normally
    - Changes take effect immediately for new executions

    **Error Responses**:
    - `404 Not Found`: Worker or breakpoint not found
    - `500 Internal Server Error`: Breakpoint manager not available

    **Best Practices**:
    1. Create breakpoints first: POST /api/jobs/{job_id}/breakpoints
    2. Use enable/disable to control breakpoint activation
    3. Disable breakpoints when not debugging to avoid performance impact
    4. Check breakpoint status: GET /api/jobs/{job_id}/breakpoints

    **Related Endpoints**:
    - POST /api/jobs/{job_id}/breakpoints - Create breakpoint
    - GET /api/jobs/{job_id}/breakpoints - List breakpoints
    - DELETE /api/jobs/{job_id}/breakpoints/{breakpoint_id} - Delete breakpoint

    Args:
        worker_id: Unique worker identifier
        breakpoint_id: Unique breakpoint identifier
        request: BreakpointUpdateRequest with enabled flag

    Returns:
        dict: Updated breakpoint information

    Raises:
        HTTPException: 404 if worker or breakpoint not found
        HTTPException: 500 if breakpoint manager unavailable
    """
    from routilux.monitoring.registry import MonitoringRegistry
    from routilux.server.dependencies import get_job_storage, get_runtime

    runtime = get_runtime()
    worker_registry = get_worker_registry()

    # Check active workers first
    with runtime._worker_lock:
        worker_state = runtime._active_workers.get(worker_id)

    # Fall back to registry
    if worker_state is None:
        worker_state = worker_registry.get(worker_id)

    if worker_state is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.WORKER_NOT_FOUND, f"Worker '{worker_id}' not found"
            ),
        )

    # Find breakpoint by ID (need to search through all jobs for this worker)
    registry = MonitoringRegistry.get_instance()
    breakpoint_mgr = registry.breakpoint_manager

    if not breakpoint_mgr:
        raise HTTPException(status_code=404, detail="Breakpoint manager not available")

    # Get all jobs for this worker
    job_storage = get_job_storage()
    jobs = job_storage.list_jobs(worker_id=worker_id)

    # Search for breakpoint across all jobs
    found_breakpoint = None
    for job in jobs:
        breakpoints = breakpoint_mgr.get_breakpoints(job.job_id)
        for bp in breakpoints:
            if bp.breakpoint_id == breakpoint_id:
                found_breakpoint = bp
                break
        if found_breakpoint:
            break

    if not found_breakpoint:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(
                ErrorCode.JOB_NOT_FOUND, f"Breakpoint '{breakpoint_id}' not found"
            ),
        )

    found_breakpoint.enabled = request.enabled

    return {
        "breakpoint_id": breakpoint_id,
        "enabled": request.enabled,
        "updated_at": datetime.now().isoformat(),
    }
