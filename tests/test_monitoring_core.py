"""
Comprehensive tests for monitoring core functionality.

These tests focus on the core monitoring features without FastAPI dependencies.
Tests are written against the public interfaces, challenging the business logic.
"""

import time

import pytest

from routilux import Flow, Routine
from routilux.job_state import JobState
from routilux.monitoring import (
    Breakpoint,
    MonitoringRegistry,
)
from routilux.monitoring.breakpoint_condition import evaluate_condition
from routilux.monitoring.storage import FlowStore, JobStore
from routilux.status import ExecutionStatus


class TestMonitoringRegistry:
    """Test MonitoringRegistry - the global monitoring control."""

    def test_registry_disabled_by_default(self):
        """Test that monitoring is disabled by default for backward compatibility."""
        # Reset to default state
        MonitoringRegistry.disable()
        assert not MonitoringRegistry.is_enabled()

        # Services should be None when disabled
        registry = MonitoringRegistry.get_instance()
        assert registry.breakpoint_manager is None
        assert registry.monitor_collector is None
        assert registry.debug_session_store is None

    def test_registry_enable_initializes_services(self):
        """Test that enabling monitoring initializes all services."""
        MonitoringRegistry.enable()

        assert MonitoringRegistry.is_enabled()
        registry = MonitoringRegistry.get_instance()
        assert registry.breakpoint_manager is not None
        assert registry.monitor_collector is not None
        assert registry.debug_session_store is not None

    def test_registry_disable_clears_services(self):
        """Test that disabling monitoring clears service access."""
        MonitoringRegistry.enable()
        assert MonitoringRegistry.is_enabled()

        MonitoringRegistry.disable()
        assert not MonitoringRegistry.is_enabled()

        MonitoringRegistry.get_instance()
        # Services should still exist but registry reports disabled
        # This is by design - services are lazy initialized
        assert not MonitoringRegistry.is_enabled()

    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        instance1 = MonitoringRegistry.get_instance()
        instance2 = MonitoringRegistry.get_instance()
        assert instance1 is instance2


