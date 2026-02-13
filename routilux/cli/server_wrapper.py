"""Server wrapper for CLI mode.

Wraps the existing FastAPI server with CLI-specific configuration
including routine discovery and registration.
"""

import atexit
import os
from pathlib import Path
from typing import List, Optional

from routilux.cli.discovery import discover_routines, get_default_routines_dirs

# PID file management


def get_pid_file(port: int) -> Path:
    """Get PID file path for a server instance.

    Args:
        port: Server port number

    Returns:
        Path to PID file
    """
    return Path(f"/tmp/routilux-server-{port}.pid")


def write_pid_file(port: int, pid: int) -> None:
    """Write PID file when server starts.

    Args:
        port: Server port number
        pid: Process ID to write
    """
    pid_file = get_pid_file(port)
    pid_file.write_text(str(pid))
    atexit.register(lambda: remove_pid_file(port))


def read_pid_file(port: int) -> Optional[int]:
    """Read PID from file.

    Args:
        port: Server port number

    Returns:
        Process ID if file exists and is valid, None otherwise
    """
    pid_file = get_pid_file(port)
    if pid_file.exists():
        try:
            return int(pid_file.read_text().strip())
        except ValueError:
            return None
    return None


def remove_pid_file(port: int) -> None:
    """Remove PID file.

    Args:
        port: Server port number
    """
    pid_file = get_pid_file(port)
    if pid_file.exists():
        try:
            pid_file.unlink()
        except OSError:
            pass


def start_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    routines_dirs: Optional[List[Path]] = None,
    reload: bool = False,
    log_level: str = "info",
):
    """Start the routilux HTTP server.

    Discovers routines from specified directories and starts the FastAPI server.

    Args:
        host: Host to bind to
        port: Port to bind to
        routines_dirs: Additional directories to scan for routines
        reload: Enable auto-reload for development
        log_level: Log level for uvicorn
    """
    # Gather routines directories
    all_dirs = list(routines_dirs or [])
    all_dirs.extend(get_default_routines_dirs())

    # Discover routines before starting server
    if all_dirs:
        print(f"Discovering routines from: {all_dirs}")
        factory = discover_routines(all_dirs, on_error="warn")
        routines = factory.list_available()
        print(f"Registered {len(routines)} routines")

    # Set environment variables for server
    os.environ["ROUTILUX_API_HOST"] = host
    os.environ["ROUTILUX_API_PORT"] = str(port)
    os.environ["ROUTILUX_API_RELOAD"] = str(reload).lower()

    # Store routines directories for server endpoints
    if all_dirs:
        os.environ["ROUTILUX_ROUTINES_DIRS"] = ":".join(str(d) for d in all_dirs)

    # Write PID file
    write_pid_file(port, os.getpid())

    # Import and start server
    import uvicorn

    uvicorn.run(
        "routilux.server.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
