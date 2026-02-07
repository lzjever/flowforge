"""
Cloning utilities for Flow and Routine objects.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from routilux.core.flow import Flow
    from routilux.core.routine import Routine


def clone_routine(routine: "Routine") -> "Routine":
    """Clone a routine with config, policy, and logic.

    Creates a new instance of the same class and copies:
    - Configuration (_config)
    - Activation policy (_activation_policy)
    - Logic function (_logic)
    - Error handler (_error_handler)

    Note: Slots and events are class-level and will be recreated
    when the routine is instantiated, so they are not cloned.

    Args:
        routine: Routine instance to clone.

    Returns:
        New Routine instance with copied configuration.
    """
    # Create new instance
    new_routine = routine.__class__()

    # Copy config (deep copy)
    new_routine._config = routine._config.copy()

    # Copy policy and logic (references - they're callables)
    if routine._activation_policy:
        new_routine.set_activation_policy(routine._activation_policy)
    if routine._logic:
        new_routine.set_logic(routine._logic)
    if routine._error_handler:
        new_routine.set_error_handler(routine._error_handler)

    return new_routine


def clone_flow(flow: "Flow", flow_id: Optional[str] = None) -> "Flow":
    """Clone a flow with all routines and connections.

    Creates a new Flow instance and clones:
    - All routines (using clone_routine())
    - All connections (mapped to new routine instances)
    - Error handler

    Args:
        flow: Flow instance to clone.
        flow_id: Optional flow ID for the new flow. If None, generates a new one.

    Returns:
        New Flow instance with cloned routines and connections.
    """
    from routilux.core.flow import Flow

    # Create new flow
    new_flow = Flow(flow_id=flow_id)

    # Clone routines and create mapping
    routine_mapping = {}  # old_routine -> new_routine
    routine_id_mapping = {}  # old_routine_id -> new_routine_id

    for routine_id, routine in flow.routines.items():
        cloned_routine = clone_routine(routine)
        new_flow.add_routine(cloned_routine, routine_id)
        routine_mapping[routine] = cloned_routine
        routine_id_mapping[routine_id] = routine_id  # Same IDs

    # Clone connections
    for conn in flow.connections:
        if conn.source_event is None or conn.target_slot is None:
            continue  # Skip incomplete connections

        source_routine = conn.source_event.routine
        target_routine = conn.target_slot.routine

        if source_routine is None or target_routine is None:
            continue

        # Find routine IDs
        source_id = flow._get_routine_id(source_routine)
        target_id = flow._get_routine_id(target_routine)

        if source_id is None or target_id is None:
            continue

        # Connect using new routine IDs (same IDs, but new routine instances)
        new_flow.connect(
            source_id,
            conn.source_event.name,
            target_id,
            conn.target_slot.name,
        )

    # Clone error handler
    if flow.error_handler:
        new_flow.set_error_handler(flow.error_handler)

    # Clone execution timeout
    new_flow.execution_timeout = flow.execution_timeout

    return new_flow