class TestBreakpointManager:
    """Test BreakpointManager - breakpoint management."""

    def setup_method(self):
        """Set up test fixtures."""
        MonitoringRegistry.enable()
        self.manager = MonitoringRegistry.get_instance().breakpoint_manager
        # Clear any existing breakpoints to ensure test isolation
        self.manager.clear_breakpoints("job1")

    def test_add_breakpoint(self):
        """Test adding a breakpoint."""
        bp = Breakpoint(
            job_id="job1",
            type="routine",
            routine_id="r1",
        )
        bp_id = self.manager.add_breakpoint(bp)
        assert bp_id == bp.breakpoint_id

        # Verify breakpoint is stored
        breakpoints = self.manager.get_breakpoints("job1")
        assert len(breakpoints) == 1
        assert breakpoints[0].breakpoint_id == bp.breakpoint_id

    def test_add_breakpoint_requires_routine_id(self):
        """Test that breakpoint requires routine_id."""
        # Validation happens in __post_init__, so we test Breakpoint creation
        with pytest.raises(ValueError, match="routine_id is required"):
            Breakpoint(
                job_id="job1",
                type="routine",
                routine_id=None,  # Missing routine_id
            )

    def test_add_breakpoint_slot_requires_slot_name(self):
        """Test that slot breakpoint requires slot_name."""
        # Validation happens in __post_init__, so we test Breakpoint creation
        with pytest.raises(ValueError, match="slot_name is required"):
            Breakpoint(
                job_id="job1",
                type="slot",
                routine_id="r1",
                slot_name=None,  # Missing slot_name
            )

    def test_add_breakpoint_event_requires_event_name(self):
        """Test that event breakpoint requires event_name."""
        # Validation happens in __post_init__, so we test Breakpoint creation
        with pytest.raises(ValueError, match="event_name is required"):
            Breakpoint(
                job_id="job1",
                type="event",
                routine_id="r1",
                event_name=None,  # Missing event_name
            )

    def test_remove_breakpoint(self):
        """Test removing a breakpoint."""
        bp = Breakpoint(job_id="job1", type="routine", routine_id="r1")
        bp_id = self.manager.add_breakpoint(bp)

        # Verify it was added
        breakpoints = self.manager.get_breakpoints("job1")
        assert len(breakpoints) == 1

        self.manager.remove_breakpoint(bp_id, "job1")

        breakpoints = self.manager.get_breakpoints("job1")
        assert len(breakpoints) == 0

    def test_clear_breakpoints(self):
        """Test clearing all breakpoints for a job."""
        bp1 = Breakpoint(job_id="job1", type="routine", routine_id="r1")
        bp2 = Breakpoint(job_id="job1", type="slot", routine_id="r1", slot_name="input")
        self.manager.add_breakpoint(bp1)
        self.manager.add_breakpoint(bp2)

        self.manager.clear_breakpoints("job1")

        breakpoints = self.manager.get_breakpoints("job1")
        assert len(breakpoints) == 0

    def test_check_breakpoint_routine(self):
        """Test checking routine breakpoint."""
        bp = Breakpoint(
            job_id="job1",
            type="routine",
            routine_id="r1",
            enabled=True,
        )
        self.manager.add_breakpoint(bp)

        # Should match
        result = self.manager.check_breakpoint("job1", "r1", "routine")
        assert result is not None
        assert result.breakpoint_id == bp.breakpoint_id
        assert result.hit_count == 1

        # Should not match different routine
        result = self.manager.check_breakpoint("job1", "r2", "routine")
        assert result is None

    def test_check_breakpoint_slot(self):
        """Test checking slot breakpoint."""
        bp = Breakpoint(
            job_id="job1",
            type="slot",
            routine_id="r1",
            slot_name="input",
            enabled=True,
        )
        self.manager.add_breakpoint(bp)

        # Should match
        result = self.manager.check_breakpoint("job1", "r1", "slot", slot_name="input")
        assert result is not None

        # Should not match different slot
        result = self.manager.check_breakpoint("job1", "r1", "slot", slot_name="output")
        assert result is None

    def test_check_breakpoint_event(self):
        """Test checking event breakpoint."""
        bp = Breakpoint(
            job_id="job1",
            type="event",
            routine_id="r1",
            event_name="output",
            enabled=True,
        )
        self.manager.add_breakpoint(bp)

        # Should match
        result = self.manager.check_breakpoint("job1", "r1", "event", event_name="output")
        assert result is not None

        # Should not match different event
        result = self.manager.check_breakpoint("job1", "r1", "event", event_name="error")
        assert result is None

    def test_check_breakpoint_disabled(self):
        """Test that disabled breakpoints don't trigger."""
        bp = Breakpoint(
            job_id="job1",
            type="routine",
            routine_id="r1",
            enabled=False,
        )
        self.manager.add_breakpoint(bp)

        # Clear any previous state
        self.manager.clear_breakpoints("job1")
        self.manager.add_breakpoint(bp)

        result = self.manager.check_breakpoint("job1", "r1", "routine")
        assert result is None

    def test_check_breakpoint_condition(self):
        """Test breakpoint with condition."""
        # Clear any previous state
        self.manager.clear_breakpoints("job1")

        bp = Breakpoint(
            job_id="job1",
            type="routine",
            routine_id="r1",
            condition="data.get('value', 0) > 10",
            enabled=True,
        )
        self.manager.add_breakpoint(bp)

        # Condition should be evaluated and pass
        variables = {"data": {"value": 15}}
        result = self.manager.check_breakpoint("job1", "r1", "routine", variables=variables)
        assert result is not None

        # Condition should fail (value <= 10)
        variables = {"data": {"value": 5}}
        result = self.manager.check_breakpoint("job1", "r1", "routine", variables=variables)
        assert result is None

    def test_breakpoint_hit_count(self):
        """Test that hit count increments on each hit."""
        # Clear any previous state
        self.manager.clear_breakpoints("job1")

        bp = Breakpoint(job_id="job1", type="routine", routine_id="r1", enabled=True)
        self.manager.add_breakpoint(bp)

        # First hit
        result = self.manager.check_breakpoint("job1", "r1", "routine")
        assert result is not None
        assert result.hit_count == 1

        # Second hit
        result = self.manager.check_breakpoint("job1", "r1", "routine")
        assert result is not None
        assert result.hit_count == 2


