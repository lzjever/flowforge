"""
Job management API routes.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException

from routilux.api.models.job import JobListResponse, JobResponse, JobStartRequest
from routilux.job_state import JobState
from routilux.monitoring.registry import MonitoringRegistry
from routilux.monitoring.storage import flow_store, job_store

router = APIRouter()


def _job_to_response(job_state: JobState) -> JobResponse:
    """Convert JobState to response model."""
    return JobResponse(
        job_id=job_state.job_id,
        flow_id=job_state.flow_id,
        status=job_state.status.value
        if hasattr(job_state.status, "value")
        else str(job_state.status),
        created_at=datetime.now(),  # JobState doesn't track creation time
        started_at=None,  # Would need to track this
        completed_at=None,  # Would need to track this
        error=None,  # Would need to extract from execution history
    )


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def start_job(request: JobStartRequest):
    """Start a new job from a flow."""
    # Get flow
    flow = flow_store.get(request.flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow '{request.flow_id}' not found")

    # Enable monitoring if not already enabled
    MonitoringRegistry.enable()

    # Execute flow
    try:
        job_state = flow.execute(
            entry_routine_id=request.entry_routine_id,
            entry_params=request.entry_params,
            timeout=request.timeout,
        )

        # Store job
        job_store.add(job_state)

        return _job_to_response(job_state)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start job: {str(e)}")


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs():
    """List all jobs."""
    jobs = job_store.list_all()
    return JobListResponse(
        jobs=[_job_to_response(job) for job in jobs],
        total=len(jobs),
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get job details."""
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return _job_to_response(job_state)


@router.post("/jobs/{job_id}/pause", status_code=200)
async def pause_job(job_id: str):
    """Pause job execution."""
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
        raise HTTPException(status_code=400, detail=f"Failed to pause job: {str(e)}")


@router.post("/jobs/{job_id}/resume", status_code=200)
async def resume_job(job_id: str):
    """Resume job execution."""
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to resume job: {str(e)}")


@router.post("/jobs/{job_id}/cancel", status_code=200)
async def cancel_job(job_id: str):
    """Cancel job execution."""
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
        raise HTTPException(status_code=400, detail=f"Failed to cancel job: {str(e)}")


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get job status."""
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


@router.get("/jobs/{job_id}/state")
async def get_job_state(job_id: str):
    """Get full job state."""
    job_state = job_store.get(job_id)
    if not job_state:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # Serialize job state
    return job_state.serialize()
