"""
Monitoring and debugging infrastructure for Routilux.

This module provides optional monitoring, debugging, and breakpoint functionality.
All features are disabled by default and have zero overhead when not enabled.
"""

import os

# Auto-enable if environment variable is set
_AUTO_ENABLE = os.getenv("ROUTILUX_ENABLE_MONITORING", "false").lower() == "true"

from routilux.monitoring.registry import MonitoringRegistry  # noqa: E402

# Auto-enable if environment variable is set
if _AUTO_ENABLE:
    MonitoringRegistry.enable()

from routilux.monitoring.breakpoint_manager import Breakpoint, BreakpointManager  # noqa: E402
from routilux.monitoring.debug_session import (  # noqa: E402
    CallFrame,
    DebugSession,
    DebugSessionStore,
)
from routilux.monitoring.event_manager import JobEventManager, get_event_manager  # noqa: E402
from routilux.monitoring.monitor_collector import (  # noqa: E402
    ErrorRecord,
    ExecutionEvent,
    ExecutionMetrics,
    MonitorCollector,
    RoutineMetrics,
)

__all__ = [
    "MonitoringRegistry",
    "BreakpointManager",
    "Breakpoint",
    "DebugSession",
    "DebugSessionStore",
    "CallFrame",
    "MonitorCollector",
    "ExecutionMetrics",
    "RoutineMetrics",
    "ExecutionEvent",
    "ErrorRecord",
    "JobEventManager",
    "get_event_manager",
]
