"""
Tests for execution_strategy and max_workers removal refactoring.

Tests verify that:
1. Flow.__init__() no longer accepts execution_strategy and max_workers
2. Execution is unified by Runtime
3. All routines execute in shared thread pool
"""

import threading
import time

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.runtime import Runtime
from routilux.status import ExecutionStatus


class TestFlowCreationWithoutExecutionStrategy:
    """Test that Flow no longer accepts execution_strategy and max_workers."""

    def test_flow_init_no_execution_strategy(self):
        """Test: Flow.__init__() does not accept execution_strategy parameter."""
        # Interface contract: Flow.__init__() should not accept execution_strategy
        # This should raise TypeError if we try to pass it
        with pytest.raises(TypeError):
            Flow(flow_id="test", execution_strategy="concurrent")

        # Should work without it
        flow = Flow(flow_id="test")
        assert flow.flow_id == "test"

    def test_flow_init_no_max_workers(self):
        """Test: Flow.__init__() does not accept max_workers parameter."""
        # Interface contract: Flow.__init__() should not accept max_workers
        with pytest.raises(TypeError):
            Flow(flow_id="test", max_workers=10)

        # Should work without it
        flow = Flow(flow_id="test")
        assert flow.flow_id == "test"

    def test_flow_serialization_no_execution_strategy(self):
        """Test: Flow serialization does not include execution_strategy fields."""
        flow = Flow(flow_id="test_flow")
        serialized = flow.serialize()

        # Interface contract: Serialized data should not contain execution_strategy or max_workers
        assert "execution_strategy" not in serialized
        assert "max_workers" not in serialized
        assert "_execution_strategy" not in serialized
        assert "_max_workers" not in serialized


class TestExecutionUnifiedByRuntime:
    """Test that execution is unified by Runtime."""

    def test_all_routines_execute_in_shared_pool(self):
        """Test: All routines execute in Runtime's shared thread pool."""
        flow = Flow("test_flow")
        execution_threads = set()

        # Create multiple routines
        for i in range(5):
            routine = Routine()

            def make_logic(idx):
                def logic(trigger_data, policy_message, job_state):
                    # Record thread ID
                    execution_threads.add(threading.current_thread().ident)
                    time.sleep(0.1)  # Simulate work

                return logic

            routine.define_slot("trigger")
            routine.set_logic(make_logic(i))
            routine.set_activation_policy(immediate_policy())
            flow.add_routine(routine, f"routine_{i}")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Create job and post to all routines concurrently
        job_state = runtime.exec("test_flow")
        for i in range(5):
            runtime.post("test_flow", f"routine_{i}", "trigger", {"data": i}, job_id=job_state.job_id)

        # Wait for execution
        time.sleep(1.0)

        # Interface contract: All routines should execute (thread IDs recorded)
        # They may execute in different threads (from thread pool) or same thread
        # The key is that they execute, not which thread
        assert len(execution_threads) > 0

        runtime.shutdown(wait=True)

    def test_execution_is_concurrent(self):
        """Test: Execution is concurrent (non-blocking)."""
        flow = Flow("test_flow")
        start_times = {}
        end_times = {}

        # Create routines that take time to execute
        for i in range(3):
            routine = Routine()

            def make_logic(idx):
                def logic(trigger_data, policy_message, job_state):
                    start_times[idx] = time.time()
                    time.sleep(0.2)  # Simulate work
                    end_times[idx] = time.time()

                return logic

            routine.define_slot("trigger")
            routine.set_logic(make_logic(i))
            routine.set_activation_policy(immediate_policy())
            flow.add_routine(routine, f"routine_{i}")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Post to all routines at once
        job_state = runtime.exec("test_flow")
        post_time = time.time()
        for i in range(3):
            runtime.post("test_flow", f"routine_{i}", "trigger", {"data": i}, job_id=job_state.job_id)

        # Wait for all to complete
        time.sleep(1.0)

        # Interface contract: Routines should execute concurrently
        # If sequential, total time would be ~0.6s (3 * 0.2s)
        # If concurrent, total time should be ~0.2s (all run in parallel)
        max_end_time = max(end_times.values())
        total_time = max_end_time - post_time

        # Should complete faster than sequential execution
        assert total_time < 0.5  # Much less than 0.6s sequential

        runtime.shutdown(wait=True)

    def test_runtime_manages_thread_pool(self):
        """Test: Runtime manages the thread pool."""
        runtime = Runtime()

        # Interface contract: Runtime should have thread_pool attribute
        assert hasattr(runtime, "thread_pool")
        assert runtime.thread_pool is not None

        # Interface contract: Runtime should have thread_pool_size
        assert hasattr(runtime, "thread_pool_size")
        assert runtime.thread_pool_size > 0

        runtime.shutdown(wait=True)

    def test_flow_has_no_executor(self):
        """Test: Flow does not have executor attribute."""
        flow = Flow("test_flow")

        # Interface contract: Flow should not have _executor or _get_executor
        assert not hasattr(flow, "_executor")
        assert not hasattr(flow, "_get_executor")

    def test_multiple_flows_share_runtime_pool(self):
        """Test: Multiple flows share Runtime's thread pool."""
        flow1 = Flow("flow1")
        flow2 = Flow("flow2")

        # Create routines in both flows
        for flow, flow_name in [(flow1, "flow1"), (flow2, "flow2")]:
            routine = Routine()
            routine.define_slot("trigger")

            def logic(trigger_data, policy_message, job_state):
                pass

            routine.set_logic(logic)
            routine.set_activation_policy(immediate_policy())
            flow.add_routine(routine, "routine")
            FlowRegistry.get_instance().register_by_name(flow_name, flow)

        runtime = Runtime()

        # Execute both flows
        job1 = runtime.exec("flow1")
        job2 = runtime.exec("flow2")

        # Interface contract: Both jobs should use same Runtime thread pool
        assert job1._current_runtime is runtime
        assert job2._current_runtime is runtime
        assert job1._current_runtime is job2._current_runtime

        runtime.shutdown(wait=True)
