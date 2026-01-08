"""
Monitoring and debugging infrastructure for Routilux.

This module provides optional monitoring, debugging, and breakpoint functionality.
All features are disabled by default and have zero overhead when not enabled.
"""

import os
from typing import Optional

# Auto-enable if environment variable is set
_AUTO_ENABLE = os.getenv("ROUTILUX_ENABLE_MONITORING", "false").lower() == "true"

from routilux.monitoring.registry import MonitoringRegistry

# Auto-enable if environment variable is set
if _AUTO_ENABLE:
    MonitoringRegistry.enable()

from routilux.monitoring.registry import MonitoringRegistry
from routilux.monitoring.breakpoint_manager import BreakpointManager, Breakpoint
from routilux.monitoring.debug_session import DebugSession, DebugSessionStore, CallFrame
from routilux.monitoring.monitor_collector import (
    MonitorCollector,
    ExecutionMetrics,
    RoutineMetrics,
    ExecutionEvent,
    ErrorRecord,
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
]

