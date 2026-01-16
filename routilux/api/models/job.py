"""
Pydantic models for Job API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator


class JobStartRequest(BaseModel):
    """Request model for starting a job."""

    flow_id: str
    entry_routine_id: str
    entry_params: Optional[Dict[str, Any]] = None
    timeout: Optional[float] = None

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v < 0:
                raise ValueError("timeout must be non-negative")
            if v > 86400:
                raise ValueError("timeout must be <= 86400 seconds (24 hours)")
        return v


class JobResponse(BaseModel):
    """Response model for job details."""

    job_id: str
    flow_id: str
    status: str
    created_at: Optional[int] = None
    started_at: Optional[int] = None
    completed_at: Optional[int] = None
    error: Optional[str] = None


class JobListResponse(BaseModel):
    """Response model for job list with pagination support."""

    jobs: List[JobResponse]
    total: int
    limit: int = 100
    offset: int = 0
