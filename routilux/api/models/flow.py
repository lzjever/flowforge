"""
Pydantic models for Flow API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FlowCreateRequest(BaseModel):
    """Request model for creating a flow."""

    flow_id: Optional[str] = None
    dsl: Optional[str] = None  # YAML string
    dsl_dict: Optional[Dict[str, Any]] = None  # JSON dict
    execution_strategy: Optional[str] = "sequential"
    max_workers: Optional[int] = 5


class RoutineInfo(BaseModel):
    """Information about a routine."""

    routine_id: str
    class_name: str
    slots: List[str]
    events: List[str]
    config: Dict[str, Any]


class ConnectionInfo(BaseModel):
    """Information about a connection."""

    connection_id: str
    source_routine: str
    source_event: str
    target_routine: str
    target_slot: str
    param_mapping: Optional[Dict[str, str]] = None


class FlowResponse(BaseModel):
    """Response model for flow details."""

    flow_id: str
    routines: Dict[str, RoutineInfo]
    connections: List[ConnectionInfo]
    execution_strategy: str
    max_workers: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FlowListResponse(BaseModel):
    """Response model for flow list."""

    flows: List[FlowResponse]
    total: int
