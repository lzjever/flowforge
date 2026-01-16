"""
DSL loader for creating Flow objects from specifications.
"""

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from routilux.flow.flow import Flow


def load_flow_from_spec(spec: Dict[str, Any]) -> "Flow":
    """Create Flow from specification dictionary.

    Args:
        spec: Flow specification dictionary with structure:
            {
                "flow_id": "optional_flow_id",
                "routines": {
                    "routine_id": {
                        "class": "module.path.ClassName" or ClassObject,
                        "config": {...},
                        "error_handler": {...}
                    }
                },
                "connections": [
                    {"from": "r1.output", "to": "r2.input", "param_mapping": {...}}
                ],
                "execution": {
                    "strategy": "sequential",
                    "timeout": 300.0
                }
            }

    Returns:
        Constructed Flow object.
    """
    from routilux.dsl.spec_parser import parse_spec
    from routilux.error_handler import ErrorHandler, ErrorStrategy
    from routilux.flow.flow import Flow

    # Parse specification
    parsed = parse_spec(spec)

    # Create flow
    flow = Flow(flow_id=parsed.get("flow_id"))

    # Fix: Validate that routines key exists
    routines = parsed.get("routines")
    if not routines or not isinstance(routines, dict):
        raise ValueError(
            "Specification must contain a 'routines' dictionary with routine definitions"
        )

    # Add routines
    for routine_id, routine_info in routines.items():
        # Critical fix: Validate 'class' key exists to prevent KeyError
        if "class" not in routine_info:
            raise KeyError(
                f"Missing required 'class' key in routine specification for '{routine_id}'. "
                f"Each routine must specify a 'class' field with the routine class or import path."
            )
        routine_class = routine_info["class"]

        # Critical fix: Validate that routine_class is callable
        if not callable(routine_class):
            raise TypeError(
                f"Routine class for '{routine_id}' must be callable (a class or callable that returns Routine instances), got {type(routine_class).__name__}"
            )

        routine = routine_class()

        # Apply config
        config = routine_info.get("config")
        # Critical fix: Validate config is a dict
        if config is not None and not isinstance(config, dict):
            raise ValueError(
                f"Config for routine '{routine_id}' must be a dictionary, got {type(config).__name__}"
            )
        if config:
            routine.set_config(**config)

        # Apply error handler
        error_handler_spec = routine_info.get("error_handler")
        if error_handler_spec:
            handler_spec = error_handler_spec
            if isinstance(handler_spec, dict):
                strategy_str = handler_spec.get("strategy", "stop")
                strategy = (
                    ErrorStrategy[strategy_str.upper()]
                    if hasattr(ErrorStrategy, strategy_str.upper())
                    else ErrorStrategy.STOP
                )
                handler = ErrorHandler(
                    strategy=strategy,
                    max_retries=handler_spec.get("max_retries"),
                    retry_delay=handler_spec.get("retry_delay"),
                    retry_backoff=handler_spec.get("retry_backoff"),
                    is_critical=handler_spec.get("is_critical", False),
                )
                routine.set_error_handler(handler)
            elif isinstance(handler_spec, ErrorHandler):
                routine.set_error_handler(handler_spec)

        flow.add_routine(routine, routine_id)

    # Add connections
    # Critical fix: Validate connections key exists and is list
    connections = parsed.get("connections")
    if not isinstance(connections, list):
        raise ValueError("'connections' must be a list in flow specification")

    for conn in connections:
        # Critical fix: Validate connection has required keys
        if not isinstance(conn, dict):
            raise ValueError(f"Each connection must be a dictionary, got {type(conn)}")

        if "from" not in conn or "to" not in conn:
            raise ValueError("Connection must specify 'from' and 'to' keys")

        from_path = conn["from"].split(".")
        to_path = conn["to"].split(".")

        if len(from_path) != 2 or len(to_path) != 2:
            raise ValueError(
                f"Invalid connection format: {conn['from']} -> {conn['to']}. Expected 'routine_id.event_name' -> 'routine_id.slot_name'"
            )

        # LOW fix: Validate that path segments are non-empty
        if not all(from_path) or not all(to_path):
            raise ValueError(
                f"Connection path cannot contain empty segments: {conn['from']} -> {conn['to']}"
            )

        source_id = from_path[0]
        source_event = from_path[1]
        target_id = to_path[0]
        target_slot = to_path[1]

        flow.connect(source_id, source_event, target_id, target_slot, conn.get("param_mapping"))

    # Apply execution settings
    execution = parsed.get("execution", {})
    if "strategy" in execution:
        # Note: execution_strategy and max_workers are set in Flow.__init__()
        # We need to update them directly since set_execution_strategy() doesn't exist
        flow.execution_strategy = execution["strategy"]
        flow.max_workers = execution.get("max_workers", flow.max_workers)
        # Update worker count based on strategy
        if flow.execution_strategy == "sequential":
            flow.max_workers = 1
    if "timeout" in execution:
        flow.execution_timeout = execution["timeout"]

    return flow
