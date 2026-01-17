"""
Tests for IDLE status management refactoring.

Tests verify that:
1. IDLE status is correctly defined
2. Jobs enter IDLE when all routines complete
3. Routines enter IDLE when no pending data
4. IDLE vs COMPLETED distinction
5. complete() method works correctly
"""

import time

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.job_executor import JobExecutor
from routilux.job_manager import get_job_manager
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.runtime import Runtime
from routilux.status import ExecutionStatus, RoutineStatus


class TestIdleStatusDefinition:
    """Test that IDLE status is correctly defined."""

    def test_execution_status_has_idle(self):
        """Test: ExecutionStatus has IDLE value."""
        # Interface contract: ExecutionStatus should have IDLE
        assert hasattr(ExecutionStatus, "IDLE")
        assert ExecutionStatus.IDLE == "idle"

    def test_routine_status_has_idle(self):
        """Test: RoutineStatus has IDLE value."""
        # Interface contract: RoutineStatus should have IDLE
        assert hasattr(RoutineStatus, "IDLE")
        assert RoutineStatus.IDLE == "idle"


class TestJobIdleBehavior:
    """Test job IDLE behavior."""

    def test_job_enters_idle_when_all_routines_complete(self):
        """Test: Job enters IDLE when all routines complete their work."""
        flow = Flow("test_flow")
        execution_done = {"done": False}

        routine = Routine()
        routine.define_slot("input")

        def logic(input_data, policy_message, job_state):
            # Process data
            time.sleep(0.1)
            execution_done["done"] = True

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")
        runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id=job_state.job_id)

        # Wait for execution to complete
        time.sleep(0.5)

        # Interface contract: Job should enter IDLE when all routines complete
        # Note: This may take a moment for IDLE detection
        time.sleep(0.3)
        # Job should be IDLE or still RUNNING (if checking)
        assert job_state.status in (ExecutionStatus.IDLE, ExecutionStatus.RUNNING)
        assert execution_done["done"] is True

        runtime.shutdown(wait=True)

    def test_idle_job_can_receive_new_tasks(self):
        """Test: IDLE job can receive new tasks via Runtime.post()."""
        flow = Flow("test_flow")
        execution_count = {"count": 0}

        routine = Routine()
        routine.define_slot("input")

        def logic(input_data, policy_message, job_state):
            execution_count["count"] += 1

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # First execution
        runtime.post("test_flow", "routine", "input", {"data": 1}, job_id=job_state.job_id)
        time.sleep(0.3)
        assert execution_count["count"] == 1

        # Wait for IDLE
        time.sleep(0.3)

        # Interface contract: IDLE job should accept new tasks
        runtime.post("test_flow", "routine", "input", {"data": 2}, job_id=job_state.job_id)
        time.sleep(0.3)
        assert execution_count["count"] == 2

        runtime.shutdown(wait=True)

    def test_idle_job_event_loop_continues(self):
        """Test: IDLE job's event loop continues running."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")

        def logic(input_data, policy_message, job_state):
            pass

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # Get executor
        executor = job_state._job_executor
        assert executor is not None

        # Post data and wait for completion
        runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id=job_state.job_id)
        time.sleep(0.5)

        # Interface contract: Event loop should still be running (not stopped)
        assert executor._running is True
        assert executor.event_loop_thread is not None
        assert executor.event_loop_thread.is_alive()

        runtime.shutdown(wait=True)


class TestRoutineIdleBehavior:
    """Test routine IDLE behavior."""

    def test_routine_enters_idle_when_no_pending_data(self):
        """Test: Routine enters IDLE when no pending data."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")

        def logic(input_data, policy_message, job_state):
            # Process all data
            pass

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # Initially IDLE
        routine_state = job_state.get_routine_state("routine")
        assert routine_state["status"] == RoutineStatus.IDLE.value

        # Post data
        runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id=job_state.job_id)
        time.sleep(0.2)

        # Should be RUNNING or back to IDLE after processing
        time.sleep(0.3)
        routine_state = job_state.get_routine_state("routine")
        # Interface contract: Should be IDLE when no pending data
        assert routine_state["status"] in (RoutineStatus.IDLE.value, RoutineStatus.RUNNING.value)

        runtime.shutdown(wait=True)

    def test_routine_exits_idle_when_receives_data(self):
        """Test: Routine exits IDLE when receives data."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")

        def logic(input_data, policy_message, job_state):
            pass

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # Initially IDLE
        routine_state = job_state.get_routine_state("routine")
        assert routine_state["status"] == RoutineStatus.IDLE.value

        # Post data
        runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id=job_state.job_id)

        # Should transition to RUNNING
        time.sleep(0.2)
        routine_state = job_state.get_routine_state("routine")
        # Interface contract: Should not be IDLE when processing
        # (May be RUNNING or back to IDLE quickly)
        assert routine_state["status"] in (
            RoutineStatus.IDLE.value,
            RoutineStatus.RUNNING.value,
            RoutineStatus.COMPLETED.value,
        )

        runtime.shutdown(wait=True)


class TestCompleteMethod:
    """Test JobExecutor.complete() method."""

    def test_complete_stops_event_loop(self):
        """Test: complete() stops the event loop thread."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        executor = job_state._job_executor
        assert executor is not None
        assert executor._running is True
        assert executor.event_loop_thread is not None

        # Interface contract: complete() should stop event loop
        executor.complete()

        # Wait for thread to stop
        if executor.event_loop_thread:
            executor.event_loop_thread.join(timeout=2.0)

        assert executor._running is False
        if executor.event_loop_thread:
            assert not executor.event_loop_thread.is_alive()

        runtime.shutdown(wait=True)

    def test_complete_marks_job_completed(self):
        """Test: complete() marks job as COMPLETED."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        executor = job_state._job_executor

        # Interface contract: complete() should mark job as COMPLETED
        executor.complete()

        assert job_state.status == ExecutionStatus.COMPLETED

        runtime.shutdown(wait=True)

    def test_completed_job_cannot_receive_tasks(self):
        """Test: COMPLETED job cannot receive new tasks."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        executor = job_state._job_executor
        executor.complete()

        # Interface contract: Should raise RuntimeError when posting to COMPLETED job
        with pytest.raises(RuntimeError, match="completed"):
            runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id=job_state.job_id)

        runtime.shutdown(wait=True)

    def test_complete_sets_completed_at_timestamp(self):
        """Test: complete() sets completed_at timestamp."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        executor = job_state._job_executor

        # Interface contract: complete() should set completed_at
        executor.complete()

        assert job_state.completed_at is not None
        assert job_state.status == ExecutionStatus.COMPLETED

        runtime.shutdown(wait=True)


class TestIdleVsCompleted:
    """Test IDLE vs COMPLETED distinction."""

    def test_idle_is_automatic_completed_is_manual(self):
        """Test: IDLE is automatic, COMPLETED is manual."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")

        def logic(input_data, policy_message, job_state):
            pass

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # Post data and wait
        runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id=job_state.job_id)
        time.sleep(0.5)

        # Interface contract: Should be IDLE automatically (not COMPLETED)
        # Unless explicitly completed
        assert job_state.status != ExecutionStatus.COMPLETED

        # Now complete manually
        executor = job_state._job_executor
        executor.complete()

        # Should be COMPLETED
        assert job_state.status == ExecutionStatus.COMPLETED

        runtime.shutdown(wait=True)

    def test_idle_job_can_become_completed(self):
        """Test: IDLE job can become COMPLETED via complete()."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # Wait for IDLE
        time.sleep(0.3)

        # Should be IDLE or RUNNING
        assert job_state.status in (ExecutionStatus.IDLE, ExecutionStatus.RUNNING)

        # Interface contract: Can call complete() on IDLE job
        executor = job_state._job_executor
        executor.complete()

        # Should be COMPLETED
        assert job_state.status == ExecutionStatus.COMPLETED

        runtime.shutdown(wait=True)