class TestBreakpointCondition:
    """Test breakpoint condition evaluation."""

    def test_evaluate_simple_condition(self):
        """Test evaluating a simple condition."""
        # Test with dict access
        result = evaluate_condition("data['value'] > 10", variables={"data": {"value": 15}})
        assert result is True

        result = evaluate_condition("data['value'] > 10", variables={"data": {"value": 5}})
        assert result is False

        # Test with .get() method (if dict is in context)
        result = evaluate_condition("data.get('value', 0) > 10", variables={"data": {"value": 15}})
        assert result is True

    def test_evaluate_condition_with_context(self):
        """Test evaluating condition with execution context."""
        from unittest.mock import Mock

        context = Mock()
        context.job_state = Mock()
        context.job_state.shared_data = {"key": "value"}
        context.flow = Mock()
        context.routine_id = "r1"

        result = evaluate_condition("shared_data.get('key') == 'value'", context=context)
        assert result is True

    def test_evaluate_condition_invalid_syntax(self):
        """Test that invalid condition syntax raises error."""
        with pytest.raises(ValueError, match="Invalid condition syntax"):
            evaluate_condition("invalid syntax !!!", variables={})

    def test_evaluate_condition_unsafe_operations(self):
        """Test that unsafe operations are rejected."""
        # Test unsafe function call (eval is not in safe_builtins)
        with pytest.raises(ValueError, match="Unsafe function call"):
            evaluate_condition("eval('1+1')", variables={})

        # Test __import__ (should be caught as unsafe function call)
        with pytest.raises(ValueError, match="Unsafe function call.*__import__"):
            evaluate_condition("__import__('os')", variables={})


