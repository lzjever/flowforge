"""Tests for core hooks interface."""

import pytest

from routilux.core.hooks import (
    ExecutionHooksInterface,
    NullExecutionHooks,
)


def test_null_hooks_on_slot_before_enqueue():
    """Test that NullExecutionHooks allows all enqueues."""
    hooks = NullExecutionHooks()

    # Should always return (True, None) - allow enqueue
    should_enqueue, reason = hooks.on_slot_before_enqueue(
        slot=None,  # Slot not needed for null implementation
        routine_id="test_routine",
        job_context=None,
        data={"key": "value"},
        flow_id="test_flow",
    )

    assert should_enqueue is True
    assert reason is None


def test_hook_interface_requires_implementation():
    """Test that ExecutionHooksInterface requires on_slot_before_enqueue."""

    # Create a partial implementation
    class PartialHooks(ExecutionHooksInterface):
        def on_worker_start(self, flow, worker_state):
            pass

        def on_worker_stop(self, flow, worker_state, status):
            pass

        def on_job_start(self, job_context, worker_state):
            pass

        def on_job_end(self, job_context, worker_state, status="completed", error=None):
            pass

        def on_routine_start(self, routine_id, worker_state, job_context=None):
            return True

        def on_routine_end(
            self, routine_id, worker_state, job_context=None, status="completed", error=None
        ):
            pass

        def on_event_emit(
            self, event, source_routine_id, worker_state, job_context=None, data=None
        ):
            return True

        # Missing on_slot_before_enqueue - should fail

    # Should raise TypeError when trying to instantiate
    with pytest.raises(TypeError):
        PartialHooks()
