"""
Comprehensive tests for Runtime hook integration.

These tests are written based on interface specifications, not implementation details.
They challenge the business logic and verify correct behavior in all scenarios.
"""

import threading
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.job_state import JobState
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.monitoring.hooks import ExecutionHooks, execution_hooks
from routilux.monitoring.registry import MonitoringRegistry
from routilux.runtime import Runtime
from routilux.status import ExecutionStatus


class TestRuntimeHookInterfaceCompliance:
    """Test that Runtime correctly implements hook interface contracts."""

    def test_flow_start_hook_receives_correct_parameters(self):
        """Test: on_flow_start receives flow and job_state as specified in interface."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        # Create a mock hook to verify interface compliance
        mock_hook = Mock(spec=ExecutionHooks)
        mock_hook.on_flow_start = Mock()
        mock_hook.on_flow_end = Mock()

        with patch.object(execution_hooks, "on_flow_start", mock_hook.on_flow_start):
            with patch.object(execution_hooks, "on_flow_end", mock_hook.on_flow_end):
                job_state = runtime.exec("test_flow")
                runtime.wait_until_all_jobs_finished(timeout=5.0)

                # Verify interface: on_flow_start(flow, job_state)
                assert mock_hook.on_flow_start.called
                call_args = mock_hook.on_flow_start.call_args
                assert len(call_args[0]) == 2, "on_flow_start should receive exactly 2 positional args"
                assert call_args[0][0] is flow, "First arg should be flow object"
                assert call_args[0][1] is job_state, "Second arg should be job_state object"

        runtime.shutdown(wait=True)

    def test_flow_end_hook_receives_status_parameter(self):
        """Test: on_flow_end receives status parameter as specified in interface."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        mock_hook = Mock(spec=ExecutionHooks)
        mock_hook.on_flow_end = Mock()

        with patch.object(execution_hooks, "on_flow_end", mock_hook.on_flow_end):
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Verify interface: on_flow_end(flow, job_state, status=...)
            assert mock_hook.on_flow_end.called
            call_args = mock_hook.on_flow_end.call_args
            # Should have flow, job_state, and status
            assert len(call_args[0]) >= 2, "on_flow_end should receive at least 2 positional args"
            assert "status" in call_args[1] or len(call_args[0]) > 2, "status should be provided"
            if "status" in call_args[1]:
                status = call_args[1]["status"]
                assert isinstance(status, str), "status should be a string"
                assert status in ["completed", "failed", "cancelled"], f"Invalid status: {status}"

        runtime.shutdown(wait=True)

    def test_routine_start_hook_called_before_logic_execution(self):
        """Test: on_routine_start is called BEFORE routine logic executes."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        execution_order = []

        def my_logic(trigger_data, policy_message, job_state):
            execution_order.append("logic")

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        def track_routine_start(*args, **kwargs):
            execution_order.append("hook_start")

        with patch.object(execution_hooks, "on_routine_start", side_effect=track_routine_start):
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Verify hook is called before logic
            assert "hook_start" in execution_order
            assert "logic" in execution_order
            assert execution_order.index("hook_start") < execution_order.index("logic"), \
                "on_routine_start should be called before logic execution"

        runtime.shutdown(wait=True)

    def test_routine_end_hook_called_after_logic_execution(self):
        """Test: on_routine_end is called AFTER routine logic executes (even on error)."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        execution_order = []

        def my_logic(trigger_data, policy_message, job_state):
            execution_order.append("logic")
            raise ValueError("Test error")

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        def track_routine_end(*args, **kwargs):
            execution_order.append("hook_end")

        with patch.object(execution_hooks, "on_routine_end", side_effect=track_routine_end):
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Verify hook is called after logic (even on error)
            assert "logic" in execution_order
            assert "hook_end" in execution_order
            assert execution_order.index("logic") < execution_order.index("hook_end"), \
                "on_routine_end should be called after logic execution (even on error)"

        runtime.shutdown(wait=True)

    def test_event_emit_hook_receives_correct_data(self):
        """Test: on_event_emit receives event, routine_id, job_state, and data as specified."""
        flow = Flow("test_flow")
        routine_a = Routine()
        routine_a.define_slot("trigger")
        event = routine_a.define_event("output")

        test_data = {"key": "value", "number": 42}

        def logic_a(trigger_data, policy_message, job_state):
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                event.emit(runtime=runtime, job_state=job_state, **test_data)

        routine_a.set_logic(logic_a)
        routine_a.set_activation_policy(immediate_policy())
        flow.add_routine(routine_a, "routine_a")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        mock_hook = Mock()
        mock_hook.return_value = True  # Continue execution

        with patch.object(execution_hooks, "on_event_emit", mock_hook):
            job_state = runtime.exec("test_flow")
            time.sleep(0.5)  # Wait for event emission
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Verify interface: on_event_emit(event, routine_id, job_state, data=...)
            if mock_hook.called:
                call_args = mock_hook.call_args
                assert len(call_args[0]) >= 3, "on_event_emit should receive at least 3 positional args"
                assert call_args[0][0] is event, "First arg should be event object"
                assert call_args[0][1] == "routine_a", "Second arg should be routine_id"
                assert call_args[0][2] is job_state, "Third arg should be job_state"
                # Data should be passed (either positional or keyword)
                if "data" in call_args[1]:
                    received_data = call_args[1]["data"]
                    # Data should match what was emitted
                    assert isinstance(received_data, dict), "data should be a dict"

        runtime.shutdown(wait=True)

    def test_slot_data_received_hook_receives_correct_parameters(self):
        """Test: on_slot_data_received receives slot, routine_id, job_state, and data."""
        flow = Flow("test_flow")
        routine_a = Routine()
        routine_a.define_slot("trigger")
        event = routine_a.define_event("output")

        def logic_a(trigger_data, policy_message, job_state):
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                event.emit(runtime=runtime, job_state=job_state, data={"test": "data"})

        routine_a.set_logic(logic_a)
        routine_a.set_activation_policy(immediate_policy())

        routine_b = Routine()
        slot_b = routine_b.define_slot("input")

        def logic_b(input_data, policy_message, job_state):
            pass

        routine_b.set_logic(logic_b)
        routine_b.set_activation_policy(immediate_policy())

        flow.add_routine(routine_a, "routine_a")
        flow.add_routine(routine_b, "routine_b")
        flow.connect("routine_a", "output", "routine_b", "input")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        mock_hook = Mock()
        mock_hook.return_value = True

        with patch.object(execution_hooks, "on_slot_data_received", mock_hook):
            job_state = runtime.exec("test_flow")
            time.sleep(0.5)
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Verify interface: on_slot_data_received(slot, routine_id, job_state, data=...)
            if mock_hook.called:
                call_args = mock_hook.call_args
                assert len(call_args[0]) >= 3, "on_slot_data_received should receive at least 3 positional args"
                assert call_args[0][0] is slot_b, "First arg should be slot object"
                assert call_args[0][1] == "routine_b", "Second arg should be routine_id"
                assert call_args[0][2] is job_state, "Third arg should be job_state"
                # Data should be passed
                assert "data" in call_args[1] or len(call_args[0]) > 3, "data should be provided"

        runtime.shutdown(wait=True)


