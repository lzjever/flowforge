"""
Tests for entry concept removal refactoring.

Tests verify that:
1. Runtime.exec() no longer accepts entry_routine_id and entry_params
2. JobExecutor.start() no longer accepts entry parameters
3. All routines start in IDLE state
4. Must use Runtime.post() to start routines
"""

import time

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.job_executor import JobExecutor
from routilux.job_manager import get_job_manager
from routilux.job_state import JobState
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.runtime import Runtime
from routilux.status import ExecutionStatus, RoutineStatus


class TestNoEntryParameters:
    """Test that entry parameters are removed from interfaces."""

    def test_runtime_exec_no_entry_routine(self):
        """Test: Runtime.exec() does not accept entry_routine_id parameter."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")

        def logic(trigger_data, policy_message, job_state):
            pass

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Interface contract: exec() should not accept entry_routine_id
        # Should work without it
        job_state = runtime.exec("test_flow")

        assert job_state is not None
        assert job_state.status == ExecutionStatus.RUNNING

        runtime.shutdown(wait=True)

    def test_job_executor_start_no_entry(self):
        """Test: JobExecutor.start() does not accept entry parameters."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")
        flow.add_routine(routine, "routine")

        job_state = JobState(flow_id=flow.flow_id)
        job_manager = get_job_manager()

        executor = JobExecutor(
            flow=flow,
            job_state=job_state,
            global_thread_pool=job_manager.global_thread_pool,
            timeout=None,
        )

        # Interface contract: start() should not accept entry_routine_id or entry_params
        # Should work without them
        executor.start()

        # Verify it started
        assert executor._running is True
        assert executor.event_loop_thread is not None

        executor.stop()

    def test_global_job_manager_start_no_entry(self):
        """Test: GlobalJobManager.start_job() does not accept entry parameters."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("trigger")
        flow.add_routine(routine, "routine")

        job_manager = get_job_manager()

        # Interface contract: start_job() should not accept entry_routine_id or entry_params
        job_state = job_manager.start_job(flow=flow, timeout=None)

        assert job_state is not None
        assert job_state.status == ExecutionStatus.RUNNING

        # Cleanup
        executor = job_manager.get_job(job_state.job_id)
        if executor:
            executor.stop()


class TestAllRoutinesStartIdle:
    """Test that all routines start in IDLE state."""

    def test_all_routines_initialized_as_idle(self):
        """Test: All routines are initialized as IDLE when job starts."""
        flow = Flow("test_flow")

        # Create multiple routines
        for i in range(3):
            routine = Routine()
            routine.define_slot("input")
            flow.add_routine(routine, f"routine_{i}")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # Interface contract: All routines should be in IDLE state
        for i in range(3):
            routine_state = job_state.get_routine_state(f"routine_{i}")
            assert routine_state is not None
            assert routine_state["status"] == RoutineStatus.IDLE.value

        runtime.shutdown(wait=True)

    def test_no_routine_auto_triggered(self):
        """Test: No routine is automatically triggered when job starts."""
        flow = Flow("test_flow")
        execution_count = {"count": 0}

        routine = Routine()
        routine.define_slot("trigger")

        def logic(trigger_data, policy_message, job_state):
            execution_count["count"] += 1

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # Wait a bit - routine should not execute automatically
        time.sleep(0.3)

        # Interface contract: Routine should not execute without explicit post()
        assert execution_count["count"] == 0

        # Now post to trigger it
        runtime.post("test_flow", "routine", "trigger", {"data": "test"}, job_id=job_state.job_id)
        time.sleep(0.3)

        # Should execute after post
        assert execution_count["count"] > 0

        runtime.shutdown(wait=True)

    def test_must_use_runtime_post_to_start(self):
        """Test: Must use Runtime.post() to start routine execution."""
        flow = Flow("test_flow")
        received_data = []

        routine = Routine()
        routine.define_slot("input")

        def logic(input_data, policy_message, job_state):
            if input_data:
                received_data.append(input_data[0])

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # Wait - should not receive data
        time.sleep(0.2)
        assert len(received_data) == 0

        # Interface contract: Must use Runtime.post() to send data
        runtime.post("test_flow", "routine", "input", {"value": 123}, job_id=job_state.job_id)
        time.sleep(0.3)

        # Should receive data after post
        assert len(received_data) > 0
        assert received_data[0]["value"] == 123

        runtime.shutdown(wait=True)


class TestMigrationFromEntry:
    """Test migration scenarios from entry routine pattern."""

    def test_migration_from_entry_routine_pattern(self):
        """Test: Migration scenario from old entry routine pattern."""
        # Old pattern: runtime.exec("flow", entry_routine_id="start", entry_params={"data": "value"})
        # New pattern: runtime.exec("flow") then runtime.post("flow", "start", "trigger", {"data": "value"})

        flow = Flow("migration_flow")
        received_data = []

        # Old "entry" routine
        start_routine = Routine()
        start_routine.define_slot("trigger")

        def start_logic(trigger_data, policy_message, job_state):
            if trigger_data:
                received_data.append(trigger_data[0])
            # Emit to next routine
            start_routine.emit(
                "output", runtime=job_state._current_runtime, job_state=job_state, result="processed"
            )

        start_routine.define_event("output", ["result"])
        start_routine.set_logic(start_logic)
        start_routine.set_activation_policy(immediate_policy())

        # Next routine
        next_routine = Routine()
        next_routine.define_slot("input")

        def next_logic(input_data, policy_message, job_state):
            if input_data:
                received_data.append(input_data[0])

        next_routine.set_logic(next_logic)
        next_routine.set_activation_policy(immediate_policy())

        flow.add_routine(start_routine, "start")
        flow.add_routine(next_routine, "next")
        flow.connect("start", "output", "next", "input")

        FlowRegistry.get_instance().register_by_name("migration_flow", flow)
        runtime = Runtime()

        # New pattern: exec() then post()
        job_state = runtime.exec("migration_flow")
        runtime.post("migration_flow", "start", "trigger", {"data": "value"}, job_id=job_state.job_id)

        time.sleep(0.5)

        # Interface contract: Should work with new pattern
        assert len(received_data) >= 1
        # Should receive initial data
        assert any("data" in d and d["data"] == "value" for d in received_data)
        # Should receive result from start routine
        assert any("result" in d and d["result"] == "processed" for d in received_data)

        runtime.shutdown(wait=True)
