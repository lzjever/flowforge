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

__all__ = ["app", "config"]

# Export config module - this doesn't require FastAPI
from routilux.server import config

# Import app only if FastAPI is available
try:
    from routilux.server.main import app

    _app_available = True
except ImportError:
    _app_available = False
    app = None


def _ensure_fastapi():
    """Ensure FastAPI dependencies are available."""
    if not _app_available:
        raise ImportError(
            "FastAPI dependencies are not installed. Install them with: pip install routilux[api]"
        )