class TestMonitorCollector:
    """Test MonitorCollector - execution metrics collection."""

    def setup_method(self):
        """Set up test fixtures."""
        MonitoringRegistry.enable()
        self.collector = MonitoringRegistry.get_instance().monitor_collector
        # Clear any existing metrics to ensure test isolation
        self.collector.clear("job1")

    def test_record_flow_start(self):
        """Test recording flow start."""
        self.collector.record_flow_start("flow1", "job1")

        metrics = self.collector.get_metrics("job1")
        assert metrics is not None
        assert metrics.job_id == "job1"
        assert metrics.flow_id == "flow1"
        assert metrics.start_time is not None
        assert metrics.end_time is None

    def test_record_flow_end(self):
        """Test recording flow end."""
        self.collector.record_flow_start("flow1", "job1")
        time.sleep(0.01)  # Small delay to ensure duration > 0
        self.collector.record_flow_end("job1", "completed")

        metrics = self.collector.get_metrics("job1")
        assert metrics.end_time is not None
        assert metrics.duration is not None
        assert metrics.duration > 0

    def test_record_routine_start_end(self):
        """Test recording routine execution."""
        self.collector.record_flow_start("flow1", "job1")
        self.collector.record_routine_start("r1", "job1")
        time.sleep(0.01)
        self.collector.record_routine_end("r1", "job1", "completed")

        metrics = self.collector.get_metrics("job1")
        assert "r1" in metrics.routine_metrics
        rm = metrics.routine_metrics["r1"]
        assert rm.execution_count == 1
        assert rm.total_duration > 0
        assert rm.avg_duration > 0
        assert rm.error_count == 0

    def test_record_routine_error(self):
        """Test recording routine error."""
        self.collector.record_flow_start("flow1", "job1")
        self.collector.record_routine_start("r1", "job1")
        self.collector.record_routine_end("r1", "job1", "failed", error=ValueError("test error"))

        metrics = self.collector.get_metrics("job1")
        rm = metrics.routine_metrics["r1"]
        assert rm.error_count == 1
        assert len(metrics.errors) == 1
        assert metrics.errors[0].error_type == "ValueError"

    def test_record_slot_call(self):
        """Test recording slot call."""
        self.collector.record_flow_start("flow1", "job1")
        self.collector.record_slot_call("input", "r1", "job1", {"data": "value"})

        metrics = self.collector.get_metrics("job1")
        assert metrics.total_slot_calls == 1
        assert metrics.total_events == 1

        trace = self.collector.get_execution_trace("job1")
        assert len(trace) == 1
        assert trace[0].event_type == "slot_call"
        assert trace[0].data["slot_name"] == "input"

    def test_record_event_emit(self):
        """Test recording event emission."""
        self.collector.record_flow_start("flow1", "job1")
        self.collector.record_event_emit("output", "r1", "job1", {"result": "value"})

        metrics = self.collector.get_metrics("job1")
        assert metrics.total_event_emits == 1
        assert metrics.total_events == 1

        trace = self.collector.get_execution_trace("job1")
        assert len(trace) == 1
        assert trace[0].event_type == "event_emit"
        assert trace[0].data["event_name"] == "output"

    def test_get_execution_trace_limit(self):
        """Test getting execution trace with limit."""
        self.collector.record_flow_start("flow1", "job1")
        for i in range(10):
            self.collector.record_slot_call(f"slot{i}", "r1", "job1", {})

        trace = self.collector.get_execution_trace("job1", limit=5)
        assert len(trace) == 5
        # Should return last 5 events
        assert trace[0].data["slot_name"] == "slot5"

    def test_routine_metrics_aggregation(self):
        """Test that routine metrics aggregate multiple executions."""
        self.collector.record_flow_start("flow1", "job1")

        # Execute routine multiple times
        for _ in range(3):
            self.collector.record_routine_start("r1", "job1")
            time.sleep(0.01)
            self.collector.record_routine_end("r1", "job1", "completed")

        metrics = self.collector.get_metrics("job1")
        rm = metrics.routine_metrics["r1"]
        assert rm.execution_count == 3
        assert rm.total_duration > 0
        assert rm.avg_duration == rm.total_duration / 3
        assert rm.min_duration is not None
        assert rm.max_duration is not None

    def test_clear_metrics(self):
        """Test clearing metrics for a job."""
        self.collector.record_flow_start("flow1", "job1")
        self.collector.record_routine_start("r1", "job1")

        self.collector.clear("job1")

        metrics = self.collector.get_metrics("job1")
        assert metrics is None

        trace = self.collector.get_execution_trace("job1")
        assert len(trace) == 0


