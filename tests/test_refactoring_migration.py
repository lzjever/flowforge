"""
Migration scenario tests for refactored API.

Tests verify migration scenarios from old API to new API.
"""

import time

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.runtime import Runtime
from routilux.status import ExecutionStatus


class TestMigrationScenarios:
    """Test migration scenarios from old API."""

    def test_migrate_from_param_mapping(self):
        """Test: Migration from code using param_mapping."""
        # Old pattern:
        # flow.connect(source, "output", target, "input", param_mapping={"result": "data"})
        #
        # New pattern:
        # flow.connect(source, "output", target, "input")
        # Source emits with field names that target expects

        flow = Flow("migration_flow")
        received_data = []

        source = Routine()
        source.define_slot("trigger")  # Add trigger slot for posting data
        source.define_event("output", ["result", "status"])

        def source_logic(trigger_data, policy_message, job_state):
            # Emit with field names that target expects (no mapping needed)
            # Get runtime from job_state (set by JobExecutor)
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                source.emit(
                    "output",
                    runtime=runtime,
                    job_state=job_state,
                    result="success",
                    status="ok",
                )

        source.set_logic(source_logic)
        source.set_activation_policy(immediate_policy())

        target = Routine()
        target.define_slot("input")

        def target_logic(input_data, policy_message, job_state):
            if input_data:
                received_data.append(input_data[0])

        target.set_logic(target_logic)
        target.set_activation_policy(immediate_policy())

        flow.add_routine(source, "source")
        flow.add_routine(target, "target")

        # New pattern: No param_mapping
        flow.connect("source", "output", "target", "input")

        FlowRegistry.get_instance().register_by_name("migration_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("migration_flow")
        runtime.post("migration_flow", "source", "trigger", {"start": True}, job_id=job_state.job_id)

        time.sleep(0.5)

        # Interface contract: Data should arrive with correct field names
        assert len(received_data) > 0
        data = received_data[0]
        assert "result" in data
        assert "status" in data
        assert data["result"] == "success"
        assert data["status"] == "ok"

        runtime.shutdown(wait=True)

    def test_migrate_from_execution_strategy(self):
        """Test: Migration from code using execution_strategy."""
        # Old pattern:
        # flow = Flow(flow_id="test", execution_strategy="concurrent", max_workers=10)
        #
        # New pattern:
        # flow = Flow(flow_id="test")
        # Execution is managed by Runtime

        # Interface contract: Flow should not accept execution_strategy
        with pytest.raises(TypeError):
            Flow(flow_id="test", execution_strategy="concurrent")

        # New pattern works
        flow = Flow(flow_id="test")
        assert flow.flow_id == "test"

        # Execution is handled by Runtime
        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        FlowRegistry.get_instance().register_by_name("test", flow)
        runtime = Runtime()

        job_state = runtime.exec("test")

        # Interface contract: Should work without execution_strategy
        assert job_state is not None
        assert job_state.status == ExecutionStatus.RUNNING

        runtime.shutdown(wait=True)

    def test_migrate_from_entry_routine(self):
        """Test: Migration from entry routine pattern."""
        # Old pattern:
        # job_state = runtime.exec("flow", entry_routine_id="start", entry_params={"data": "value"})
        #
        # New pattern:
        # job_state = runtime.exec("flow")
        # runtime.post("flow", "start", "trigger", {"data": "value"}, job_id=job_state.job_id)

        flow = Flow("migration_flow")
        received_data = []

        start_routine = Routine()
        start_routine.define_slot("trigger")

        def start_logic(trigger_data, policy_message, job_state):
            if trigger_data:
                received_data.append(trigger_data[0])

        start_routine.set_logic(start_logic)
        start_routine.set_activation_policy(immediate_policy())
        flow.add_routine(start_routine, "start")

        FlowRegistry.get_instance().register_by_name("migration_flow", flow)
        runtime = Runtime()

        # New pattern: exec() then post()
        job_state = runtime.exec("migration_flow")
        runtime.post("migration_flow", "start", "trigger", {"data": "value"}, job_id=job_state.job_id)

        time.sleep(0.5)

        # Interface contract: Should work with new pattern
        assert len(received_data) > 0
        assert received_data[0]["data"] == "value"

        runtime.shutdown(wait=True)

    def test_migrate_complete_workflow(self):
        """Test: Complete workflow migration example."""
        # This test demonstrates a complete migration from old API to new API

        # Old code would have been:
        # flow = Flow("workflow", execution_strategy="concurrent", max_workers=5)
        # flow.connect(r1, "out", r2, "in", param_mapping={"result": "data"})
        # job = runtime.exec("workflow", entry_routine_id="start", entry_params={"input": "data"})

        # New code:
        flow = Flow("workflow")  # No execution_strategy, max_workers

        # Routines
        start = Routine()
        start.define_slot("trigger")
        start.define_event("output", ["data"])  # Emit with correct field name

        process = Routine()
        process.define_slot("input")

        received = []

        def start_logic(trigger_data, policy_message, job_state):
            if trigger_data:
                start.emit(
                    "output",
                    runtime=job_state._current_runtime,
                    job_state=job_state,
                    data=trigger_data[0].get("input", ""),
                )

        def process_logic(input_data, policy_message, job_state):
            if input_data:
                received.append(input_data[0])

        start.set_logic(start_logic)
        start.set_activation_policy(immediate_policy())
        process.set_logic(process_logic)
        process.set_activation_policy(immediate_policy())

        flow.add_routine(start, "start")
        flow.add_routine(process, "process")

        # No param_mapping needed
        flow.connect("start", "output", "process", "input")

        FlowRegistry.get_instance().register_by_name("workflow", flow)
        runtime = Runtime()

        # No entry_routine_id, entry_params
        job_state = runtime.exec("workflow")

        # Use post() instead
        runtime.post("workflow", "start", "trigger", {"input": "data"}, job_id=job_state.job_id)

        time.sleep(0.5)

        # Interface contract: Should work end-to-end
        assert len(received) > 0
        assert received[0]["data"] == "data"

        runtime.shutdown(wait=True)