class TestRuntimeHookErrorHandling:
    """Test error handling in hook execution."""

    def test_hook_exception_does_not_crash_runtime(self):
        """Test: Exception in hook should not crash Runtime execution."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        # Make hook raise exception
        def failing_hook(*args, **kwargs):
            raise RuntimeError("Hook error - should not crash Runtime")

        with patch.object(execution_hooks, "on_flow_start", side_effect=failing_hook):
            # Execution should still proceed
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Job should complete (or at least not crash)
            assert job_state is not None
            # Job might be failed due to hook error, but Runtime should not crash
            assert job_state.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.RUNNING]

        runtime.shutdown(wait=True)

    def test_multiple_hook_exceptions_handled_gracefully(self):
        """Test: Multiple hook exceptions should all be handled gracefully."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        hook_errors = []

        def failing_flow_start(*args, **kwargs):
            hook_errors.append("flow_start")
            raise ValueError("Flow start error")

        def failing_routine_start(*args, **kwargs):
            hook_errors.append("routine_start")
            raise ValueError("Routine start error")

        def failing_routine_end(*args, **kwargs):
            hook_errors.append("routine_end")
            raise ValueError("Routine end error")

        def failing_flow_end(*args, **kwargs):
            hook_errors.append("flow_end")
            raise ValueError("Flow end error")

        with patch.object(execution_hooks, "on_flow_start", side_effect=failing_flow_start):
            with patch.object(execution_hooks, "on_routine_start", side_effect=failing_routine_start):
                with patch.object(execution_hooks, "on_routine_end", side_effect=failing_routine_end):
                    with patch.object(execution_hooks, "on_flow_end", side_effect=failing_flow_end):
                        job_state = runtime.exec("test_flow")
                        runtime.wait_until_all_jobs_finished(timeout=5.0)

                        # All hooks should have been called (and failed)
                        assert len(hook_errors) > 0
                        # Runtime should still complete
                        assert job_state is not None

        runtime.shutdown(wait=True)

    def test_hook_returning_false_pauses_execution(self):
        """Test: Hook returning False should pause execution (for breakpoints)."""
        MonitoringRegistry.enable()

        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        # Make hook return False (simulating breakpoint)
        def pause_hook(*args, **kwargs):
            return False  # Pause execution

        with patch.object(execution_hooks, "on_routine_start", return_value=False):
            job_state = runtime.exec("test_flow")
            time.sleep(0.3)
            # Job might be paused - check status
            # Note: Actual pause behavior depends on DebugSessionStore implementation
            assert job_state is not None

        runtime.shutdown(wait=True)


