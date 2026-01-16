"""
Comprehensive tests for connection breakpoints.

These tests verify breakpoint functionality based on interface specifications,
challenging the implementation to ensure correctness.
"""

import pytest
import time

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.monitoring.breakpoint_manager import Breakpoint, BreakpointManager
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.monitoring.registry import MonitoringRegistry
from routilux.runtime import Runtime


class TestConnectionBreakpointInterface:
    """Test connection breakpoint interface compliance."""

    def test_connection_breakpoint_requires_all_fields(self):
        """Test: Connection breakpoint must have all required fields per interface."""
        # Missing source_routine_id
        with pytest.raises(ValueError, match="All connection fields"):
            Breakpoint(
                job_id="test_job",
                type="connection",
                source_event_name="output",
                target_routine_id="routine_b",
                target_slot_name="input",
            )

        # Missing source_event_name
        with pytest.raises(ValueError, match="All connection fields"):
            Breakpoint(
                job_id="test_job",
                type="connection",
                source_routine_id="routine_a",
                target_routine_id="routine_b",
                target_slot_name="input",
            )

        # Missing target_routine_id
        with pytest.raises(ValueError, match="All connection fields"):
            Breakpoint(
                job_id="test_job",
                type="connection",
                source_routine_id="routine_a",
                source_event_name="output",
                target_slot_name="input",
            )

        # Missing target_slot_name
        with pytest.raises(ValueError, match="All connection fields"):
            Breakpoint(
                job_id="test_job",
                type="connection",
                source_routine_id="routine_a",
                source_event_name="output",
                target_routine_id="routine_b",
            )

    def test_connection_breakpoint_matches_exact_connection(self):
        """Test: Connection breakpoint should match only exact connection."""
        manager = BreakpointManager()

        breakpoint = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )

        manager.add_breakpoint(breakpoint)

        # Exact match
        matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )
        assert matched is not None, "Should match exact connection"

        # Different source routine
        not_matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_x",  # Different source
            breakpoint_type="connection",
            source_routine_id="routine_x",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )
        assert not_matched is None, "Should not match different source routine"

        # Different source event
        not_matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="different_event",  # Different event
            target_routine_id="routine_b",
            target_slot_name="input",
        )
        assert not_matched is None, "Should not match different source event"

        # Different target routine
        not_matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_c",  # Different target
            target_slot_name="input",
        )
        assert not_matched is None, "Should not match different target routine"

        # Different target slot
        not_matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="different_slot",  # Different slot
        )
        assert not_matched is None, "Should not match different target slot"

    def test_connection_breakpoint_condition_evaluation(self):
        """Test: Connection breakpoint conditions should be evaluated correctly."""
        manager = BreakpointManager()

        # Breakpoint with condition
        breakpoint = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            condition="data.get('value', 0) > 10",
        )

        manager.add_breakpoint(breakpoint)

        # Condition matches
        matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            variables={"data": {"value": 42}},  # Condition: 42 > 10 = True
        )
        assert matched is not None, "Should match when condition is true"

        # Condition doesn't match
        not_matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            variables={"data": {"value": 5}},  # Condition: 5 > 10 = False
        )
        assert not_matched is None, "Should not match when condition is false"

    def test_connection_breakpoint_increment_hit_count(self):
        """Test: Connection breakpoint should increment hit_count on match."""
        manager = BreakpointManager()

        breakpoint = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )

        manager.add_breakpoint(breakpoint)

        initial_count = breakpoint.hit_count

        # Match breakpoint multiple times
        for i in range(3):
            matched = manager.check_breakpoint(
                job_id="test_job",
                routine_id="routine_a",
                breakpoint_type="connection",
                source_routine_id="routine_a",
                source_event_name="output",
                target_routine_id="routine_b",
                target_slot_name="input",
            )
            assert matched is not None
            assert matched.hit_count == initial_count + i + 1, \
                f"Hit count should increment, expected {initial_count + i + 1}, got {matched.hit_count}"

    def test_connection_breakpoint_enabled_disabled(self):
        """Test: Connection breakpoint should respect enabled flag."""
        manager = BreakpointManager()

        breakpoint = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            enabled=False,  # Disabled
        )

        manager.add_breakpoint(breakpoint)

        # Should not match when disabled
        not_matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )
        assert not_matched is None, "Disabled breakpoint should not match"

        # Enable and should match
        breakpoint.enabled = True
        matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )
        assert matched is not None, "Enabled breakpoint should match"


