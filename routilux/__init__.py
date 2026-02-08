"""
Routilux - Event-driven workflow orchestration framework

Provides flexible workflow orchestration capabilities using the new core architecture.
For the core workflow engine, import from routilux.core:

    from routilux.core import Flow, Routine, Runtime
"""

# Import from new core architecture - only what's exported
from routilux.core import (
    Connection,
    Event,
    EventRoutingTask,
    ExecutionHooksInterface,
    ExecutionRecord,
    ExecutionStatus,
    Flow,
    FlowRegistry,
    JobContext,
    JobStatus,
    NullExecutionHooks,
    Routine,
    RoutineConfig,
    RoutineStatus,
    RoutedStdout,
    Slot,
    SlotActivationTask,
    SlotDataPoint,
    SlotQueueFullError,
    TaskPriority,
    WorkerExecutor,
    WorkerManager,
    WorkerNotRunningError,
    WorkerRegistry,
    WorkerState,
    # Functions
    clear_job_output,
    get_current_job,
    get_current_job_id,
    get_current_worker_state,
    get_execution_hooks,
    get_flow_registry,
    get_job_output,
    get_routed_stdout,
    get_worker_manager,
    get_worker_registry,
    install_routed_stdout,
    reset_execution_hooks,
    reset_worker_manager,
    set_current_job,
    set_current_worker_state,
    set_execution_hooks,
    uninstall_routed_stdout,
    Runtime,
    # Error handling
    ErrorHandler,
    ErrorStrategy,
)

# Import ExecutionContext directly since it's defined but not exported
from routilux.core.context import ExecutionContext

# Import analysis tools
from routilux.analysis import (
    BaseFormatter,
    RoutineAnalyzer,
    RoutineMarkdownFormatter,
    WorkflowAnalyzer,
    WorkflowD2Formatter,
    analyze_routine_file,
    analyze_workflow,
)

# Import built-in routines
from routilux.builtin_routines import (
    ConditionalRouter,
    DataFlattener,
    DataTransformer,
    DataValidator,
    ResultExtractor,
    TextClipper,
    TextRenderer,
    TimeProvider,
)

# Import exceptions (these are still useful utilities)
from routilux.exceptions import (
    ConfigurationError,
    RoutiluxError,
    SerializationError,
    SlotHandlerError,
    StateError,
)

# Import validators (still useful)
from routilux.validators import ValidationError, Validator

# Import metrics (still useful)
from routilux.metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsCollector,
    MetricTimer,
)

__all__ = [
    # Core classes (from new core architecture)
    "Routine",
    "ExecutionContext",
    "JobContext",
    "Slot",
    "Event",
    "Connection",
    "Flow",
    "RoutineConfig",
    "Runtime",
    "WorkerState",
    "ExecutionRecord",
    "WorkerExecutor",
    "WorkerManager",
    "FlowRegistry",
    "WorkerRegistry",
    # Status enums
    "ExecutionStatus",
    "RoutineStatus",
    "JobStatus",
    # Task classes
    "TaskPriority",
    "SlotActivationTask",
    "EventRoutingTask",
    # Slot utilities
    "SlotDataPoint",
    "SlotQueueFullError",
    # Error handling
    "ErrorHandler",
    "ErrorStrategy",
    # Hooks
    "ExecutionHooksInterface",
    "NullExecutionHooks",
    # Output handling
    "RoutedStdout",
    # Worker management
    "WorkerNotRunningError",
    # Convenience functions
    "get_current_job",
    "get_current_job_id",
    "get_current_worker_state",
    "set_current_job",
    "set_current_worker_state",
    "get_execution_hooks",
    "set_execution_hooks",
    "reset_execution_hooks",
    "get_flow_registry",
    "get_worker_registry",
    "get_worker_manager",
    "reset_worker_manager",
    "install_routed_stdout",
    "uninstall_routed_stdout",
    "get_routed_stdout",
    "get_job_output",
    "clear_job_output",
    # Exceptions (utility module)
    "RoutiluxError",
    "SerializationError",
    "ConfigurationError",
    "StateError",
    "SlotHandlerError",
    "ValidationError",
    "Validator",
    # Metrics (utility module)
    "MetricsCollector",
    "Counter",
    "Gauge",
    "Histogram",
    "MetricTimer",
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

__version__ = "0.11.0"