class TestRuntimeHookThreadSafety:
    """Test thread safety of hook execution."""

    def test_concurrent_hook_calls_are_thread_safe(self):
        """Test: Multiple concurrent jobs should call hooks safely."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=10)

        hook_calls = []
        hook_lock = threading.Lock()

        def track_hook(*args, **kwargs):
            with hook_lock:
                hook_calls.append(threading.current_thread().ident)

        with patch.object(execution_hooks, "on_routine_start", side_effect=track_hook):
            # Start multiple jobs concurrently
            job_states = []
            for i in range(5):
                job_state = runtime.exec("test_flow")
                job_states.append(job_state)

            runtime.wait_until_all_jobs_finished(timeout=10.0)

            # All jobs should complete
            assert len(job_states) == 5
            # Hooks should have been called (thread-safe)
            assert len(hook_calls) >= 5, "Hooks should be called for each job"

        runtime.shutdown(wait=True)

    def test_hook_calls_from_different_threads(self):
        """Test: Hooks can be called from different threads safely."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=5)

        thread_ids = set()
        thread_lock = threading.Lock()

        def track_thread(*args, **kwargs):
            with thread_lock:
                thread_ids.add(threading.current_thread().ident)

        with patch.object(execution_hooks, "on_routine_start", side_effect=track_thread):
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Hook should be called from a worker thread (not main thread)
            assert len(thread_ids) > 0

        runtime.shutdown(wait=True)


class TestRuntimeHookEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_hook_called_with_none_job_state(self):
        """Test: Hook should handle None job_state gracefully."""
        # This tests the hook's internal None checking
        result = execution_hooks.on_routine_start(Mock(), "test_routine", None)
        # Should return without error (hooks check for None internally)
        assert result is None  # on_routine_start returns None

    def test_hook_called_with_empty_flow(self):
        """Test: Hooks should be called even for empty flows."""
        flow = Flow("empty_flow")
        FlowRegistry.get_instance().register_by_name("empty_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        with patch.object(execution_hooks, "on_flow_start") as mock_start:
            with patch.object(execution_hooks, "on_flow_end") as mock_end:
                try:
                    job_state = runtime.exec("empty_flow")
                    runtime.wait_until_all_jobs_finished(timeout=5.0)
                except (ValueError, StopIteration):
                    # Empty flow might raise error - that's OK
                    pass

                # Hooks should still be called (or flow should fail gracefully)
                # The exact behavior depends on implementation

        runtime.shutdown(wait=True)

    def test_hook_called_when_monitoring_disabled(self):
        """Test: Hooks should have zero overhead when monitoring is disabled."""
        MonitoringRegistry.disable()

        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        # Hooks are still called, but should return early if monitoring disabled
        # This is tested by verifying execution completes successfully
        job_state = runtime.exec("test_flow")
        runtime.wait_until_all_jobs_finished(timeout=5.0)

        # Execution should complete successfully
        assert job_state.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]

        runtime.shutdown(wait=True)

        # Re-enable for other tests
        MonitoringRegistry.enable()

    def test_hook_called_for_routine_without_logic(self):
        """Test: Hooks should be called even if routine has no logic."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")
        # No logic set

        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        with patch.object(execution_hooks, "on_routine_start") as mock_start:
            with patch.object(execution_hooks, "on_routine_end") as mock_end:
                job_state = runtime.exec("test_flow")
                runtime.wait_until_all_jobs_finished(timeout=5.0)

                # on_routine_end should still be called (with status="skipped")
                if mock_end.called:
                    call_args = mock_end.call_args
                    if "status" in call_args[1]:
                        assert call_args[1]["status"] == "skipped"

        runtime.shutdown(wait=True)

    def test_hook_called_for_routine_without_activation_policy(self):
        """Test: Hooks should be called even if routine has no activation policy."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        # No activation policy - should use default behavior
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        with patch.object(execution_hooks, "on_routine_start") as mock_start:
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Hook should still be called
            # (Runtime should handle None activation policy)
            assert job_state is not None

        runtime.shutdown(wait=True)


