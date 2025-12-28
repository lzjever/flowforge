"""
FlowForge - Event-driven workflow orchestration framework

Provides flexible connection, state management, and workflow orchestration capabilities.
"""

from flowforge.routine import Routine
from flowforge.slot import Slot
from flowforge.event import Event
from flowforge.connection import Connection
from flowforge.flow import Flow
from flowforge.job_state import JobState, ExecutionRecord
from flowforge.execution_tracker import ExecutionTracker
from flowforge.error_handler import ErrorHandler, ErrorStrategy

# Import built-in routines
from flowforge.builtin_routines import (
    # Text processing
    TextClipper,
    TextRenderer,
    ResultExtractor,
    # Utils
    TimeProvider,
    DataFlattener,
    # Data processing
    DataTransformer,
    DataValidator,
    # Control flow
    ConditionalRouter,
)

__all__ = [
    # Core classes
    "Routine",
    "Slot",
    "Event",
    "Connection",
    "Flow",
    "JobState",
    "ExecutionRecord",
    "ExecutionTracker",
    "ErrorHandler",
    "ErrorStrategy",
    # Built-in routines - Text processing
    "TextClipper",
    "TextRenderer",
    "ResultExtractor",
    # Built-in routines - Utils
    "TimeProvider",
    "DataFlattener",
    # Built-in routines - Data processing
    "DataTransformer",
    "DataValidator",
    # Built-in routines - Control flow
    "ConditionalRouter",
]

__version__ = "0.8.0"

