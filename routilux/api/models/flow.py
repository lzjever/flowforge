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


class AddRoutineRequest(BaseModel):
    """Request model for adding a routine to a flow."""

    routine_id: str
    object_name: str
    config: Optional[Dict[str, Any]] = None


class AddConnectionRequest(BaseModel):
    """Request model for adding a connection to a flow."""

    source_routine: str
    source_event: str
    target_routine: str
    target_slot: str


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


class FlowResponse(BaseModel):
    """Response model for flow details."""

    flow_id: str
    routines: Dict[str, RoutineInfo]
    connections: List[ConnectionInfo]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FlowListResponse(BaseModel):
    """Response model for flow list."""

    flows: List[FlowResponse]
    total: int