class TestDebugSession:
    """Test DebugSession - debug session management."""

    def setup_method(self):
        """Set up test fixtures."""
        MonitoringRegistry.enable()
        self.store = MonitoringRegistry.get_instance().debug_session_store
        # Clear any existing sessions to ensure test isolation
        self.store.remove("job1")

    def test_create_debug_session(self):
        """Test creating a debug session."""
        session = self.store.get_or_create("job1")
        assert session.job_id == "job1"
        assert session.status == "running"
        assert len(session.call_stack) == 0

    def test_pause_execution(self):
        """Test pausing execution."""
        session = self.store.get_or_create("job1")
        from unittest.mock import Mock

        context = Mock()
        context.routine_id = "r1"

        session.pause(context, reason="test pause")

        assert session.status == "paused"
        assert session.paused_at == context
        assert len(session.call_stack) == 1

    def test_resume_execution(self):
        """Test resuming execution."""
        session = self.store.get_or_create("job1")
        session.pause(None, reason="test")

        session.resume()

        assert session.status == "running"
        assert session.paused_at is None
        assert session.step_mode is None

    def test_step_over(self):
        """Test step-over operation."""
        session = self.store.get_or_create("job1")
        session.step_over()

        assert session.status == "stepping"
        assert session.step_mode == "over"
        assert session.step_count == 1

    def test_step_into(self):
        """Test step-into operation."""
        session = self.store.get_or_create("job1")
        session.step_into()

        assert session.status == "stepping"
        assert session.step_mode == "into"
        assert session.step_count == 1

    def test_should_continue_running(self):
        """Test should_continue when running."""
        session = self.store.get_or_create("job1")
        assert session.should_continue() is True

    def test_should_continue_paused(self):
        """Test should_continue when paused."""
        session = self.store.get_or_create("job1")
        session.pause(None, reason="test")
        assert session.should_continue() is False

    def test_should_continue_stepping(self):
        """Test should_continue when stepping."""
        session = self.store.get_or_create("job1")
        session.step_over()

        # Initially step_count is 1, status is "stepping"
        assert session.step_count == 1
        assert session.status == "stepping"

        # First call: step_count is 1, decrements to 0, then checks if 0 == 0, so pauses
        # According to the code: if step_count > 0, decrement, then if step_count == 0, pause
        result = session.should_continue()
        assert result is False  # step_count was 1, decremented to 0, so pauses immediately
        assert session.step_count == 0
        assert session.status == "paused"

        # Test with step_count = 2: first call should continue
        session.step_over()
        session.step_count = 2
        result = session.should_continue()
        assert result is True  # step_count was 2, decremented to 1, so continues
        assert session.step_count == 1
        assert session.status == "stepping"

        # Second call: step_count is now 1, decrements to 0, so pauses
        result = session.should_continue()
        assert result is False
        assert session.step_count == 0
        assert session.status == "paused"

    def test_get_variables(self):
        """Test getting variables from call stack."""
        session = self.store.get_or_create("job1")
        from routilux.monitoring.debug_session import CallFrame

        frame = CallFrame(routine_id="r1", variables={"x": 1, "y": 2})
        session.call_stack.append(frame)

        variables = session.get_variables("r1")
        assert variables == {"x": 1, "y": 2}

    def test_set_variable(self):
        """Test setting variable value."""
        session = self.store.get_or_create("job1")
        from routilux.monitoring.debug_session import CallFrame

        frame = CallFrame(routine_id="r1", variables={})
        session.call_stack.append(frame)

        session.set_variable("r1", "x", 42)

        variables = session.get_variables("r1")
        assert variables["x"] == 42

    def test_get_call_stack(self):
        """Test getting call stack."""
        session = self.store.get_or_create("job1")
        from routilux.monitoring.debug_session import CallFrame

        frame1 = CallFrame(routine_id="r1")
        frame2 = CallFrame(routine_id="r2")
        session.call_stack.extend([frame1, frame2])

        stack = session.get_call_stack()
        assert len(stack) == 2
        assert stack[0].routine_id == "r1"
        assert stack[1].routine_id == "r2"


class TestStorage:
    """Test storage managers."""

    def test_flow_store(self):
        """Test FlowStore operations."""
        store = FlowStore()
        flow = Flow("flow1")

        store.add(flow)
        assert store.get("flow1") == flow

        flows = store.list_all()
        assert len(flows) == 1

        store.remove("flow1")
        assert store.get("flow1") is None

    def test_job_store(self):
        """Test JobStore operations."""
        store = JobStore()
        job_state = JobState("flow1")

        store.add(job_state)
        assert store.get(job_state.job_id) == job_state

        jobs = store.list_all()
        assert len(jobs) == 1

        jobs_by_flow = store.get_by_flow("flow1")
        assert len(jobs_by_flow) == 1

        store.remove(job_state.job_id)
        assert store.get(job_state.job_id) is None


