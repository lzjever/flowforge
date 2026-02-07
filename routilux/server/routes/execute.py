"""
One-shot execution API route.

Provides a simple endpoint to execute a flow with optional waiting.
"""

import asyncio
import logging
import time

from fastapi import APIRouter, HTTPException

from routilux.server.dependencies import (
    get_idempotency_backend,
    get_job_storage,
    get_runtime,
)
from routilux.server.errors import ErrorCode, create_error_response
from routilux.server.middleware.auth import RequireAuth
from routilux.server.models.execute import ExecuteRequest, ExecuteResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/execute", response_model=ExecuteResponse, dependencies=[RequireAuth])
async def execute_flow(request: ExecuteRequest):
    """
    One-shot flow execution.

    **Overview**:
    A convenience endpoint that combines worker creation, job submission, and optional
    waiting into a single operation. This is ideal for simple "submit and get result"
    workflows where you don't need persistent workers or complex job management.

    **Endpoint**: `POST /api/v1/execute`

    **Use Cases**:
    - Simple one-time job execution
    - Submit and wait for result patterns
    - Fire-and-forget job execution
    - Simple API integrations
    - Testing and development

    **Execution Modes**:

    **1. Async Mode** (`wait: false`):
    - Creates worker and submits job
    - Returns immediately with job information
    - Job executes in background
    - Use job_id to check status later

    **2. Sync Mode** (`wait: true`):
    - Creates worker and submits job
    - Waits for job completion (up to timeout)
    - Returns with job result or timeout status
    - Blocks until completion or timeout

    **Request Fields**:
    - `flow_id` (required): Flow to execute
    - `routine_id` (required): Entry point routine name
    - `slot_name` (required): Slot to trigger in the entry routine
    - `data` (required): Input data for the job
    - `wait` (optional): Whether to wait for completion (default: false)
    - `timeout` (optional): Timeout in seconds when wait=true (default: 60.0)
    - `metadata` (optional): Additional metadata for the job
    - `idempotency_key` (optional): Key for idempotent requests

    **Request Examples**:

    **Async execution**:
    ```json
    {
      "flow_id": "data_processing_flow",
      "routine_id": "data_source",
      "slot_name": "trigger",
      "data": {"value": 42},
      "wait": false
    }
    ```

    **Sync execution**:
    ```json
    {
      "flow_id": "data_processing_flow",
      "routine_id": "data_source",
      "slot_name": "trigger",
      "data": {"value": 42},
      "wait": true,
      "timeout": 30.0
    }
    ```

    **Response Examples**:

    **Async response**:
    ```json
    {
      "job_id": "job_xyz789",
      "worker_id": "worker_abc123",
      "status": "pending"
    }
    ```

    **Sync response (completed)**:
    ```json
    {
      "job_id": "job_xyz789",
      "worker_id": "worker_abc123",
      "status": "completed",
      "output": "Processing complete...",
      "result": {"processed": true},
      "error": null,
      "elapsed_seconds": 45.2
    }
    ```

    **Sync response (timeout)**:
    ```json
    {
      "job_id": "job_xyz789",
      "worker_id": "worker_abc123",
      "status": "timeout",
      "error": "Job did not complete within 30 seconds",
      "elapsed_seconds": 30.0
    }
    ```

    **Worker Creation**:
    - Always creates a new worker for each execution
    - Worker is created automatically and managed internally
    - Worker may be cleaned up after job completion

    **Idempotency**:
    - Provide `idempotency_key` to ensure duplicate requests return the same result
    - Idempotency cache is valid for 24 hours
    - Useful for retry scenarios

    **Error Responses**:
    - `404 Not Found`: Flow, routine, or slot not found
    - `400 Bad Request`: Execution failed (invalid data, runtime error)
    - `503 Service Unavailable`: Runtime is shutting down

    **When to Use**:
    - **Use this endpoint for**: Simple one-time executions, testing, simple integrations
    - **Use Worker/Job endpoints for**: Multiple jobs, persistent workers, complex workflows

    **Best Practices**:
    1. Use async mode for long-running jobs
    2. Use sync mode for quick jobs that need results
    3. Set appropriate timeout for sync mode
    4. Use idempotency keys for critical operations
    5. Check status if using async mode

    **Related Endpoints**:
    - POST /api/v1/jobs - Submit job to existing worker
    - POST /api/v1/workers - Create persistent worker
    - GET /api/v1/jobs/{job_id} - Check job status (for async mode)

    Args:
        request: ExecuteRequest with flow_id, routine_id, slot_name, data, and optional wait/timeout

    Returns:
        ExecuteResponse: Job information (async) or job result (sync)

    Raises:
        HTTPException: 404 if flow, routine, or slot not found
        HTTPException: 400 if execution fails
        HTTPException: 503 if runtime is shutting down
    """
    runtime = get_runtime()
    job_storage = get_job_storage()
    idempotency = get_idempotency_backend()

    start_time = time.time()

    # Check idempotency key
    if request.idempotency_key:
        cached = idempotency.get(request.idempotency_key)
        if cached is not None:
            return ExecuteResponse(**cached)

    try:
        # Submit job via Runtime.post() - this creates a new worker
        worker_state, job_context = runtime.post(
            flow_name=request.flow_id,
            routine_name=request.routine_id,
            slot_name=request.slot_name,
            data=request.data,
            worker_id=None,  # Always create new worker for one-shot
            metadata=request.metadata,
        )

        job_storage.save_job(job_context, flow_id=worker_state.flow_id)

        logger.info(f"Execute: created job {job_context.job_id} on worker {worker_state.worker_id}")

        if not request.wait:
            # Return immediately
            response = ExecuteResponse(
                job_id=job_context.job_id,
                worker_id=worker_state.worker_id,
                status=job_context.status,
            )

            if request.idempotency_key:
                idempotency.set(request.idempotency_key, response.model_dump(), ttl_seconds=86400)

            return response

        # Wait for completion
        timeout = request.timeout
        poll_interval = 0.1

        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout:
                response = ExecuteResponse(
                    job_id=job_context.job_id,
                    worker_id=worker_state.worker_id,
                    status="timeout",
                    error=f"Job did not complete within {timeout} seconds",
                    elapsed_seconds=elapsed,
                )

                if request.idempotency_key:
                    idempotency.set(
                        request.idempotency_key, response.model_dump(), ttl_seconds=86400
                    )

                return response

            # Check job status
            current_job = runtime.get_job(job_context.job_id)
            if current_job and current_job.status in ("completed", "failed"):
                # Get output
                output = None
                try:
                    from routilux.core.output import get_job_output

                    output = get_job_output(job_context.job_id, incremental=False)
                except Exception:
                    pass

                response = ExecuteResponse(
                    job_id=job_context.job_id,
                    worker_id=worker_state.worker_id,
                    status=current_job.status,
                    output=output if output else None,
                    result=current_job.data if current_job.data else None,
                    error=current_job.error,
                    elapsed_seconds=time.time() - start_time,
                )

                if request.idempotency_key:
                    idempotency.set(
                        request.idempotency_key, response.model_dump(), ttl_seconds=86400
                    )

                logger.info(
                    f"Execute: job {job_context.job_id} completed with status {current_job.status}"
                )
                return response

            await asyncio.sleep(poll_interval)

    except ValueError as e:
        error_msg = str(e)
        if "Flow" in error_msg:
            error_code = ErrorCode.FLOW_NOT_FOUND
        elif "Routine" in error_msg:
            error_code = ErrorCode.ROUTINE_NOT_FOUND
        elif "Slot" in error_msg:
            error_code = ErrorCode.SLOT_NOT_FOUND
        else:
            error_code = ErrorCode.JOB_SUBMISSION_FAILED

        raise HTTPException(status_code=404, detail=create_error_response(error_code, error_msg))
    except RuntimeError as e:
        if "shutdown" in str(e).lower():
            raise HTTPException(
                status_code=503, detail=create_error_response(ErrorCode.RUNTIME_SHUTDOWN, str(e))
            )
        raise HTTPException(
            status_code=400, detail=create_error_response(ErrorCode.JOB_SUBMISSION_FAILED, str(e))
        )
