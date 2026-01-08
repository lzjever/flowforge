"""
FastAPI backend for Routilux monitoring and flow builder.

This module provides REST API and WebSocket endpoints for:
- Flow management (CRUD, DSL import/export)
- Job management (start, pause, resume, cancel)
- Breakpoint management
- Debug operations
- Real-time monitoring

This is an optional module. Install with: pip install routilux[api]
"""

__all__ = ["app"]

try:
    from routilux.api.main import app
except ImportError as e:
    raise ImportError(
        "FastAPI dependencies are not installed. "
        "Install them with: pip install routilux[api]"
    ) from e

