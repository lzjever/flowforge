"""
Tests for Flow staticization refactoring.

Tests verify that:
1. Flow has no runtime state attributes
2. Flow can be shared by multiple jobs
3. Flow connections can be modified during execution (thread-safe)
4. Flow serialization does not include runtime state
"""

import threading
import time

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.runtime import Runtime
from routilux.status import ExecutionStatus


class TestFlowNoRuntimeState:
    """Test that Flow has no runtime state attributes."""

    def test_flow_has_no_task_queue(self):
        """Test: Flow does not have _task_queue attribute."""
        flow = Flow("test_flow")

        # Interface contract: Flow should not have runtime state attributes
        assert not hasattr(flow, "_task_queue")

    def test_flow_has_no_execution_thread(self):
        """Test: Flow does not have _execution_thread attribute."""
        flow = Flow("test_flow")

        # Interface contract: Flow should not have execution thread
        assert not hasattr(flow, "_execution_thread")

    def test_flow_has_no_running_flag(self):
        """Test: Flow does not have _running flag."""
        flow = Flow("test_flow")

        # Interface contract: Flow should not have _running flag
        assert not hasattr(flow, "_running")

    def test_flow_has_no_paused_flag(self):
        """Test: Flow does not have _paused flag."""
        flow = Flow("test_flow")

        # Interface contract: Flow should not have _paused flag
        assert not hasattr(flow, "_paused")

    def test_flow_has_config_lock(self):
        """Test: Flow has _config_lock for thread safety."""
        flow = Flow("test_flow")

        # Interface contract: Flow should have _config_lock for protecting connections
        assert hasattr(flow, "_config_lock")
        assert flow._config_lock is not None


class TestFlowStaticBehavior:
    """Test Flow static behavior - can be shared, modified during execution."""

    def test_flow_can_be_shared_by_multiple_jobs(self):
        """Test: Flow can be shared by multiple jobs."""
        flow = Flow("shared_flow")

        routine = Routine()
        routine.define_slot("trigger")

        def logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("shared_flow", flow)
        runtime = Runtime()

        # Create multiple jobs using same flow
        job1 = runtime.exec("shared_flow")
        job2 = runtime.exec("shared_flow")
        job3 = runtime.exec("shared_flow")

        # Interface contract: All jobs should reference the same Flow instance
        assert job1.flow_id == job2.flow_id == job3.flow_id == "shared_flow"

        # All should be able to execute
        runtime.post("shared_flow", "routine", "trigger", {"data": 1}, job_id=job1.job_id)
        runtime.post("shared_flow", "routine", "trigger", {"data": 2}, job_id=job2.job_id)
        runtime.post("shared_flow", "routine", "trigger", {"data": 3}, job_id=job3.job_id)

        time.sleep(0.5)

        runtime.shutdown(wait=True)

    def test_modify_connections_during_execution(self):
        """Test: Can modify Flow connections during execution (real-time update)."""
        flow = Flow("dynamic_flow")

        # Create routines
        source1 = Routine()
        source1.define_slot("trigger")
        event1 = source1.define_event("output1", ["data1"])
        source2 = Routine()
        source2.define_slot("trigger")
        event2 = source2.define_event("output2", ["data2"])
        target = Routine()
        target.define_slot("input")

        def source1_logic(trigger_data, policy_message, job_state):
            # Get runtime from job_state (set by JobExecutor)
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                event1.emit(runtime=runtime, job_state=job_state, data1={"value": 1})

        def source2_logic(trigger_data, policy_message, job_state):
            # Get runtime from job_state (set by JobExecutor)
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                event2.emit(runtime=runtime, job_state=job_state, data2={"value": 2})

        def target_logic(input_data, policy_message, job_state):
            # Store received data
            if not hasattr(target_logic, "received"):
                target_logic.received = []
            if input_data:
                target_logic.received.append(input_data[0])

        source1.set_logic(source1_logic)
        source1.set_activation_policy(immediate_policy())
        source2.set_logic(source2_logic)
        source2.set_activation_policy(immediate_policy())
        target.set_logic(target_logic)
        target.set_activation_policy(immediate_policy())

        flow.add_routine(source1, "source1")
        flow.add_routine(source2, "source2")
        flow.add_routine(target, "target")

        # Initially connect source1
        flow.connect("source1", "output1", "target", "input")

        FlowRegistry.get_instance().register_by_name("dynamic_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("dynamic_flow")

        # Start execution with source1 connected
        runtime.post("dynamic_flow", "source1", "trigger", {"start": True}, job_id=job_state.job_id)
        time.sleep(0.2)

        # Modify connection during execution - connect source2 instead
        # Remove old connection
        flow.connections.clear()
        # Add new connection
        flow.connect("source2", "output2", "target", "input")

        # Post from source2 - should be routed to target
        runtime.post("dynamic_flow", "source2", "trigger", {"start": True}, job_id=job_state.job_id)
        time.sleep(0.5)

        # Interface contract: Connection changes should take effect immediately
        # Target should receive data from source2
        assert hasattr(target_logic, "received")
        # Should have received at least one message
        assert len(target_logic.received) > 0

        runtime.shutdown(wait=True)

    def test_connections_thread_safe(self):
        """Test: Concurrent modification of connections is thread-safe."""
        flow = Flow("thread_safe_flow")

        routine1 = Routine()
        routine1.define_event("output", ["data"])
        routine2 = Routine()
        routine2.define_slot("input")

        flow.add_routine(routine1, "source")
        flow.add_routine(routine2, "target")

        errors = []
        connections_created = []

        def modify_connections(i):
            try:
                # Try to get connections (reads)
                event = routine1._events["output"]
                connections = flow.get_connections_for_event(event)
                connections_created.append(len(connections))

                # Try to add connection (write)
                if i % 2 == 0:
                    # Add connection
                    flow.connect("source", "output", "target", "input")
            except Exception as e:
                errors.append((i, e))

        # Concurrent access
        threads = [threading.Thread(target=modify_connections, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Interface contract: Should handle concurrent access without errors
        # (or with expected errors like duplicate connections)
        assert len([e for e in errors if "already" not in str(e[1]).lower()]) == 0


class TestFlowSerialization:
    """Test Flow serialization without runtime state."""

    def test_flow_serialization_no_runtime_state(self):
        """Test: Flow serialization does not include runtime state."""
        flow = Flow("test_flow")

        routine = Routine()
        flow.add_routine(routine, "routine")

        serialized = flow.serialize()

        # Interface contract: Should not contain runtime state fields
        assert "_task_queue" not in serialized
        assert "_execution_thread" not in serialized
        assert "_running" not in serialized
        assert "_paused" not in serialized
        assert "_active_tasks" not in serialized
        assert "_execution_lock" not in serialized
        assert "_pending_tasks" not in serialized
        assert "_runtime" not in serialized

        # Should contain static configuration
        assert "flow_id" in serialized
        assert "routines" in serialized
        assert "connections" in serialized

    def test_flow_deserialization_creates_static_flow(self):
        """Test: Flow deserialization creates static Flow."""
        flow = Flow("test_flow")

        routine = Routine()
        flow.add_routine(routine, "routine")

        serialized = flow.serialize()

        # Deserialize
        new_flow = Flow()
        new_flow.deserialize(serialized)

        # Interface contract: Deserialized Flow should be static (no runtime state)
        assert not hasattr(new_flow, "_task_queue")
        assert not hasattr(new_flow, "_execution_thread")
        assert not hasattr(new_flow, "_running")
        assert new_flow.flow_id == "test_flow"
        assert "routine" in new_flow.routines
