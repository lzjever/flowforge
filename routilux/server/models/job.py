"""
Pydantic models for Job API.

All models include detailed field descriptions and examples for frontend developers.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class JobStartRequest(BaseModel):
    """Request model for starting a new job execution.

    This endpoint creates a new job and starts executing the specified flow asynchronously.
    The job will be in RUNNING status immediately after creation, and all routines start in IDLE state,
    waiting for external data via the post endpoint.

    **Example Request**:
    ```json
    {
      "flow_id": "data_processing_flow",
      "runtime_id": "production",
      "timeout": 3600.0
    }
    ```

    **Note**: If `runtime_id` is not provided, the default runtime will be used.
    """

    flow_id: str = Field(
        ...,
        description="The unique identifier of the flow to execute. Must be a registered flow ID.",
        example="data_processing_flow",
    )
    runtime_id: Optional[str] = Field(
        None,
        description="Optional runtime ID to use for execution. If not provided, uses the default runtime. "
        "Use this to select different execution environments (e.g., 'development', 'production').",
        example="production",
    )
    timeout: Optional[float] = Field(
        None,
        description="Execution timeout in seconds. If not provided, uses the flow's default timeout. "
        "Maximum allowed: 86400 seconds (24 hours). "
        "When timeout is reached, the job will be automatically cancelled.",
        example=3600.0,
        ge=0.0,
        le=86400.0,
    )

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v < 0:
                raise ValueError("timeout must be non-negative")
            if v > 86400:
                raise ValueError("timeout must be <= 86400 seconds (24 hours)")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "flow_id": "data_processing_flow",
                    "timeout": 3600.0,
                },
                {
                    "flow_id": "quick_test_flow",
                    "runtime_id": "development",
                    "timeout": 60.0,
                },
            ]
        }
    }


class PostToJobRequest(BaseModel):
    """Request model for posting data to a routine slot in a running or paused job.

    This endpoint allows you to send data to a specific routine's input slot while the job is running.
    This is the primary way to trigger routine execution in the new architecture where all routines
    start in IDLE state.

    **When to Use**:
    - Job is in RUNNING or PAUSED status
    - You want to send data to a routine's input slot
    - You want to trigger routine execution

    **Example Request**:
    ```json
    {
      "routine_id": "data_source",
      "slot_name": "trigger",
      "data": {
        "input": "test_data",
        "index": 1
      }
    }
    ```

    **Error Cases**:
    - 404: Job, flow, routine, or slot not found
    - 409: Job is not in RUNNING or PAUSED status
    - 400: Invalid data format
    """

    routine_id: str = Field(
        ...,
        description="The ID of the routine to send data to. Must be a routine that exists in the flow.",
        example="data_source",
    )
    slot_name: str = Field(
        ...,
        description="The name of the input slot to send data to. Must be a slot defined in the routine.",
        example="trigger",
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="The data to send to the slot. Can be any JSON-serializable object. "
        "If not provided, an empty dictionary will be sent. "
        "The data will be queued in the slot and processed according to the routine's activation policy.",
        example={"input": "test_data", "index": 1, "metadata": {"source": "api"}},
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "routine_id": "data_source",
                    "slot_name": "trigger",
                    "data": {"input": "test_data", "index": 1},
                },
                {
                    "routine_id": "processor",
                    "slot_name": "input",
                    "data": {"items": [1, 2, 3], "batch_id": "batch-123"},
                },
            ]
        }
    }


class JobResponse(BaseModel):
    """Response model for job details.

    Contains all essential information about a job's current state.

    **Status Values**:
    - `pending`: Job created but not yet started
    - `running`: Job is currently executing
    - `idle`: All routines are idle, waiting for data
    - `completed`: Job finished successfully
    - `failed`: Job failed due to an error
    - `paused`: Job execution is paused
    - `cancelled`: Job was cancelled

    **Timestamps**: All timestamps are Unix timestamps (seconds since epoch).

    **Example Response**:
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
    """

    job_id: str = Field(
        ...,
        description="Unique identifier for this job. UUID format. Use this ID for all subsequent API calls.",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    flow_id: str = Field(
        ...,
        description="The flow ID that this job is executing.",
        example="data_processing_flow",
    )
    status: str = Field(
        ...,
        description="Current execution status of the job. Possible values: "
        "pending, running, idle, completed, failed, paused, cancelled.",
        example="running",
    )
    created_at: Optional[int] = Field(
        None,
        description="Unix timestamp (seconds) when the job was created.",
        example=1705312800,
    )
    started_at: Optional[int] = Field(
        None,
        description="Unix timestamp (seconds) when the job execution started. "
        "Null if job hasn't started yet.",
        example=1705312801,
    )
    completed_at: Optional[int] = Field(
        None,
        description="Unix timestamp (seconds) when the job completed (successfully or with error). "
        "Null if job is still running or hasn't started.",
        example=1705316400,
    )
    error: Optional[str] = Field(
        None,
        description="Error message if the job failed. Null if job is successful or still running.",
        example="Routine 'processor' failed: ValueError: Invalid input data",
    )


class JobListResponse(BaseModel):
    """Response model for job list with pagination support.

    Returns a paginated list of jobs with total count for building pagination UI.

    **Example Response**:
    ```json
    {
      "jobs": [
        {
          "job_id": "job-1",
          "flow_id": "flow-1",
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

    **Pagination**: Use `limit` and `offset` to implement pagination:
    - Page 1: `limit=100, offset=0`
    - Page 2: `limit=100, offset=100`
    - Page 3: `limit=100, offset=200`
    """

    jobs: List[JobResponse] = Field(
        ...,
        description="List of job objects matching the query criteria. "
        "Limited by the `limit` parameter and offset by the `offset` parameter.",
    )
    total: int = Field(
        ...,
        description="Total number of jobs matching the filter criteria (before pagination). "
        "Use this to calculate total pages: `Math.ceil(total / limit)`.",
        example=150,
    )
    limit: int = Field(
        100,
        description="Maximum number of jobs returned in this response. "
        "Range: 1-1000. Default: 100.",
        example=100,
        ge=1,
        le=1000,
    )
    offset: int = Field(
        0,
        description="Number of jobs skipped before returning results. "
        "Use this for pagination: `offset = (page - 1) * limit`.",
        example=0,
        ge=0,
    )
