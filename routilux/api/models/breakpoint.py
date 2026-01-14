"""
Pydantic models for Breakpoint API.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel


class BreakpointCreateRequest(BaseModel):
    """Request model for creating a breakpoint."""

    type: Literal["routine", "slot", "event"]
    routine_id: Optional[str] = None
    slot_name: Optional[str] = None
    event_name: Optional[str] = None
    condition: Optional[str] = None
    enabled: bool = True


class BreakpointResponse(BaseModel):
    """Response model for breakpoint details."""

    breakpoint_id: str
    job_id: str
    type: str
    routine_id: Optional[str]
    slot_name: Optional[str]
    event_name: Optional[str]
    condition: Optional[str]
    enabled: bool
    hit_count: int


class BreakpointListResponse(BaseModel):
    """Response model for breakpoint list."""

    breakpoints: List[BreakpointResponse]
    total: int
