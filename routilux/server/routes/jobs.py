"""
Job management API routes.

Jobs are single tasks/requests processed by Workers.
Each Job tracks one execution path through the workflow.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from routilux.core.context import JobContext
from routilux.monitoring.monitor_service import get_monitor_service
from routilux.monitoring.registry import MonitoringRegistry
from routilux.server.dependencies import (
    get_idempotency_backend,
    get_job_storage,
    get_runtime,
    get_worker_registry,
)
from routilux.server.errors import ErrorCode, create_error_response
from routilux.server.middleware.auth import RequireAuth
from routilux.server.models.job import (
    JobFailRequest,
    JobListResponse,
    JobOutputResponse,
    JobResponse,
    JobSubmitRequest,
    JobTraceResponse,
)
from routilux.server.models.monitor import (
    ExecutionEventResponse,
    ExecutionMetricsResponse,
    ExecutionTraceResponse,
    JobMonitoringData,
    RoutineExecutionStatus,
    RoutineMetricsResponse,
    SlotQueueStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _dt_to_int(dt: Optional[datetime]) -> Optional[int]:
    """Convert datetime to Unix timestamp."""
    if dt is None:
        return None
    return int(dt.timestamp())


def _job_to_response(job_context: JobContext, flow_id: str = "") -> JobResponse:
    """Convert JobContext to API response."""
    # Get flow_id from worker if not provided
    if not flow_id:
        try:
            worker_registry = get_worker_registry()
            worker = worker_registry.get(job_context.worker_id)
            if worker:
                flow_id = worker.flow_id
        except Exception:
            pass

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


@router.post("/jobs", response_model=JobResponse, status_code=201, dependencies=[RequireAuth])
async def submit_job(request: JobSubmitRequest):
    """
    Submit a new Job to a Worker.

    **Overview**:
    Submits a new Job for processing. If a worker_id is provided, the job is submitted to
    that worker. If not provided, a new Worker is automatically created for the flow.
    Each job submission creates a new JobContext that tracks this specific task execution.

    **Endpoint**: `POST /api/v1/jobs`

    **Use Cases**:
    - Submit jobs to existing workers
    - Create workers on-demand by submitting jobs
    - Process data through flows
    - Trigger workflow executions
    - Build job queues

    **Request Fields**:
    - `flow_id` (required): Flow to execute
    - `routine_id` (required): Entry point routine name
    - `slot_name` (required): Slot to trigger in the entry routine
    - `data` (required): Input data for the job
    - `worker_id` (optional): Existing worker ID (creates new worker if not provided)
    - `job_id` (optional): Custom job ID (auto-generated if not provided)
    - `metadata` (optional): Additional metadata for the job
    - `idempotency_key` (optional): Key for idempotent requests

    **Request Examples**:

    **Submit to existing worker**:
    ```json
    {
      "flow_id": "data_processing_flow",
      "routine_id": "data_source",
      "slot_name": "trigger",
      "data": {"value": 42},
      "worker_id": "worker_abc123",
      "metadata": {"source": "api", "priority": "high"}
    }
    ```

    **Create new worker automatically**:
    ```json
    {
      "flow_id": "data_processing_flow",
      "routine_id": "data_source",
      "slot_name": "trigger",
      "data": {"value": 42}
    }
    ```

    **With idempotency key**:
    ```json
    {
      "flow_id": "data_processing_flow",
      "routine_id": "data_source",
      "slot_name": "trigger",
      "data": {"value": 42},
      "idempotency_key": "unique-request-id-123"
    }
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "worker_id": "worker_abc123",
      "flow_id": "data_processing_flow",
      "status": "pending",
      "created_at": 1705312800,
      "started_at": null,
      "completed_at": null,
      "error": null,
      "metadata": {"source": "api", "priority": "high"}
    }
    ```

    **Worker Creation**:
    - If `worker_id` is not provided, a new Worker is created automatically
    - The new worker is started immediately and can process multiple jobs
    - Use existing workers for better resource management

    **Idempotency**:
    - Provide `idempotency_key` to ensure duplicate requests return the same job
    - Idempotency cache is valid for 24 hours
    - Useful for retry scenarios and preventing duplicate job submissions

    **Error Responses**:
    - `404 Not Found`: Flow, routine, slot, or worker not found
    - `400 Bad Request`: Job submission failed (invalid data, runtime error)
    - `503 Service Unavailable`: Runtime is shutting down

    **Best Practices**:
    1. Reuse workers for multiple jobs to improve efficiency
    2. Use idempotency keys for critical operations
    3. Monitor job status: GET /api/v1/jobs/{job_id}
    4. Use metadata to track job context and source
    5. Check worker status before submitting: GET /api/v1/workers/{worker_id}

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id} - Get job details
    - GET /api/v1/jobs/{job_id}/status - Get job status (lightweight)
    - POST /api/v1/jobs/{job_id}/wait - Wait for job completion
    - GET /api/v1/workers/{worker_id}/jobs - List jobs for worker
    - POST /api/v1/execute - One-shot execution (alternative)

    Args:
        request: JobSubmitRequest with flow_id, routine_id, slot_name, data, and optional fields

    Returns:
        JobResponse: Created job information with status

    Raises:
        HTTPException: 404 if flow, routine, slot, or worker not found
        HTTPException: 400 if job submission fails
        HTTPException: 503 if runtime is shutting down
    """
    runtime = get_runtime()
    job_storage = get_job_storage()
    idempotency = get_idempotency_backend()

    # Check idempotency key
    if request.idempotency_key:
        cached = idempotency.get(request.idempotency_key)
        if cached is not None:
            return JobResponse(**cached)

    try:
        # Submit via Runtime.post()
        worker_state, job_context = runtime.post(
            flow_name=request.flow_id,
            routine_name=request.routine_id,
            slot_name=request.slot_name,
            data=request.data,
            worker_id=request.worker_id,
            job_id=request.job_id,
            metadata=request.metadata,
        )

        # Store job for API access
        job_storage.save_job(job_context, flow_id=worker_state.flow_id)

        response = _job_to_response(job_context, flow_id=worker_state.flow_id)

        # Update idempotency cache
        if request.idempotency_key:
            idempotency.set(request.idempotency_key, response.model_dump(), ttl_seconds=86400)

        logger.info(f"Submitted job {job_context.job_id} to worker {worker_state.worker_id}")
        return response

    except ValueError as e:
        error_msg = str(e)
        if "Flow" in error_msg:
            error_code = ErrorCode.FLOW_NOT_FOUND
        elif "Routine" in error_msg:
            error_code = ErrorCode.ROUTINE_NOT_FOUND
        elif "Slot" in error_msg:
            error_code = ErrorCode.SLOT_NOT_FOUND
        elif "Worker" in error_msg:
            error_code = ErrorCode.WORKER_NOT_FOUND
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


@router.get("/jobs", response_model=JobListResponse, dependencies=[RequireAuth])
async def list_jobs(
    worker_id: Optional[str] = Query(None, description="Filter by worker ID"),
    flow_id: Optional[str] = Query(None, description="Filter by flow ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
):
    """
    List all Jobs with optional filters.

    **Query Parameters**:
    - `worker_id`: Filter by specific worker
    - `flow_id`: Filter by flow being executed
    - `status`: Filter by job status (pending, running, completed, failed)
    - `limit`: Maximum results (1-1000, default 100)
    - `offset`: Skip first N results (for pagination)
    """
    job_storage = get_job_storage()

    all_jobs = job_storage.list_jobs(
        worker_id=worker_id,
        flow_id=flow_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    total = job_storage.count_jobs(
        worker_id=worker_id,
        flow_id=flow_id,
        status=status,
    )

    # Get flow_id for each job
    responses = []
    for job in all_jobs:
        flow = job_storage.get_flow_id(job.job_id) or ""
        responses.append(_job_to_response(job, flow_id=flow))

    return JobListResponse(
        jobs=responses,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse, dependencies=[RequireAuth])
async def get_job(job_id: str):
    """
    Get Job details by ID.

    **Overview**:
    Returns complete information about a specific Job, including its status, lifecycle
    timestamps, error information, and metadata. Use this to check job progress, inspect
    job state, and debug job issues.

    **Endpoint**: `GET /api/v1/jobs/{job_id}`

    **Use Cases**:
    - Check job status and progress
    - Inspect job metadata and configuration
    - Debug failed jobs
    - Track job lifecycle
    - Monitor job execution

    **Request Example**:
    ```
    GET /api/v1/jobs/job_xyz789
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "worker_id": "worker_abc123",
      "flow_id": "data_processing_flow",
      "status": "completed",
      "created_at": 1705312800,
      "started_at": 1705312801,
      "completed_at": 1705312950,
      "error": null,
      "metadata": {"source": "api", "priority": "high"}
    }
    ```

    **Job Status Values**:
    - `pending`: Job is queued but not yet started
    - `running`: Job is currently executing
    - `completed`: Job finished successfully
    - `failed`: Job encountered an error

    **Response Fields**:
    - `job_id`: Unique job identifier
    - `worker_id`: Worker processing this job
    - `flow_id`: Flow being executed
    - `status`: Current job status
    - `created_at`: Unix timestamp when job was created
    - `started_at`: Unix timestamp when job started (null if pending)
    - `completed_at`: Unix timestamp when job completed (null if not completed)
    - `error`: Error message if job failed (null if successful)
    - `metadata`: Additional metadata provided during submission

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id}/status - Get lightweight status only
    - GET /api/v1/jobs/{job_id}/output - Get job output
    - GET /api/v1/jobs/{job_id}/trace - Get execution trace
    - GET /api/v1/jobs/{job_id}/metrics - Get execution metrics
    - POST /api/v1/jobs/{job_id}/wait - Wait for completion

    Args:
        job_id: Unique job identifier

    Returns:
        JobResponse: Complete job information

    Raises:
        HTTPException: 404 if job not found
    """
    runtime = get_runtime()
    job_storage = get_job_storage()

    # Check storage first
    job_context = job_storage.get_job(job_id)

    # Fall back to Runtime
    if job_context is None:
        job_context = runtime.get_job(job_id)

    if job_context is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    flow_id = job_storage.get_flow_id(job_id) or ""
    return _job_to_response(job_context, flow_id=flow_id)


@router.get("/jobs/{job_id}/output", response_model=JobOutputResponse, dependencies=[RequireAuth])
async def get_job_output(
    job_id: str,
    incremental: bool = Query(
        False,
        description="Return only new output since last call. Use true for streaming output. Default: false (return all output).",
    ),
):
    """
    Get captured stdout output for a Job.

    **Overview**:
    Returns the captured stdout/stderr output from a Job's execution. This includes all
    print statements, logging output, and error messages generated during job execution.
    Use this to debug jobs, monitor progress, and inspect execution logs.

    **Endpoint**: `GET /api/v1/jobs/{job_id}/output`

    **Use Cases**:
    - Debug job execution issues
    - Monitor job progress in real-time
    - Inspect logging output
    - View error messages and stack traces
    - Stream output for long-running jobs

    **Query Parameters**:
    - `incremental` (optional): If true, returns only new output since last call. Default: false.

    **Request Examples**:
    ```
    # Get all output
    GET /api/v1/jobs/job_xyz789/output

    # Get incremental output (for streaming)
    GET /api/v1/jobs/job_xyz789/output?incremental=true
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "output": "Processing data...\nData processed successfully\n",
      "is_complete": true,
      "truncated": false
    }
    ```

    **Response Fields**:
    - `job_id`: Job identifier
    - `output`: Captured stdout/stderr output as string
    - `is_complete`: Whether job has completed (true if status is completed or failed)
    - `truncated`: Whether output was truncated (true if output exceeds 200KB)

    **Incremental Mode**:
    - Use `incremental=true` for streaming output from running jobs
    - Each call returns only new output since the previous call
    - Useful for real-time monitoring and progress tracking
    - Output is tracked per job, so multiple clients can stream independently

    **Output Limits**:
    - Output is truncated if it exceeds 200KB
    - `truncated` field indicates if output was truncated
    - For very large outputs, consider using logs endpoint instead

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist

    **Best Practices**:
    1. Use incremental mode for long-running jobs
    2. Poll regularly when using incremental mode
    3. Check `is_complete` to know when to stop polling
    4. Use GET /api/v1/jobs/{job_id}/logs for structured logs

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id}/logs - Get structured execution logs
    - GET /api/v1/jobs/{job_id}/trace - Get execution trace
    - GET /api/v1/jobs/{job_id} - Get job status

    Args:
        job_id: Unique job identifier
        incremental: Return only new output since last call

    Returns:
        JobOutputResponse: Job output with completion status

    Raises:
        HTTPException: 404 if job not found
    """
    runtime = get_runtime()
    job_storage = get_job_storage()

    # Get job
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)

    if job_context is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    # Get output from RoutedStdout
    try:
        from routilux.core.output import get_job_output as core_get_output

        output = core_get_output(job_id, incremental=incremental)
    except ImportError:
        output = ""
    except Exception as e:
        logger.warning(f"Failed to get output for job {job_id}: {e}")
        output = ""

    return JobOutputResponse(
        job_id=job_id,
        output=output,
        is_complete=job_context.status in ("completed", "failed"),
        truncated=len(output) >= 200000,
    )


@router.get("/jobs/{job_id}/trace", response_model=JobTraceResponse, dependencies=[RequireAuth])
async def get_job_trace(job_id: str):
    """
    Get execution trace for a Job.

    **Overview**:
    Returns the trace_log entries recorded during job execution. The trace log contains
    detailed execution information including routine calls, data flow, and execution
    context. Use this to debug execution flow, trace data transformations, and understand
    job behavior.

    **Endpoint**: `GET /api/v1/jobs/{job_id}/trace`

    **Use Cases**:
    - Debug execution flow issues
    - Trace data transformations
    - Understand routine execution order
    - Inspect execution context
    - Audit job execution

    **Request Example**:
    ```
    GET /api/v1/jobs/job_xyz789/trace
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "trace_log": [
        "Job started: job_xyz789",
        "Routine data_source: slot trigger called",
        "Routine data_source: event output emitted",
        "Routine data_processor: slot input called",
        "Routine data_processor: event output emitted",
        "Job completed: job_xyz789"
      ],
      "total_entries": 6
    }
    ```

    **Trace Log Format**:
    - Each entry is a string describing an execution event
    - Entries are ordered chronologically
    - Format depends on trace implementation
    - May include routine names, slot/event names, and data summaries

    **Trace vs Execution Trace**:
    - This endpoint returns `trace_log` from JobContext (high-level trace)
    - GET /api/v1/jobs/{job_id}/execution-trace returns detailed events from MonitorCollector
    - Use this endpoint for quick overview, execution-trace for detailed analysis

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id}/execution-trace - Get detailed execution trace
    - GET /api/v1/jobs/{job_id}/logs - Get structured execution logs
    - GET /api/v1/jobs/{job_id}/metrics - Get execution metrics

    Args:
        job_id: Unique job identifier

    Returns:
        JobTraceResponse: Trace log entries with total count

    Raises:
        HTTPException: 404 if job not found
    """
    runtime = get_runtime()
    job_storage = get_job_storage()

    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)

    if job_context is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    return JobTraceResponse(
        job_id=job_id,
        trace_log=job_context.trace_log,
        total_entries=len(job_context.trace_log),
    )


@router.get(
    "/jobs/{job_id}/metrics", response_model=ExecutionMetricsResponse, dependencies=[RequireAuth]
)
async def get_job_metrics(job_id: str):
    """
    Get execution metrics for a job.

    **Overview**:
    Returns comprehensive execution metrics for a Job, including routine-level statistics,
    execution duration, event counts, and error information. Use this to analyze performance,
    identify bottlenecks, and monitor job health.

    **Endpoint**: `GET /api/v1/jobs/{job_id}/metrics`

    **Use Cases**:
    - Analyze job performance
    - Identify slow routines
    - Track execution statistics
    - Monitor error rates
    - Build performance dashboards

    **Request Example**:
    ```
    GET /api/v1/jobs/job_xyz789/metrics
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "flow_id": "data_processing_flow",
      "start_time": "2025-01-15T10:00:00Z",
      "end_time": "2025-01-15T10:00:50Z",
      "duration": 50.5,
      "routine_metrics": {
        "data_source": {
          "routine_id": "data_source",
          "execution_count": 1,
          "total_duration": 10.2,
          "avg_duration": 10.2,
          "min_duration": 10.2,
          "max_duration": 10.2,
          "error_count": 0,
          "last_execution": "2025-01-15T10:00:10Z"
        }
      },
      "total_events": 15,
      "total_slot_calls": 10,
      "total_event_emits": 5,
      "errors": []
    }
    ```

    **Metrics Fields**:
    - `job_id`: Job identifier
    - `flow_id`: Flow being executed
    - `start_time`: Job start timestamp
    - `end_time`: Job end timestamp (null if still running)
    - `duration`: Total execution duration in seconds
    - `routine_metrics`: Per-routine statistics
    - `total_events`: Total number of execution events
    - `total_slot_calls`: Total number of slot calls
    - `total_event_emits`: Total number of event emissions
    - `errors`: List of error records

    **Routine Metrics**:
    Each routine includes:
    - `execution_count`: Number of times routine was executed
    - `total_duration`: Total execution time
    - `avg_duration`: Average execution time per call
    - `min_duration` / `max_duration`: Execution time bounds
    - `error_count`: Number of errors encountered
    - `last_execution`: Timestamp of last execution

    **Error Responses**:
    - `404 Not Found`: Job not found or no metrics available
    - `500 Internal Server Error`: Monitor collector not available

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id}/execution-trace - Get detailed execution trace
    - GET /api/v1/jobs/{job_id}/monitoring - Get complete monitoring data
    - GET /api/v1/jobs/{job_id}/routines/status - Get routine execution status

    Args:
        job_id: Unique job identifier

    Returns:
        ExecutionMetricsResponse: Comprehensive execution metrics

    Raises:
        HTTPException: 404 if job not found or metrics unavailable
        HTTPException: 500 if monitor collector unavailable
    """
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    registry = MonitoringRegistry.get_instance()
    collector = registry.monitor_collector

    if not collector:
        raise HTTPException(status_code=500, detail="Monitor collector not available")

    metrics = collector.get_metrics(job_id)
    if not metrics:
        raise HTTPException(status_code=404, detail=f"No metrics found for job '{job_id}'")

    # Convert to response model
    routine_metrics = {
        rid: RoutineMetricsResponse(
            routine_id=rm.routine_id,
            execution_count=rm.execution_count,
            total_duration=rm.total_duration,
            avg_duration=rm.avg_duration,
            min_duration=rm.min_duration,
            max_duration=rm.max_duration,
            error_count=rm.error_count,
            last_execution=rm.last_execution,
        )
        for rid, rm in metrics.routine_metrics.items()
    }

    # Convert ErrorRecord objects to dictionaries
    errors = [
        {
            "error_id": err.error_id,
            "job_id": err.job_id,
            "routine_id": err.routine_id,
            "timestamp": err.timestamp.isoformat(),
            "error_type": err.error_type,
            "error_message": err.error_message,
            "traceback": err.traceback,
        }
        for err in metrics.errors
    ]

    return ExecutionMetricsResponse(
        job_id=metrics.job_id,
        flow_id=metrics.flow_id,
        start_time=metrics.start_time if metrics.start_time else datetime.now(),
        end_time=metrics.end_time,
        duration=metrics.duration,
        routine_metrics=routine_metrics,
        total_events=metrics.total_events,
        total_slot_calls=metrics.total_slot_calls,
        total_event_emits=metrics.total_event_emits,
        errors=errors,
    )


@router.get(
    "/jobs/{job_id}/execution-trace",
    response_model=ExecutionTraceResponse,
    dependencies=[RequireAuth],
)
async def get_job_execution_trace(
    job_id: str,
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=10000,
        description="Maximum number of trace events to return. Range: 1-10000. Default: all events.",
    ),
):
    """
    Get execution trace for a job (from MonitorCollector).

    **Overview**:
    Returns detailed execution trace events from the MonitorCollector, providing fine-grained
    visibility into job execution. This includes all routine executions, slot calls, event
    emissions, and their timing. Use this for detailed debugging and performance analysis.

    **Endpoint**: `GET /api/v1/jobs/{job_id}/execution-trace`

    **Use Cases**:
    - Detailed execution debugging
    - Performance analysis and profiling
    - Trace data flow through routines
    - Understand execution timing
    - Audit complete execution history

    **Query Parameters**:
    - `limit` (optional): Maximum number of events to return (1-10000). Default: all events.

    **Request Examples**:
    ```
    # Get all trace events
    GET /api/v1/jobs/job_xyz789/execution-trace

    # Get last 100 events
    GET /api/v1/jobs/job_xyz789/execution-trace?limit=100
    ```

    **Response Example**:
    ```json
    {
      "events": [
        {
          "event_id": "evt_001",
          "job_id": "job_xyz789",
          "routine_id": "data_source",
          "event_type": "routine_start",
          "timestamp": "2025-01-15T10:00:00Z",
          "data": {"input": "test"},
          "duration": null,
          "status": "started"
        },
        {
          "event_id": "evt_002",
          "job_id": "job_xyz789",
          "routine_id": "data_source",
          "event_type": "slot_call",
          "timestamp": "2025-01-15T10:00:01Z",
          "data": {"slot": "trigger", "value": "test"},
          "duration": 0.5,
          "status": "completed"
        }
      ],
      "total": 2
    }
    ```

    **Event Types**:
    - `routine_start`: Routine execution started
    - `routine_end`: Routine execution completed
    - `slot_call`: Slot was called with data
    - `event_emit`: Event was emitted
    - Other event types as defined by monitoring system

    **Event Fields**:
    - `event_id`: Unique event identifier
    - `job_id`: Job identifier
    - `routine_id`: Routine that generated the event
    - `event_type`: Type of event
    - `timestamp`: Event timestamp
    - `data`: Event-specific data payload
    - `duration`: Event duration in seconds (if applicable)
    - `status`: Event status (started, completed, failed, etc.)

    **Trace vs Trace Log**:
    - This endpoint returns detailed events from MonitorCollector (fine-grained)
    - GET /api/v1/jobs/{job_id}/trace returns high-level trace_log from JobContext
    - Use this endpoint for detailed analysis, trace for quick overview

    **Error Responses**:
    - `404 Not Found`: Job not found or no trace available
    - `500 Internal Server Error`: Monitor collector not available

    **Performance Note**:
    - Large traces may require pagination (use limit parameter)
    - Events are ordered chronologically
    - Limit parameter helps manage response size

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id}/trace - Get high-level trace log
    - GET /api/v1/jobs/{job_id}/metrics - Get aggregated metrics
    - GET /api/v1/jobs/{job_id}/monitoring - Get complete monitoring data

    Args:
        job_id: Unique job identifier
        limit: Maximum number of events to return (1-10000)

    Returns:
        ExecutionTraceResponse: Detailed execution trace events

    Raises:
        HTTPException: 404 if job not found or trace unavailable
        HTTPException: 500 if monitor collector unavailable
    """
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    registry = MonitoringRegistry.get_instance()
    collector = registry.monitor_collector

    if not collector:
        raise HTTPException(status_code=500, detail="Monitor collector not available")

    events = collector.get_execution_trace(job_id, limit)

    event_responses = [
        ExecutionEventResponse(
            event_id=event.event_id,
            job_id=event.job_id,
            routine_id=event.routine_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            data=event.data,
            duration=event.duration,
            status=event.status,
        )
        for event in events
    ]

    return ExecutionTraceResponse(
        events=event_responses,
        total=len(event_responses),
    )


@router.get("/jobs/{job_id}/logs", dependencies=[RequireAuth])
async def get_job_logs(job_id: str):
    """
    Get execution logs for a job.

    **Overview**:
    Returns structured execution logs from a Job's trace_log. This provides a structured
    view of execution events, making it easier to parse and analyze than raw output.

    **Endpoint**: `GET /api/v1/jobs/{job_id}/logs`

    **Use Cases**:
    - Parse structured execution logs
    - Analyze execution patterns
    - Build log analysis tools
    - Extract specific log entries
    - Debug execution flow

    **Request Example**:
    ```
    GET /api/v1/jobs/job_xyz789/logs
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "logs": [
        "Job started: job_xyz789",
        "Routine data_source: slot trigger called",
        "Routine data_source: event output emitted",
        "Job completed: job_xyz789"
      ],
      "total": 4
    }
    ```

    **Response Fields**:
    - `job_id`: Job identifier
    - `logs`: Array of log entry strings
    - `total`: Total number of log entries

    **Log Format**:
    - Each log entry is a string describing an execution event
    - Format depends on trace implementation
    - Entries are ordered chronologically
    - May include routine names, slot/event names, and execution context

    **Logs vs Output**:
    - **Logs**: Structured trace_log entries (this endpoint)
    - **Output**: Raw stdout/stderr output (GET /api/v1/jobs/{job_id}/output)

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id}/trace - Get trace log (same data, different format)
    - GET /api/v1/jobs/{job_id}/output - Get raw output
    - GET /api/v1/jobs/{job_id}/execution-trace - Get detailed execution trace

    Args:
        job_id: Unique job identifier

    Returns:
        dict: Execution logs with total count

    Raises:
        HTTPException: 404 if job not found
    """
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    logs = getattr(job_context, "trace_log", [])

    return {
        "job_id": job_id,
        "logs": logs,
        "total": len(logs),
    }


@router.get("/jobs/{job_id}/data", dependencies=[RequireAuth])
async def get_job_data(job_id: str):
    """
    Get job-level data.

    **Overview**:
    Returns the job-level data stored in the JobContext. This is the data associated
    with the job execution, which may include input data, intermediate results, or
    final output depending on the flow implementation.

    **Endpoint**: `GET /api/v1/jobs/{job_id}/data`

    **Use Cases**:
    - Retrieve job execution data
    - Access job results
    - Inspect job state
    - Extract job output
    - Debug data transformations

    **Request Example**:
    ```
    GET /api/v1/jobs/job_xyz789/data
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "data": {
        "input": {"value": 42},
        "processed": true,
        "result": {"output": 84}
      }
    }
    ```

    **Response Fields**:
    - `job_id`: Job identifier
    - `data`: Job data object (structure depends on flow implementation)

    **Data Structure**:
    - Data structure is determined by the flow implementation
    - May contain input data, intermediate results, or final output
    - Structure may change during job execution
    - Use flow documentation to understand expected structure

    **Data vs Result**:
    - **Data**: JobContext.data (this endpoint) - may include intermediate state
    - **Result**: Final job result (in ExecuteResponse when using execute endpoint)

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id} - Get complete job information
    - POST /api/v1/execute - One-shot execution with result
    - GET /api/v1/jobs/{job_id}/output - Get stdout/stderr output

    Args:
        job_id: Unique job identifier

    Returns:
        dict: Job data with job_id

    Raises:
        HTTPException: 404 if job not found
    """
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    return {
        "job_id": job_id,
        "data": job_context.data,
    }


@router.get(
    "/jobs/{job_id}/monitoring",
    response_model=JobMonitoringData,
    dependencies=[RequireAuth],
)
async def get_job_monitoring_data(job_id: str):
    """Get complete monitoring data for a job."""
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    service = get_monitor_service()
    try:
        return service.get_job_monitoring_data(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, str(e)),
        )


@router.get(
    "/jobs/{job_id}/routines/status",
    response_model=Dict[str, RoutineExecutionStatus],
    dependencies=[RequireAuth],
)
async def get_routines_status(job_id: str):
    """Get execution status for all routines in a job."""
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    service = get_monitor_service()
    try:
        return service.get_all_routines_status(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, str(e)),
        )


@router.get(
    "/jobs/{job_id}/routines/{routine_id}/queue-status",
    response_model=List[SlotQueueStatus],
    dependencies=[RequireAuth],
)
async def get_routine_queue_status(job_id: str, routine_id: str):
    """Get queue status for all slots in a specific routine."""
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    service = get_monitor_service()
    try:
        return service.get_routine_queue_status(job_id, routine_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, str(e)),
        )


@router.get(
    "/jobs/{job_id}/queues/status",
    response_model=Dict[str, List[SlotQueueStatus]],
    dependencies=[RequireAuth],
)
async def get_job_queues_status(job_id: str):
    """Get queue status for all routines in a job."""
    from routilux.server.dependencies import get_job_storage, get_runtime

    job_storage = get_job_storage()
    runtime = get_runtime()
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    if not job_context:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    service = get_monitor_service()
    try:
        return service.get_all_queues_status(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, str(e)),
        )


@router.post("/jobs/{job_id}/complete", response_model=JobResponse, dependencies=[RequireAuth])
async def complete_job(job_id: str):
    """
    Mark a Job as completed.

    **Overview**:
    Explicitly marks a job as completed, transitioning it to a terminal state.
    Use this when you need to manually signal that job processing is complete,
    or when the flow doesn't automatically mark jobs as complete.

    **Endpoint**: `POST /api/v1/jobs/{job_id}/complete`

    **Use Cases**:
    - Manually complete jobs
    - Signal completion for custom flows
    - Force job completion
    - Handle edge cases where auto-completion fails
    - Integrate with external completion signals

    **Request Example**:
    ```
    POST /api/v1/jobs/job_xyz789/complete
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "worker_id": "worker_abc123",
      "flow_id": "data_processing_flow",
      "status": "completed",
      "created_at": 1705312800,
      "started_at": 1705312801,
      "completed_at": 1705312950,
      "error": null,
      "metadata": {}
    }
    ```

    **Behavior**:
    - Transitions job status to "completed"
    - Sets completed_at timestamp
    - Job enters terminal state (cannot be restarted)
    - Updates job in both Runtime and storage

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist
    - `400 Bad Request`: Job is already in terminal state (completed or failed)

    **Job States**:
    - Can complete: `pending`, `running`
    - Cannot complete: `completed`, `failed` (already in terminal state)

    **Best Practices**:
    1. Only use when necessary (most flows auto-complete)
    2. Verify job is actually done before completing
    3. Check job status first: GET /api/v1/jobs/{job_id}
    4. Use for custom flows that don't auto-complete

    **Related Endpoints**:
    - POST /api/v1/jobs/{job_id}/fail - Mark job as failed
    - GET /api/v1/jobs/{job_id} - Check job status
    - GET /api/v1/jobs/{job_id}/status - Get lightweight status

    Args:
        job_id: Unique job identifier

    Returns:
        JobResponse: Updated job information with completed status

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 400 if job already in terminal state
    """
    runtime = get_runtime()
    job_storage = get_job_storage()

    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)

    if job_context is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    if job_context.status in ("completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                ErrorCode.JOB_ALREADY_COMPLETED,
                f"Job '{job_id}' is already in terminal state: {job_context.status}",
            ),
        )

    # Try Runtime.complete_job first
    success = runtime.complete_job(job_id, status="completed")

    if not success:
        # Job not in Runtime, update directly
        job_context.complete(status="completed")
        job_storage.save_job(job_context)

    # Refresh job context
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    flow_id = job_storage.get_flow_id(job_id) or ""

    logger.info(f"Completed job {job_id}")
    return _job_to_response(job_context, flow_id=flow_id)


@router.post("/jobs/{job_id}/fail", response_model=JobResponse, dependencies=[RequireAuth])
async def fail_job(job_id: str, request: JobFailRequest):
    """
    Mark a Job as failed.

    **Overview**:
    Explicitly marks a job as failed with an error message, transitioning it to a
    terminal state. Use this when you need to manually signal that job processing
    has failed, or when handling errors that don't automatically fail the job.

    **Endpoint**: `POST /api/v1/jobs/{job_id}/fail`

    **Use Cases**:
    - Manually fail jobs
    - Signal failure for custom flows
    - Handle external error conditions
    - Force job failure for testing
    - Integrate with external error handling

    **Request Example**:
    ```json
    {
      "error": "Processing failed: invalid input data"
    }
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "worker_id": "worker_abc123",
      "flow_id": "data_processing_flow",
      "status": "failed",
      "created_at": 1705312800,
      "started_at": 1705312801,
      "completed_at": 1705312900,
      "error": "Processing failed: invalid input data",
      "metadata": {}
    }
    ```

    **Request Fields**:
    - `error` (required): Error message describing the failure

    **Behavior**:
    - Transitions job status to "failed"
    - Sets completed_at timestamp
    - Stores error message
    - Job enters terminal state (cannot be restarted)
    - Updates job in both Runtime and storage

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist
    - `400 Bad Request`: Job is already in terminal state (completed or failed)

    **Job States**:
    - Can fail: `pending`, `running`
    - Cannot fail: `completed`, `failed` (already in terminal state)

    **Best Practices**:
    1. Provide clear, descriptive error messages
    2. Only use when necessary (most flows auto-fail on errors)
    3. Verify job has actually failed before marking
    4. Check job status first: GET /api/v1/jobs/{job_id}
    5. Use for custom error handling scenarios

    **Related Endpoints**:
    - POST /api/v1/jobs/{job_id}/complete - Mark job as completed
    - GET /api/v1/jobs/{job_id} - Check job status
    - GET /api/v1/jobs/{job_id}/status - Get lightweight status

    Args:
        job_id: Unique job identifier
        request: JobFailRequest with error message

    Returns:
        JobResponse: Updated job information with failed status

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 400 if job already in terminal state
    """
    runtime = get_runtime()
    job_storage = get_job_storage()

    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)

    if job_context is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    if job_context.status in ("completed", "failed"):
        raise HTTPException(
            status_code=400,
            detail=create_error_response(
                ErrorCode.JOB_ALREADY_COMPLETED,
                f"Job '{job_id}' is already in terminal state: {job_context.status}",
            ),
        )

    # Try Runtime.complete_job first
    success = runtime.complete_job(job_id, status="failed", error=request.error)

    if not success:
        # Job not in Runtime, update directly
        job_context.complete(status="failed", error=request.error)
        job_storage.save_job(job_context)

    # Refresh job context
    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)
    flow_id = job_storage.get_flow_id(job_id) or ""

    logger.info(f"Failed job {job_id}: {request.error}")
    return _job_to_response(job_context, flow_id=flow_id)


@router.get("/jobs/{job_id}/status", dependencies=[RequireAuth])
async def get_job_status(job_id: str):
    """
    Get current status of a Job (lightweight endpoint).

    **Overview**:
    Returns minimal job status information optimized for frequent polling. This endpoint
    is designed to be lightweight and fast, returning only essential status fields without
    the full job details. Use this for status polling instead of the full job endpoint.

    **Endpoint**: `GET /api/v1/jobs/{job_id}/status`

    **Use Cases**:
    - Frequent status polling
    - Lightweight status checks
    - Progress monitoring
    - Status dashboards
    - Quick status verification

    **Request Example**:
    ```
    GET /api/v1/jobs/job_xyz789/status
    ```

    **Response Example**:
    ```json
    {
      "job_id": "job_xyz789",
      "worker_id": "worker_abc123",
      "status": "running",
      "flow_id": "data_processing_flow"
    }
    ```

    **Response Fields**:
    - `job_id`: Job identifier
    - `worker_id`: Worker processing this job
    - `status`: Current job status (pending, running, completed, failed)
    - `flow_id`: Flow being executed

    **Performance**:
    - Optimized for frequent polling
    - Returns minimal data (faster than full job endpoint)
    - Lower bandwidth usage
    - Suitable for polling intervals of 1-5 seconds

    **Status Values**:
    - `pending`: Job is queued but not yet started
    - `running`: Job is currently executing
    - `completed`: Job finished successfully
    - `failed`: Job encountered an error

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist

    **Polling Recommendations**:
    - Use 1-5 second intervals for active monitoring
    - Use longer intervals (10-30 seconds) for background monitoring
    - Consider WebSocket endpoints for real-time updates
    - Stop polling when status is terminal (completed or failed)

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id} - Get complete job information (heavier)
    - POST /api/v1/jobs/{job_id}/wait - Wait for completion (blocking)
    - WS /api/ws/jobs/{job_id}/monitor - Real-time monitoring (WebSocket)

    Args:
        job_id: Unique job identifier

    Returns:
        dict: Minimal job status information

    Raises:
        HTTPException: 404 if job not found
    """
    runtime = get_runtime()
    job_storage = get_job_storage()

    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)

    if job_context is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    flow_id = job_storage.get_flow_id(job_id) or ""

    return {
        "job_id": job_id,
        "worker_id": job_context.worker_id,
        "status": job_context.status,
        "flow_id": flow_id,
    }


@router.post("/jobs/{job_id}/wait", dependencies=[RequireAuth])
async def wait_for_job(
    job_id: str,
    timeout: float = Query(
        60.0,
        ge=1.0,
        le=3600.0,
        description="Timeout in seconds. Range: 1.0-3600.0. Default: 60.0. Job must complete within this time or request will return with timeout status.",
    ),
):
    """
    Wait for a Job to complete (blocking endpoint).

    **Overview**:
    Blocks the request until the job reaches a terminal state (completed or failed) or
    the timeout is reached. This is useful for synchronous job execution patterns where
    you need to wait for the result before proceeding.

    **Endpoint**: `POST /api/v1/jobs/{job_id}/wait`

    **Use Cases**:
    - Synchronous job execution
    - Wait for job completion before processing results
    - Implement blocking API patterns
    - Simplify client code that needs job results

    **Query Parameters**:
    - `timeout` (optional): Maximum time to wait in seconds (1.0-3600.0, default: 60.0)

    **Request Examples**:
    ```
    # Wait with default timeout (60 seconds)
    POST /api/v1/jobs/job_xyz789/wait

    # Wait with custom timeout (30 seconds)
    POST /api/v1/jobs/job_xyz789/wait?timeout=30.0
    ```

    **Response Examples**:

    **Job completed**:
    ```json
    {
      "status": "completed",
      "job_id": "job_xyz789",
      "final_status": "completed",
      "waited_seconds": 45.2
    }
    ```

    **Job already complete**:
    ```json
    {
      "status": "already_complete",
      "job_id": "job_xyz789",
      "final_status": "completed",
      "waited_seconds": 0.0
    }
    ```

    **Timeout**:
    ```json
    {
      "status": "timeout",
      "job_id": "job_xyz789",
      "final_status": "running",
      "waited_seconds": 60.0,
      "message": "Job did not complete within 60 seconds"
    }
    ```

    **Response Status Values**:
    - `completed`: Job reached terminal state during wait
    - `already_complete`: Job was already in terminal state when wait started
    - `timeout`: Timeout reached before job completed

    **Behavior**:
    - Polls job status every 0.5 seconds
    - Returns immediately if job is already complete
    - Returns when job reaches terminal state (completed or failed)
    - Returns with timeout status if timeout is reached

    **Error Responses**:
    - `404 Not Found`: Job with this ID does not exist

    **Best Practices**:
    1. Use appropriate timeout based on expected job duration
    2. Check `final_status` to determine job outcome
    3. Handle timeout case appropriately (job may still be running)
    4. For long-running jobs, consider polling instead: GET /api/v1/jobs/{job_id}/status
    5. Use POST /api/v1/execute with wait=true for one-shot execution

    **Alternative Approaches**:
    - **Polling**: Use GET /api/v1/jobs/{job_id}/status in a loop
    - **WebSocket**: Use WebSocket endpoints for real-time updates
    - **One-shot**: Use POST /api/v1/execute with wait=true

    **Related Endpoints**:
    - GET /api/v1/jobs/{job_id}/status - Get job status (non-blocking)
    - POST /api/v1/execute - One-shot execution with built-in waiting
    - GET /api/v1/jobs/{job_id} - Get complete job details

    Args:
        job_id: Unique job identifier
        timeout: Maximum time to wait in seconds (1.0-3600.0)

    Returns:
        dict: Wait result with status and timing information

    Raises:
        HTTPException: 404 if job not found
    """
    runtime = get_runtime()
    job_storage = get_job_storage()

    job_context = job_storage.get_job(job_id) or runtime.get_job(job_id)

    if job_context is None:
        raise HTTPException(
            status_code=404,
            detail=create_error_response(ErrorCode.JOB_NOT_FOUND, f"Job '{job_id}' not found"),
        )

    # Check if already complete
    if job_context.status in ("completed", "failed"):
        return {
            "status": "already_complete",
            "job_id": job_id,
            "final_status": job_context.status,
            "waited_seconds": 0.0,
        }

    # Wait for completion
    start_time = time.time()
    poll_interval = 0.5

    while True:
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            current_job = job_storage.get_job(job_id) or runtime.get_job(job_id)
            return {
                "status": "timeout",
                "job_id": job_id,
                "final_status": current_job.status if current_job else "unknown",
                "waited_seconds": elapsed,
                "message": f"Job did not complete within {timeout} seconds",
            }

        # Check job status
        current_job = job_storage.get_job(job_id) or runtime.get_job(job_id)
        if current_job and current_job.status in ("completed", "failed"):
            return {
                "status": "completed",
                "job_id": job_id,
                "final_status": current_job.status,
                "waited_seconds": time.time() - start_time,
            }

        await asyncio.sleep(poll_interval)