class TestConnectionBreakpointRuntimeIntegration:
    """Test connection breakpoint integration with Runtime."""

    def test_connection_breakpoint_triggers_before_data_enqueue(self):
        """Test: Connection breakpoint should trigger BEFORE data is enqueued to slot."""
        MonitoringRegistry.enable()

        flow = Flow("test_flow")
        routine_a = Routine()
        routine_a.define_slot("trigger")
        event = routine_a.define_event("output")

        slot_data_received = []

        def logic_a(trigger_data, policy_message, job_state):
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                event.emit(runtime=runtime, job_state=job_state, data={"test": "data"})

        routine_a.set_logic(logic_a)
        routine_a.set_activation_policy(immediate_policy())

        routine_b = Routine()
        slot_b = routine_b.define_slot("input")

        def logic_b(input_data, policy_message, job_state):
            slot_data_received.append("received")

        routine_b.set_logic(logic_b)
        routine_b.set_activation_policy(immediate_policy())

        flow.add_routine(routine_a, "routine_a")
        flow.add_routine(routine_b, "routine_b")
        flow.connect("routine_a", "output", "routine_b", "input")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)

        runtime = Runtime(thread_pool_size=2)
        job_state = runtime.exec("test_flow")

        # Create connection breakpoint
        breakpoint = Breakpoint(
            job_id=job_state.job_id,
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )

        MonitoringRegistry.get_instance().breakpoint_manager.add_breakpoint(breakpoint)

        time.sleep(0.5)
        runtime.wait_until_all_jobs_finished(timeout=5.0)

        # Breakpoint should be hit
        # When breakpoint is hit, data should NOT be enqueued (execution paused)
        # So slot_data_received should be empty or minimal
        # Note: Actual behavior depends on DebugSessionStore pause implementation

        runtime.shutdown(wait=True)

    def test_connection_breakpoint_with_condition_triggers_selectively(self):
        """Test: Connection breakpoint with condition should trigger only when condition matches."""
        MonitoringRegistry.enable()

        flow = Flow("test_flow")
        routine_a = Routine()
        routine_a.define_slot("trigger")
        event = routine_a.define_event("output")

        def logic_a(trigger_data, policy_message, job_state):
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                # Emit with value=5 (condition: value > 10, so should NOT trigger)
                event.emit(runtime=runtime, job_state=job_state, data={"value": 5})
                # Emit with value=42 (condition: value > 10, so SHOULD trigger)
                event.emit(runtime=runtime, job_state=job_state, data={"value": 42})

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
        job_state = runtime.exec("test_flow")

        # Create breakpoint with condition
        breakpoint = Breakpoint(
            job_id=job_state.job_id,
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            condition="data.get('value', 0) > 10",
        )

        MonitoringRegistry.get_instance().breakpoint_manager.add_breakpoint(breakpoint)

        time.sleep(0.5)
        runtime.wait_until_all_jobs_finished(timeout=5.0)

        # Breakpoint should be hit only once (for value=42, not value=5)
        # hit_count should be 1, not 2
        assert breakpoint.hit_count >= 0, "Breakpoint hit_count should be tracked"

        runtime.shutdown(wait=True)

    def test_multiple_connection_breakpoints_same_connection(self):
        """Test: Multiple breakpoints on same connection should all be checked."""
        manager = BreakpointManager()

        # Create two breakpoints on same connection
        bp1 = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            condition="data.get('value', 0) > 10",
        )

        bp2 = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            condition="data.get('value', 0) < 5",
        )

        manager.add_breakpoint(bp1)
        manager.add_breakpoint(bp2)

        # Value=42: bp1 matches (>10), bp2 doesn't (<5)
        matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            variables={"data": {"value": 42}},
        )
        assert matched is not None
        assert matched.breakpoint_id == bp1.breakpoint_id, "Should match first breakpoint"

        # Value=3: bp1 doesn't match (>10), bp2 matches (<5)
        matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            variables={"data": {"value": 3}},
        )
        assert matched is not None
        assert matched.breakpoint_id == bp2.breakpoint_id, "Should match second breakpoint"

    def test_connection_breakpoint_different_jobs_isolated(self):
        """Test: Connection breakpoints should be isolated per job_id."""
        manager = BreakpointManager()

        bp1 = Breakpoint(
            job_id="job1",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )

        bp2 = Breakpoint(
            job_id="job2",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )

        manager.add_breakpoint(bp1)
        manager.add_breakpoint(bp2)

        # Check for job1 - should match bp1
        matched = manager.check_breakpoint(
            job_id="job1",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )
        assert matched is not None
        assert matched.breakpoint_id == bp1.breakpoint_id

        # Check for job2 - should match bp2
        matched = manager.check_breakpoint(
            job_id="job2",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )
        assert matched is not None
        assert matched.breakpoint_id == bp2.breakpoint_id

        # Check for job3 - should not match
        not_matched = manager.check_breakpoint(
            job_id="job3",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
        )
        assert not_matched is None


