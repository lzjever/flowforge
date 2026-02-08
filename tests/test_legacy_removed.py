"""
Test that legacy architecture has been removed.

This test file verifies that the legacy Flow/JobState architecture
has been properly removed and only the new core architecture remains.

Note: The new core classes (Flow, Routine, etc.) are re-exported from
routilux.core for convenience, so they should be importable from the root.
"""

import os
import pytest


def test_legacy_job_state_module_not_importable():
    """Legacy JobState module should not be importable."""
    with pytest.raises(ImportError):
        from routilux import job_state  # noqa: F401


def test_legacy_flow_module_not_importable():
    """Legacy flow module should not be importable."""
    with pytest.raises(ImportError):
        from routilux.flow import Flow  # This should fail - no flow submodule in root


def test_core_routine_is_available():
    """New core Routine should be available."""
    from routilux.core import Routine
    assert Routine is not None


def test_core_runtime_is_available():
    """New Runtime should be available."""
    from routilux.core import Runtime
    assert Runtime is not None


def test_core_flow_is_available():
    """New core Flow should be available."""
    from routilux.core import Flow
    assert Flow is not None


def test_core_event_is_available():
    """New core Event should be available."""
    from routilux.core import Event
    assert Event is not None


def test_core_connection_is_available():
    """New core Connection should be available."""
    from routilux.core import Connection
    assert Connection is not None


def test_core_slot_is_available():
    """New core Slot should be available."""
    from routilux.core import Slot
    assert Slot is not None


def test_core_error_handler_is_available():
    """New core ErrorHandler should be available."""
    from routilux.core import ErrorHandler
    assert ErrorHandler is not None


def test_worker_state_replaced_job_state():
    """WorkerState should be available (replaces JobState)."""
    from routilux.core import WorkerState
    assert WorkerState is not None


def test_execution_tracker_not_importable():
    """Legacy ExecutionTracker should not be importable."""
    with pytest.raises(ImportError):
        from routilux import ExecutionTracker  # noqa: F401


def test_legacy_files_do_not_exist():
    """Verify that legacy files have been deleted."""
    legacy_files = [
        "routilux/routine.py",
        "routilux/job_state.py",
        "routilux/connection.py",
        "routilux/error_handler.py",
        "routilux/execution_tracker.py",
        "routilux/routine_mixins.py",
        "routilux/event.py",
        "routilux/slot.py",
        "routilux/output_handler.py",
        "routilux/flow/",
    ]

    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for file_path in legacy_files:
        full_path = os.path.join(base_path, file_path)
        assert not os.path.exists(full_path), f"Legacy file {file_path} still exists"


def test_root_exports_core_classes():
    """Core classes should be importable from root for convenience."""
    from routilux import Flow, Routine, Runtime  # noqa: F401
    assert Flow is not None
    assert Routine is not None
    assert Runtime is not None