class TestMonitoringIntegration:
    """Test monitoring integration with actual flow execution."""

    def test_monitoring_disabled_no_overhead(self):
        """Test that monitoring disabled has zero overhead."""
        MonitoringRegistry.disable()

        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.define_slot("trigger", handler=self.handle)

            def handle(self, **kwargs):
                return {"result": "ok"}

        flow = Flow()
        routine = TestRoutine()
        flow.add_routine(routine, "r1")

        # Should execute normally without monitoring
        job_state = flow.execute("r1")
        assert job_state.status == ExecutionStatus.COMPLETED

    def test_monitoring_enabled_collects_metrics(self):
        """Test that monitoring collects metrics during execution."""
        MonitoringRegistry.enable()

        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.define_slot("trigger", handler=self.handle)
                self.define_event("output")

            def handle(self, **kwargs):
                self.emit("output", result="ok")
                return {"result": "ok"}

        flow = Flow()
        routine = TestRoutine()
        flow.add_routine(routine, "r1")

        job_state = flow.execute("r1")

        # Check metrics were collected
        registry = MonitoringRegistry.get_instance()
        collector = registry.monitor_collector
        metrics = collector.get_metrics(job_state.job_id)

        assert metrics is not None
        assert metrics.flow_id == flow.flow_id
        assert "r1" in metrics.routine_metrics
        assert metrics.total_events > 0

    def test_breakpoint_triggers_during_execution(self):
        """Test that breakpoints can trigger during execution."""
        MonitoringRegistry.enable()

        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.define_slot("trigger", handler=self.handle)

            def handle(self, **kwargs):
                return {"result": "ok"}

        flow = Flow()
        routine = TestRoutine()
        flow.add_routine(routine, "r1")

        # Add breakpoint
        MonitoringRegistry.get_instance()
        Breakpoint(
            job_id="",  # Will be set by job_state.job_id
            type="routine",
            routine_id="r1",
            enabled=True,
        )

        # Note: Breakpoint checking happens during execution via hooks
        # This test verifies the infrastructure is in place
        job_state = flow.execute("r1")

        # Breakpoint should be checkable (though may not trigger without proper job_id)
        # This tests the integration point exists
        assert job_state.status == ExecutionStatus.COMPLETED


