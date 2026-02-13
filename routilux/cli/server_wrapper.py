"""Server wrapper for CLI mode.

Wraps the existing FastAPI server with CLI-specific configuration
including routine discovery and registration.
"""

import atexit
import json
import os
import signal
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from routilux.cli.discovery import discover_routines, get_default_routines_dirs
from routilux.core.flow import Flow

# PID file management

# Track registered ports for signal handler cleanup
_registered_ports: set[int] = set()
_cleanup_registered = False


def _signal_handler(signum, frame):
    """Signal handler to clean up PID files on termination."""
    for port in list(_registered_ports):
        remove_pid_file(port)
    # Re-raise signal with default handler
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)


def _register_signal_handlers():
    """Register signal handlers for PID file cleanup."""
    global _cleanup_registered
    if _cleanup_registered:
        return
    _cleanup_registered = True

    # Handle SIGTERM and SIGINT for cleanup
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)


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
    _registered_ports.add(port)

    # Register signal handlers for cleanup
    _register_signal_handlers()

    # Also use atexit as fallback
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
    _registered_ports.discard(port)


def load_flows_from_directory(flows_dir: Path, factory) -> Dict[str, Flow]:
    """Load all flows from a directory.

    Args:
        flows_dir: Directory containing flow DSL files (.yaml, .json)
        factory: ObjectFactory for loading flows

    Returns:
        Dictionary mapping flow_id to Flow instance

    Raises:
        ValueError: If duplicate flow_id is detected
    """
    flows: Dict[str, Flow] = {}
    flows_path = Path(flows_dir)

    if not flows_path.exists():
        return flows

    # Load YAML files
    for dsl_file in flows_path.glob("*.yaml"):
        try:
            dsl_content = dsl_file.read_text()
            dsl_dict = yaml.safe_load(dsl_content)

            flow = factory.load_flow_from_dsl(dsl_dict)

            if flow.flow_id in flows:
                raise ValueError(
                    f"Duplicate flow_id '{flow.flow_id}' in {dsl_file} "
                    f"(already defined in another file)"
                )

            flows[flow.flow_id] = flow
            print(f"Loaded flow: {flow.flow_id} from {dsl_file.name}")

        except ValueError:
            raise  # Re-raise duplicate flow_id errors
        except yaml.YAMLError as e:
            print(f"Warning: Failed to parse {dsl_file}: {e}")
        except Exception as e:
            print(f"Warning: Failed to load flow from {dsl_file}: {e}")

    # Load JSON files
    for dsl_file in flows_path.glob("*.json"):
        try:
            dsl_content = dsl_file.read_text()
            dsl_dict = json.loads(dsl_content)

            flow = factory.load_flow_from_dsl(dsl_dict)

            if flow.flow_id in flows:
                raise ValueError(
                    f"Duplicate flow_id '{flow.flow_id}' in {dsl_file} "
                    f"(already defined in another file)"
                )

            flows[flow.flow_id] = flow
            print(f"Loaded flow: {flow.flow_id} from {dsl_file.name}")

        except ValueError:
            raise  # Re-raise duplicate flow_id errors
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse {dsl_file}: {e}")
        except Exception as e:
            print(f"Warning: Failed to load flow from {dsl_file}: {e}")

    return flows


def start_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    routines_dirs: Optional[List[Path]] = None,
    flows_dir: Optional[Path] = None,
    reload: bool = False,
    log_level: str = "info",
):
    """Start the routilux HTTP server.

    Discovers routines from specified directories and starts the FastAPI server.

    Args:
        host: Host to bind to
        port: Port to bind to
        routines_dirs: Additional directories to scan for routines
        flows_dir: Directory containing flow DSL files to load at startup
        reload: Enable auto-reload for development
        log_level: Log level for uvicorn
    """
    # Register built-in routines first
    from routilux.builtin_routines import register_all_builtins

    factory = discover_routines([], on_error="warn")  # Get factory
    register_all_builtins(factory)
    print("Registered built-in routines")

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

    # Load flows from directory
    if flows_dir:
        print(f"Loading flows from: {flows_dir}")
        flows = load_flows_from_directory(flows_dir, factory)
        print(f"Loaded {len(flows)} flows")

        # Register flows with monitoring storage
        from routilux.monitoring.storage import flow_store

        for flow_id, flow in flows.items():
            flow_store.add(flow)

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
