"""
Pydantic models for Debug API.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class ExpressionEvalRequest(BaseModel):
    """Request model for expression evaluation."""

    expression: str = Field(..., description="Expression to evaluate")
    routine_id: Optional[str] = Field(None, description="Routine ID for context")
    frame_index: int = Field(0, description="Stack frame index (default 0 = current frame)")


class ExpressionEvalResponse(BaseModel):
    """Response model for expression evaluation."""

    result: Optional[Any] = Field(None, description="Evaluation result")
    type: Optional[str] = Field(None, description="Result type")
    error: Optional[str] = Field(None, description="Error message if evaluation failed")