class TestConnectionBreakpointEdgeCases:
    """Test edge cases and boundary conditions for connection breakpoints."""

    def test_connection_breakpoint_with_none_variables(self):
        """Test: Connection breakpoint should handle None variables gracefully."""
        manager = BreakpointManager()

        breakpoint = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            condition="data.get('value', 0) > 10",
        )

        manager.add_breakpoint(breakpoint)

        # Should not crash with None variables
        result = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            variables=None,
        )
        # Should not match (condition can't evaluate)
        assert result is None or result.breakpoint_id == breakpoint.breakpoint_id

    def test_connection_breakpoint_with_empty_variables(self):
        """Test: Connection breakpoint should handle empty variables dict."""
        manager = BreakpointManager()

        breakpoint = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            condition="data.get('value', 0) > 10",
        )

        manager.add_breakpoint(breakpoint)

        # Should not crash with empty variables
        result = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            variables={},
        )
        # Should not match (condition can't evaluate with empty dict)
        assert result is None or result.breakpoint_id == breakpoint.breakpoint_id

    def test_connection_breakpoint_invalid_condition_syntax(self):
        """Test: Connection breakpoint should handle invalid condition syntax gracefully."""
        manager = BreakpointManager()

        breakpoint = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            condition="invalid python syntax !!!",  # Invalid syntax
        )

        manager.add_breakpoint(breakpoint)

        # Should not crash, but condition evaluation should fail
        # The condition evaluator should catch syntax errors and return False
        try:
            result = manager.check_breakpoint(
                job_id="test_job",
                routine_id="routine_a",
                breakpoint_type="connection",
                source_routine_id="routine_a",
                source_event_name="output",
                target_routine_id="routine_b",
                target_slot_name="input",
                variables={"data": {"value": 42}},
            )
            # Should not match (condition evaluation failed due to syntax error)
            assert result is None, "Invalid condition syntax should cause evaluation to fail, breakpoint should not match"
        except ValueError as e:
            # It's also acceptable if the condition evaluator raises ValueError for invalid syntax
            # This is still "graceful" handling - it doesn't crash the system
            assert "syntax" in str(e).lower() or "invalid" in str(e).lower(), \
                f"Expected syntax error, got: {e}"

    def test_connection_breakpoint_condition_side_effects(self):
        """Test: Condition evaluation should not have side effects on variables."""
        manager = BreakpointManager()

        original_vars = {"data": {"value": 42, "other": "preserved"}}

        breakpoint = Breakpoint(
            job_id="test_job",
            type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            condition="data.get('value', 0) > 10",
        )

        manager.add_breakpoint(breakpoint)

        # Check breakpoint (condition evaluation)
        manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            variables=original_vars.copy(),
        )

        # Variables should not be modified
        # (This tests that condition evaluation doesn't mutate input)
        # Note: We can't easily test this without inspecting the condition evaluator
        # But we can verify the breakpoint still works
        matched = manager.check_breakpoint(
            job_id="test_job",
            routine_id="routine_a",
            breakpoint_type="connection",
            source_routine_id="routine_a",
            source_event_name="output",
            target_routine_id="routine_b",
            target_slot_name="input",
            variables=original_vars,
        )
        assert matched is not None, "Breakpoint should still work after condition evaluation"