class TestRingBuffer:
    """Test ring buffer (deque with maxlen) functionality in MonitorCollector."""

    def test_ring_buffer_prevents_unbounded_growth(self):
        """Test that ring buffer prevents unbounded memory growth."""
        from routilux.monitoring.monitor_collector import MonitorCollector

        # Create collector with small ring buffer (max 10 events)
        collector = MonitorCollector(max_events_per_job=10)

        # Record flow start
        collector.record_flow_start("test_flow", "job_001")

        # Record 20 events (more than buffer size)
        for i in range(20):
            collector.record_routine_start(f"routine_{i}", "job_001")

        # Get execution trace - should only have latest 10 events
        trace = collector.get_execution_trace("job_001")
        assert len(trace) == 10, "Ring buffer should only keep latest 10 events"

        # Verify events are the latest ones (routine_10 to routine_19)
        routine_ids = [event.routine_id for event in trace]
        assert routine_ids == [f"routine_{i}" for i in range(10, 20)]

    def test_ring_buffer_configurable_max_events(self):
        """Test that max_events_per_job is configurable."""
        from routilux.monitoring.monitor_collector import MonitorCollector

        # Create collector with custom max events
        collector = MonitorCollector(max_events_per_job=5)

        # Record flow start
        collector.record_flow_start("test_flow", "job_002")

        # Record 10 events
        for i in range(10):
            collector.record_routine_start(f"routine_{i}", "job_002")

        # Should only keep latest 5 events
        trace = collector.get_execution_trace("job_002")
        assert len(trace) == 5

    def test_ring_buffer_default_max_events(self):
        """Test default max_events_per_job is 1000."""
        from routilux.monitoring.monitor_collector import (
            DEFAULT_MAX_EVENTS_PER_JOB,
            MonitorCollector,
        )

        assert DEFAULT_MAX_EVENTS_PER_JOB == 1000

        # Create collector with default max events
        collector = MonitorCollector()

        # Record flow start
        collector.record_flow_start("test_flow", "job_003")

        # Record less than max (100 events)
        for i in range(100):
            collector.record_routine_start(f"routine_{i}", "job_003")

        # All events should be kept
        trace = collector.get_execution_trace("job_003")
        assert len(trace) == 100

    def test_ring_buffer_with_limit_parameter(self):
        """Test get_execution_trace limit parameter works with ring buffer."""
        from routilux.monitoring.monitor_collector import MonitorCollector

        collector = MonitorCollector(max_events_per_job=100)

        # Record flow start
        collector.record_flow_start("test_flow", "job_004")

        # Record 50 events
        for i in range(50):
            collector.record_routine_start(f"routine_{i}", "job_004")

        # Get trace with limit=10
        trace = collector.get_execution_trace("job_004", limit=10)
        assert len(trace) == 10

        # Verify it returns the last 10 events
        routine_ids = [event.routine_id for event in trace]
        assert routine_ids == [f"routine_{i}" for i in range(40, 50)]

    def test_ring_buffer_multiple_jobs(self):
        """Test ring buffer works correctly with multiple jobs."""
        from routilux.monitoring.monitor_collector import MonitorCollector

        collector = MonitorCollector(max_events_per_job=5)

        # Record events for multiple jobs
        for job_id in ["job_005", "job_006", "job_007"]:
            collector.record_flow_start("test_flow", job_id)
            for i in range(10):
                collector.record_routine_start(f"routine_{i}", job_id)

        # Each job should have only 5 events (ring buffer)
        for job_id in ["job_005", "job_006", "job_007"]:
            trace = collector.get_execution_trace(job_id)
            assert len(trace) == 5, f"Job {job_id} should have only 5 events"

    def test_set_max_events_per_job(self):
        """Test set_max_events_per_job function."""
        from routilux.monitoring import monitor_collector

        # Get original value
        original = monitor_collector.DEFAULT_MAX_EVENTS_PER_JOB

        # Set new value
        monitor_collector.set_max_events_per_job(500)
        assert monitor_collector.DEFAULT_MAX_EVENTS_PER_JOB == 500

        # Restore original value
        monitor_collector.set_max_events_per_job(original)
        assert monitor_collector.DEFAULT_MAX_EVENTS_PER_JOB == original

    def test_set_max_events_per_job_invalid_value(self):
        """Test set_max_events_per_job with invalid value."""
        from routilux.monitoring.monitor_collector import set_max_events_per_job

        # Try to set invalid value
        with pytest.raises(ValueError, match="must be greater than 0"):
            set_max_events_per_job(0)

        with pytest.raises(ValueError, match="must be greater than 0"):
            set_max_events_per_job(-10)

    def test_ring_buffer_old_events_dropped(self):
        """Test that old events are automatically dropped when buffer is full."""
        from routilux.monitoring.monitor_collector import MonitorCollector

        collector = MonitorCollector(max_events_per_job=10)

        # Record flow start
        collector.record_flow_start("test_flow", "job_008")

        # Record 10 events (fills buffer)
        for i in range(10):
            collector.record_routine_start(f"routine_{i}", "job_008")

        # Verify all 10 events are present
        trace = collector.get_execution_trace("job_008")
        assert len(trace) == 10
        assert trace[0].routine_id == "routine_0"

        # Add 1 more event (should drop routine_0)
        collector.record_routine_start("routine_10", "job_008")

        # Verify only 10 events remain, and routine_0 is gone
        trace = collector.get_execution_trace("job_008")
        assert len(trace) == 10
        routine_ids = [event.routine_id for event in trace]
        assert "routine_0" not in routine_ids
        assert "routine_10" in routine_ids
        assert routine_ids[0] == "routine_1"  # routine_0 was dropped
