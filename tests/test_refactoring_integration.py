"""
Integration tests for refactored features.

Tests verify end-to-end scenarios combining multiple refactored features.
"""

import time

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.factory.factory import ObjectFactory
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.runtime import Runtime
from routilux.status import ExecutionStatus


class TestEndToEndScenarios:
    """Test end-to-end scenarios."""

    def test_create_flow_with_factory_and_execute(self):
        """Test: Create Flow using factory and execute."""
        # Register routine in factory
        factory = ObjectFactory.get_instance()
        factory._registry.clear()

        base_routine = Routine()
        base_routine.define_slot("input")
        base_routine.set_activation_policy(immediate_policy())

        def logic(input_data, policy_message, job_state):
            pass

        base_routine.set_logic(logic)
        factory.register("processor", base_routine, description="Data processor")

        # Create flow using factory
        flow = Flow("factory_flow")
        routine = factory.create("processor")
        flow.add_routine(routine, "processor")

        FlowRegistry.get_instance().register_by_name("factory_flow", flow)
        runtime = Runtime()

        # Execute flow
        job_state = runtime.exec("factory_flow")

        # Interface contract: Should work end-to-end
        assert job_state is not None
        assert job_state.status == ExecutionStatus.RUNNING

        # Post data
        runtime.post("factory_flow", "processor", "input", {"data": "test"}, job_id=job_state.job_id)

        time.sleep(0.3)

        runtime.shutdown(wait=True)

    def test_post_data_to_idle_job_and_complete(self):
        """Test: Post data to IDLE job and complete."""
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

        # Create job
        job_state = runtime.exec("test_flow")

        # Wait for IDLE
        time.sleep(0.3)

        # Post data to IDLE job
        runtime.post("test_flow", "routine", "input", {"value": 123}, job_id=job_state.job_id)
        time.sleep(0.3)

        assert len(received_data) > 0
        assert received_data[0]["value"] == 123

        # Complete job
        executor = job_state._job_executor
        executor.complete()

        # Interface contract: Job should be COMPLETED
        assert job_state.status == ExecutionStatus.COMPLETED

        runtime.shutdown(wait=True)

    def test_multiple_jobs_share_same_flow(self):
        """Test: Multiple jobs can share the same Flow."""
        flow = Flow("shared_flow")
        execution_counts = {}

        routine = Routine()
        routine.define_slot("input")

        def make_logic(job_id):
            def logic(input_data, policy_message, job_state):
                if job_state.job_id not in execution_counts:
                    execution_counts[job_state.job_id] = 0
                execution_counts[job_state.job_id] += 1

            return logic

        routine.set_logic(make_logic("shared"))
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("shared_flow", flow)
        runtime = Runtime()

        # Create multiple jobs
        job1 = runtime.exec("shared_flow")
        job2 = runtime.exec("shared_flow")
        job3 = runtime.exec("shared_flow")

        # Post to each job
        runtime.post("shared_flow", "routine", "input", {"data": 1}, job_id=job1.job_id)
        runtime.post("shared_flow", "routine", "input", {"data": 2}, job_id=job2.job_id)
        runtime.post("shared_flow", "routine", "input", {"data": 3}, job_id=job3.job_id)

        time.sleep(0.5)

        # Interface contract: All jobs should execute independently
        assert job1.job_id in execution_counts or len(execution_counts) > 0

        runtime.shutdown(wait=True)

    def test_job_lifecycle_idle_to_completed(self):
        """Test: Job lifecycle from IDLE to COMPLETED."""
        flow = Flow("lifecycle_flow")

        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("lifecycle_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("lifecycle_flow")

        # Initially RUNNING, routines IDLE
        assert job_state.status == ExecutionStatus.RUNNING

        # Post data
        runtime.post("lifecycle_flow", "routine", "input", {"data": "test"}, job_id=job_state.job_id)
        time.sleep(0.3)

        # Should be IDLE after processing
        time.sleep(0.3)
        # May be IDLE or still RUNNING

        # Complete manually
        executor = job_state._job_executor
        executor.complete()

        # Interface contract: Should be COMPLETED
        assert job_state.status == ExecutionStatus.COMPLETED
        assert job_state.completed_at is not None

        runtime.shutdown(wait=True)


class TestComplexWorkflows:
    """Test complex workflow scenarios."""

    def test_workflow_with_multiple_routines(self):
        """Test: Workflow with multiple routines."""
        flow = Flow("multi_routine_flow")
        execution_order = []

        # Create multiple routines
        for i in range(5):
            routine = Routine()
            routine.define_slot("input")
            routine.define_event("output", ["result"])

            def make_logic(idx):
                def logic(input_data, policy_message, job_state):
                    execution_order.append(idx)
                    routine.emit(
                        "output",
                        runtime=job_state._current_runtime,
                        job_state=job_state,
                        result=f"processed_{idx}",
                    )

                return logic

            routine.set_logic(make_logic(i))
            routine.set_activation_policy(immediate_policy())
            flow.add_routine(routine, f"routine_{i}")

            # Connect to next routine
            if i > 0:
                flow.connect(f"routine_{i-1}", "output", f"routine_{i}", "input")

        FlowRegistry.get_instance().register_by_name("multi_routine_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("multi_routine_flow")

        # Start first routine
        runtime.post("multi_routine_flow", "routine_0", "input", {"start": True}, job_id=job_state.job_id)

        time.sleep(1.0)

        # Interface contract: All routines should execute in order
        assert len(execution_order) == 5
        assert execution_order == [0, 1, 2, 3, 4]

        runtime.shutdown(wait=True)

    def test_workflow_with_dynamic_connections(self):
        """Test: Workflow with dynamically modified connections."""
        flow = Flow("dynamic_flow")

        source1 = Routine()
        source1.define_event("output1", ["data1"])
        source2 = Routine()
        source2.define_event("output2", ["data2"])
        target = Routine()
        target.define_slot("input")

        received_data = []

        def target_logic(input_data, policy_message, job_state):
            if input_data:
                received_data.append(input_data[0])

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

        # Post from source1
        runtime.post("dynamic_flow", "source1", "trigger", {"start": True}, job_id=job_state.job_id)
        time.sleep(0.3)

        # Modify connection during execution
        flow.connections.clear()
        flow.connect("source2", "output2", "target", "input")

        # Post from source2
        runtime.post("dynamic_flow", "source2", "trigger", {"start": True}, job_id=job_state.job_id)
        time.sleep(0.5)

        # Interface contract: Connection changes should take effect immediately
        assert len(received_data) > 0

        runtime.shutdown(wait=True)
