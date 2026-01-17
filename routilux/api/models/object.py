"""
Pydantic models for Object API.
"""

from typing import Any, Dict, List

from pydantic import BaseModel


class ObjectMetadataResponse(BaseModel):
    """Response model for object metadata."""

    name: str
    description: str
    category: str
    tags: List[str]
    example_config: Dict[str, Any]
    version: str


class ObjectInfo(BaseModel):
    """Information about an available object."""

    name: str
    type: str  # "class" or "instance"
    description: str
    category: str
    tags: List[str]
    example_config: Dict[str, Any]
    version: str


class ObjectListResponse(BaseModel):
    """Response model for object list."""

    objects: List[ObjectInfo]
    total: int
