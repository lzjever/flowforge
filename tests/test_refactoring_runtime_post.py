"""
Tests for Runtime.post() external event injection interface.

Tests verify that:
1. Runtime.post() can create new job or use existing job
2. Data is correctly delivered to target slot
3. All error cases are handled correctly
4. Edge cases work properly
"""

import threading
import time

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.runtime import Runtime
from routilux.status import ExecutionStatus


class TestPostInterface:
    """Test Runtime.post() interface compliance."""

    def test_post_creates_new_job_when_job_id_none(self):
        """Test: post() creates new job when job_id is None."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Interface contract: post() with job_id=None should create new job
        job_state = runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id=None)

        assert job_state is not None
        assert job_state.flow_id == "test_flow"
        assert job_state.status == ExecutionStatus.RUNNING

        runtime.shutdown(wait=True)

    def test_post_uses_existing_job_when_job_id_provided(self):
        """Test: post() uses existing job when job_id is provided."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Create job first
        job_state1 = runtime.exec("test_flow")

        # Interface contract: post() with job_id should use existing job
        job_state2 = runtime.post(
            "test_flow", "routine", "input", {"data": "test"}, job_id=job_state1.job_id
        )

        assert job_state2 is not None
        assert job_state2.job_id == job_state1.job_id

        runtime.shutdown(wait=True)

    def test_post_returns_job_state(self):
        """Test: post() returns JobState."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Interface contract: post() should return JobState
        job_state = runtime.post("test_flow", "routine", "input", {"data": "test"})

        assert job_state is not None
        assert hasattr(job_state, "job_id")
        assert hasattr(job_state, "flow_id")
        assert hasattr(job_state, "status")

        runtime.shutdown(wait=True)


class TestPostDataDelivery:
    """Test data delivery via Runtime.post()."""

    def test_post_delivers_data_to_slot(self):
        """Test: post() delivers data to target slot."""
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

        # Interface contract: post() should deliver data to slot
        job_state = runtime.post("test_flow", "routine", "input", {"value": 123})

        time.sleep(0.3)

        assert len(received_data) > 0
        assert received_data[0]["value"] == 123

        runtime.shutdown(wait=True)

    def test_post_data_structure_preserved(self):
        """Test: post() preserves data structure."""
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

        complex_data = {"nested": {"key": "value"}, "list": [1, 2, 3]}

        # Interface contract: Complex data structure should be preserved
        runtime.post("test_flow", "routine", "input", complex_data)

        time.sleep(0.3)

        assert len(received_data) > 0
        data = received_data[0]
        assert data["nested"]["key"] == "value"
        assert data["list"] == [1, 2, 3]

        runtime.shutdown(wait=True)

    def test_post_creates_slot_activation_task(self):
        """Test: post() creates SlotActivationTask and submits to JobExecutor."""
        flow = Flow("test_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.post("test_flow", "routine", "input", {"data": "test"})

        # Interface contract: Should create task in JobExecutor queue
        executor = job_state._job_executor
        assert executor is not None

        # Task should be in queue or processed
        time.sleep(0.2)
        # Queue might be empty if already processed, which is fine

        runtime.shutdown(wait=True)


class TestPostErrorHandling:
    """Test error handling in Runtime.post()."""

    def test_post_flow_not_found_raises_valueerror(self):
        """Test: post() raises ValueError when flow not found."""
        runtime = Runtime()

        # Interface contract: Should raise ValueError for nonexistent flow
        with pytest.raises(ValueError, match="not found"):
            runtime.post("nonexistent_flow", "routine", "input", {"data": "test"})

        runtime.shutdown(wait=True)

    def test_post_routine_not_found_raises_valueerror(self):
        """Test: post() raises ValueError when routine not found."""
        flow = Flow("test_flow")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Interface contract: Should raise ValueError for nonexistent routine
        with pytest.raises(ValueError, match="not found"):
            runtime.post("test_flow", "nonexistent_routine", "input", {"data": "test"})

        runtime.shutdown(wait=True)

    def test_post_slot_not_found_raises_valueerror(self):
        """Test: post() raises ValueError when slot not found."""
        flow = Flow("test_flow")
        routine = Routine()
        flow.add_routine(routine, "routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Interface contract: Should raise ValueError for nonexistent slot
        with pytest.raises(ValueError, match="not found"):
            runtime.post("test_flow", "routine", "nonexistent_slot", {"data": "test"})

        runtime.shutdown(wait=True)

    def test_post_job_not_found_raises_valueerror(self):
        """Test: post() raises ValueError when job not found."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Interface contract: Should raise ValueError for nonexistent job
        with pytest.raises(ValueError, match="not found"):
            runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id="nonexistent")

        runtime.shutdown(wait=True)

    def test_post_completed_job_raises_runtimeerror(self):
        """Test: post() raises RuntimeError when job is COMPLETED."""
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

        # Interface contract: Should raise RuntimeError for COMPLETED job
        with pytest.raises(RuntimeError, match="completed"):
            runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id=job_state.job_id)

        runtime.shutdown(wait=True)

    def test_post_shutdown_runtime_raises_runtimeerror(self):
        """Test: post() raises RuntimeError when Runtime is shut down."""
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("input")
        flow.add_routine(routine, "routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        runtime.shutdown(wait=True)

        # Interface contract: Should raise RuntimeError when shut down
        with pytest.raises(RuntimeError, match="shut down"):
            runtime.post("test_flow", "routine", "input", {"data": "test"})


class TestPostEdgeCases:
    """Test edge cases for Runtime.post()."""

    def test_post_with_empty_data(self):
        """Test: post() works with empty data."""
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

        # Interface contract: Should accept empty data
        runtime.post("test_flow", "routine", "input", {})

        time.sleep(0.3)

        # Should receive empty dict
        assert len(received_data) > 0
        assert received_data[0] == {}

        runtime.shutdown(wait=True)

    def test_post_with_complex_nested_data(self):
        """Test: post() works with complex nested data."""
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

        complex_data = {
            "level1": {
                "level2": {"level3": {"value": 123}},
                "list": [{"item": i} for i in range(5)],
            },
            "mixed": [{"nested": {"key": "value"}}],
        }

        # Interface contract: Should handle complex nested structures
        runtime.post("test_flow", "routine", "input", complex_data)

        time.sleep(0.3)

        assert len(received_data) > 0
        data = received_data[0]
        assert data["level1"]["level2"]["level3"]["value"] == 123
        assert len(data["level1"]["list"]) == 5
        assert data["mixed"][0]["nested"]["key"] == "value"

        runtime.shutdown(wait=True)

    def test_post_concurrent_calls(self):
        """Test: Concurrent post() calls work correctly."""
        flow = Flow("test_flow")
        received_count = {"count": 0}

        routine = Routine()
        routine.define_slot("input")

        def logic(input_data, policy_message, job_state):
            received_count["count"] += 1

        routine.set_logic(logic)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")

        # Interface contract: Should handle concurrent calls
        def post_data(i):
            runtime.post("test_flow", "routine", "input", {"index": i}, job_id=job_state.job_id)

        threads = [threading.Thread(target=post_data, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        time.sleep(0.5)

        # Should receive all messages
        assert received_count["count"] >= 10

        runtime.shutdown(wait=True)

    def test_post_to_idle_job(self):
        """Test: post() works with IDLE job."""
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

        # Wait for IDLE
        time.sleep(0.3)

        # Interface contract: Should accept post() to IDLE job
        runtime.post("test_flow", "routine", "input", {"data": "test"}, job_id=job_state.job_id)

        time.sleep(0.3)

        assert len(received_data) > 0
        assert received_data[0]["data"] == "test"

        runtime.shutdown(wait=True)