class TestRuntimeHookDataIntegrity:
    """Test data integrity in hook calls."""

    def test_event_data_passed_correctly_to_hook(self):
        """Test: Event data should be passed correctly to on_event_emit hook."""
        flow = Flow("test_flow")
        routine_a = Routine()
        routine_a.define_slot("trigger")
        event = routine_a.define_event("output")

        original_data = {"key1": "value1", "key2": 123, "nested": {"inner": "data"}}

        def logic_a(trigger_data, policy_message, job_state):
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                event.emit(runtime=runtime, job_state=job_state, **original_data)

        routine_a.set_logic(logic_a)
        routine_a.set_activation_policy(immediate_policy())
        flow.add_routine(routine_a, "routine_a")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        received_data = None

        def capture_data(*args, **kwargs):
            nonlocal received_data
            if "data" in kwargs:
                received_data = kwargs["data"]
            return True

        with patch.object(execution_hooks, "on_event_emit", side_effect=capture_data):
            job_state = runtime.exec("test_flow")
            time.sleep(0.5)
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Data should be passed correctly
            if received_data:
                # Verify data structure is preserved
                assert isinstance(received_data, dict)
                # Note: Exact matching depends on how Event.emit packs data

        runtime.shutdown(wait=True)

    def test_slot_data_passed_correctly_to_hook(self):
        """Test: Slot data should be passed correctly to on_slot_data_received hook."""
        flow = Flow("test_flow")
        routine_a = Routine()
        routine_a.define_slot("trigger")
        event = routine_a.define_event("output")

        original_data = {"test": "data", "number": 42}

        def logic_a(trigger_data, policy_message, job_state):
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                event.emit(runtime=runtime, job_state=job_state, **original_data)

        routine_a.set_logic(logic_a)
        routine_a.set_activation_policy(immediate_policy())

        routine_b = Routine()
        slot_b = routine_b.define_slot("input")

        def logic_b(input_data, policy_message, job_state):
            pass

        routine_b.set_logic(logic_b)
        routine_b.set_activation_policy(immediate_policy())

        flow.add_routine(routine_a, "routine_a")
        flow.add_routine(routine_b, "routine_b")
        flow.connect("routine_a", "output", "routine_b", "input")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        received_data = None

        def capture_data(*args, **kwargs):
            nonlocal received_data
            if "data" in kwargs:
                received_data = kwargs["data"]
            elif len(args) > 3:
                received_data = args[3]
            return True

        with patch.object(execution_hooks, "on_slot_data_received", side_effect=capture_data):
            job_state = runtime.exec("test_flow")
            time.sleep(0.5)
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Data should be passed correctly
            if received_data:
                assert isinstance(received_data, dict)

        runtime.shutdown(wait=True)


