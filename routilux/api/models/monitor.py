"""
Pydantic models for Monitoring API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class RoutineMetricsResponse(BaseModel):
    """Response model for routine metrics."""

    routine_id: str
    execution_count: int
    total_duration: float
    avg_duration: float
    min_duration: Optional[float]
    max_duration: Optional[float]
    error_count: int
    last_execution: Optional[datetime]


class ExecutionMetricsResponse(BaseModel):
    """Response model for execution metrics."""

    job_id: str
    flow_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[float]
    routine_metrics: Dict[str, RoutineMetricsResponse]
    total_events: int
    total_slot_calls: int
    total_event_emits: int
    errors: List[Dict[str, Any]]


class ExecutionEventResponse(BaseModel):
    """Response model for execution event."""

    event_id: str
    job_id: str
    routine_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]
    duration: Optional[float]
    status: Optional[str]


class ExecutionTraceResponse(BaseModel):
    """Response model for execution trace."""

    events: List[ExecutionEventResponse]
    total: int
