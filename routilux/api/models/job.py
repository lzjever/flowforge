"""
Pydantic models for Job API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class JobStartRequest(BaseModel):
    """Request model for starting a job."""

    flow_id: str
    entry_routine_id: str
    entry_params: Optional[Dict[str, Any]] = None
    timeout: Optional[float] = None


class JobResponse(BaseModel):
    """Response model for job details."""

    job_id: str
    flow_id: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class JobListResponse(BaseModel):
    """Response model for job list with pagination support."""

    jobs: List[JobResponse]
    total: int
    limit: int = 100
    offset: int = 0
