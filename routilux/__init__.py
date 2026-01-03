"""
Routilux - Event-driven workflow orchestration framework

Provides flexible connection, state management, and workflow orchestration capabilities.
"""

from routilux.routine import Routine, ExecutionContext
from routilux.slot import Slot
from routilux.event import Event
from routilux.connection import Connection
from routilux.flow import Flow
from routilux.job_state import JobState, ExecutionRecord
from routilux.execution_tracker import ExecutionTracker
from routilux.error_handler import ErrorHandler, ErrorStrategy
from routilux.output_handler import (
    OutputHandler,
    QueueOutputHandler,
    CallbackOutputHandler,
    NullOutputHandler,
)

# Import analysis tools
from routilux.analysis import (
    RoutineAnalyzer,
    WorkflowAnalyzer,
    analyze_routine_file,
    analyze_workflow,
    BaseFormatter,
    RoutineMarkdownFormatter,
    WorkflowD2Formatter,
)

# Import built-in routines
from routilux.builtin_routines import (
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
    "ExecutionContext",
    "Slot",
    "Event",
    "Connection",
    "Flow",
    "JobState",
    "ExecutionRecord",
    "ExecutionTracker",
    "ErrorHandler",
    "ErrorStrategy",
    # Output handlers
    "OutputHandler",
    "QueueOutputHandler",
    "CallbackOutputHandler",
    "NullOutputHandler",
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
    # Analysis tools
    "RoutineAnalyzer",
    "analyze_routine_file",
    "WorkflowAnalyzer",
    "analyze_workflow",
    "BaseFormatter",
    "RoutineMarkdownFormatter",
    "WorkflowD2Formatter",
]

__version__ = "0.10.0"