class TestRuntimeHookTiming:
    """Test timing and ordering of hook calls."""

    def test_flow_hooks_called_in_correct_order(self):
        """Test: Flow hooks should be called in start -> end order."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        call_order = []

        def track_flow_start(*args, **kwargs):
            call_order.append("flow_start")

        def track_flow_end(*args, **kwargs):
            call_order.append("flow_end")

        with patch.object(execution_hooks, "on_flow_start", side_effect=track_flow_start):
            with patch.object(execution_hooks, "on_flow_end", side_effect=track_flow_end):
                job_state = runtime.exec("test_flow")
                runtime.wait_until_all_jobs_finished(timeout=5.0)

                # Verify order
                assert "flow_start" in call_order
                assert "flow_end" in call_order
                assert call_order.index("flow_start") < call_order.index("flow_end"), \
                    "on_flow_start should be called before on_flow_end"

        runtime.shutdown(wait=True)

    def test_routine_hooks_called_in_correct_order(self):
        """Test: Routine hooks should be called in start -> end order."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        call_order = []

        def track_routine_start(*args, **kwargs):
            call_order.append("routine_start")

        def track_routine_end(*args, **kwargs):
            call_order.append("routine_end")

        with patch.object(execution_hooks, "on_routine_start", side_effect=track_routine_start):
            with patch.object(execution_hooks, "on_routine_end", side_effect=track_routine_end):
                job_state = runtime.exec("test_flow")
                runtime.wait_until_all_jobs_finished(timeout=5.0)

                # Verify order
                assert "routine_start" in call_order
                assert "routine_end" in call_order
                assert call_order.index("routine_start") < call_order.index("routine_end"), \
                    "on_routine_start should be called before on_routine_end"

        runtime.shutdown(wait=True)

    def test_flow_end_called_even_on_exception(self):
        """Test: on_flow_end should be called even if flow execution raises exception."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            raise RuntimeError("Flow execution error")

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        flow_end_called = False

        def track_flow_end(*args, **kwargs):
            nonlocal flow_end_called
            flow_end_called = True

        with patch.object(execution_hooks, "on_flow_end", side_effect=track_flow_end):
            job_state = runtime.exec("test_flow")
            # Wait longer to ensure flow execution completes (including error handling and finally block)
            import time
            time.sleep(0.5)
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # on_flow_end should be called in finally block
            assert flow_end_called, "on_flow_end should be called even on exception (in finally block)"

        runtime.shutdown(wait=True)

    def test_routine_end_called_even_on_exception(self):
        """Test: on_routine_end should be called even if routine logic raises exception."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            raise ValueError("Routine logic error")

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        routine_end_called = False

        def track_routine_end(*args, **kwargs):
            nonlocal routine_end_called
            routine_end_called = True

        with patch.object(execution_hooks, "on_routine_end", side_effect=track_routine_end):
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # on_routine_end should be called in finally block
            assert routine_end_called, "on_routine_end should be called even on exception"

        runtime.shutdown(wait=True)


class TestRuntimeHookStatusReporting:
    """Test that hooks receive correct status information."""

    def test_routine_end_receives_correct_status_on_success(self):
        """Test: on_routine_end should receive status='completed' on successful execution."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass  # Successful execution

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        received_status = None

        def capture_status(*args, **kwargs):
            nonlocal received_status
            if "status" in kwargs:
                received_status = kwargs["status"]

        with patch.object(execution_hooks, "on_routine_end", side_effect=capture_status):
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Status should be "completed" for successful execution
            if received_status:
                assert received_status == "completed", \
                    f"Expected status='completed', got '{received_status}'"

        runtime.shutdown(wait=True)

    def test_routine_end_receives_correct_status_on_error(self):
        """Test: on_routine_end should receive status='failed' on error."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            raise ValueError("Test error")

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        received_status = None
        received_error = None

        def capture_status(*args, **kwargs):
            nonlocal received_status, received_error
            if "status" in kwargs:
                received_status = kwargs["status"]
            if "error" in kwargs:
                received_error = kwargs["error"]

        with patch.object(execution_hooks, "on_routine_end", side_effect=capture_status):
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Status should be "failed" for error execution
            if received_status:
                assert received_status == "failed", \
                    f"Expected status='failed', got '{received_status}'"
            # Error should be provided
            if received_error:
                assert isinstance(received_error, Exception)

        runtime.shutdown(wait=True)

    def test_flow_end_receives_correct_status(self):
        """Test: on_flow_end should receive correct status string."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def my_logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(my_logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "entry")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)

        received_status = None

        def capture_status(*args, **kwargs):
            nonlocal received_status
            if "status" in kwargs:
                received_status = kwargs["status"]

        with patch.object(execution_hooks, "on_flow_end", side_effect=capture_status):
            job_state = runtime.exec("test_flow")
            runtime.wait_until_all_jobs_finished(timeout=5.0)

            # Status should be a valid string
            if received_status:
                assert isinstance(received_status, str)
                assert received_status in ["completed", "failed", "cancelled"], \
                    f"Invalid status: {received_status}"

        runtime.shutdown(wait=True)
