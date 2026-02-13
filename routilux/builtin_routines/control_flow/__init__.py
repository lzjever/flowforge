"""
Control flow routines.

Routines for flow control, routing, and conditional execution.
"""

from routilux.builtin_routines.control_flow.aggregator import Aggregator
from routilux.builtin_routines.control_flow.batcher import Batcher
from routilux.builtin_routines.control_flow.conditional_router import ConditionalRouter
from routilux.builtin_routines.control_flow.debouncer import Debouncer
from routilux.builtin_routines.control_flow.splitter import Splitter

__all__ = [
    "ConditionalRouter",
    "Aggregator",
    "Batcher",
    "Debouncer",
    "Splitter",
]
