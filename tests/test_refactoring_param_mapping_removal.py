"""
Tests for param_mapping removal refactoring.

Tests verify that:
1. param_mapping parameter is completely removed from Connection and Flow.connect()
2. Event data is passed directly without mapping transformation
3. Backward compatibility with old serialized data
"""

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.connection import Connection
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.runtime import Runtime
from routilux.status import ExecutionStatus


class TestConnectionWithoutParamMapping:
    """Test that Connection and Flow.connect() no longer accept param_mapping."""

    def test_connect_without_param_mapping(self):
        """Test: Flow.connect() does not accept param_mapping parameter."""
        flow = Flow()
        routine1 = Routine()
        routine2 = Routine()

        routine1.define_event("output", ["result", "status"])
        routine2.define_slot("input")

        flow.add_routine(routine1, "source")
        flow.add_routine(routine2, "target")

        # Should work without param_mapping
        connection = flow.connect("source", "output", "target", "input")
        assert connection is not None

        # Verify param_mapping is not in connection attributes
        # Interface contract: Connection should not have param_mapping attribute
        assert not hasattr(connection, "param_mapping")

    def test_connection_serialization_no_param_mapping(self):
        """Test: Connection serialization does not include param_mapping."""
        flow = Flow()
        routine1 = Routine()
        routine2 = Routine()

        routine1.define_event("output", ["data"])
        routine2.define_slot("input")

        flow.add_routine(routine1, "source")
        flow.add_routine(routine2, "target")

        connection = flow.connect("source", "output", "target", "input")
        serialized = connection.serialize()

        # Interface contract: Serialized data should not contain param_mapping
        assert "param_mapping" not in serialized

    def test_connection_deserialization_ignores_old_param_mapping(self):
        """Test: Connection deserialization ignores old param_mapping field."""
        # Create a connection
        flow = Flow()
        routine1 = Routine()
        routine2 = Routine()

        routine1.define_event("output", ["data"])
        routine2.define_slot("input")

        flow.add_routine(routine1, "source")
        flow.add_routine(routine2, "target")

        connection = flow.connect("source", "output", "target", "input")
        serialized = connection.serialize()

        # Simulate old data with param_mapping
        old_data = serialized.copy()
        old_data["param_mapping"] = {"old_key": "new_key"}

        # Should deserialize without error
        new_connection = Connection()
        new_connection.deserialize(old_data)

        # Interface contract: Should not have param_mapping attribute after deserialization
        assert not hasattr(new_connection, "param_mapping")


class TestEventDataDirectPassing:
    """Test that event data is passed directly without mapping transformation."""

    def test_event_data_passed_directly(self):
        """Test: Event data is passed directly to target slot without mapping."""
        flow = Flow("test_flow")
        received_data = {}

        # Source routine
        source = Routine()
        source.define_slot("trigger")  # Add trigger slot for posting data
        source.define_event("output", ["result", "status", "metadata"])

        def source_logic(trigger_data, policy_message, job_state):
            # Emit with original field names
            # Get runtime from job_state (set by JobExecutor)
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                source.emit(
                    "output",
                    runtime=runtime,
                    job_state=job_state,
                result="success",
                status="ok",
                metadata={"key": "value"},
            )

        source.set_logic(source_logic)
        source.set_activation_policy(immediate_policy())

        # Target routine
        target = Routine()
        target.define_slot("input")

        def target_logic(input_data, policy_message, job_state):
            # Should receive data with original field names
            received_data["data"] = input_data[0] if input_data else None

        target.set_logic(target_logic)
        target.set_activation_policy(immediate_policy())

        flow.add_routine(source, "source")
        flow.add_routine(target, "target")
        flow.connect("source", "output", "target", "input")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        # Create job and post data to source
        job_state = runtime.exec("test_flow")
        runtime.post("test_flow", "source", "trigger", {"start": True}, job_id=job_state.job_id)

        # Wait for execution
        import time

        time.sleep(0.5)

        # Interface contract: Data should be passed with original field names
        assert "data" in received_data
        data = received_data["data"]
        assert data is not None
        assert "result" in data
        assert "status" in data
        assert "metadata" in data
        assert data["result"] == "success"
        assert data["status"] == "ok"
        assert data["metadata"] == {"key": "value"}

        runtime.shutdown(wait=True)

    def test_event_data_structure_preserved(self):
        """Test: Event data structure is completely preserved."""
        flow = Flow("test_flow")
        received_data = {}

        source = Routine()
        source.define_slot("trigger")  # Add trigger slot for posting data
        source.define_event("output", ["data"])

        def source_logic(trigger_data, policy_message, job_state):
            # Emit complex nested structure
            complex_data = {
                "nested": {"level1": {"level2": "value"}},
                "list": [1, 2, 3],
                "mixed": {"key": [{"item": "value"}]},
            }
            # Get runtime from job_state (set by JobExecutor)
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                source.emit(
                    "output", runtime=runtime, job_state=job_state, data=complex_data
                )

        source.set_logic(source_logic)
        source.set_activation_policy(immediate_policy())

        target = Routine()
        target.define_slot("input")

        def target_logic(input_data, policy_message, job_state):
            # Event data is passed as {"data": complex_data} when event is defined with ["data"]
            # So input_data[0] is {"data": complex_data}, and we need to extract the actual data
            if input_data and len(input_data) > 0:
                event_data_dict = input_data[0]
                # Extract the actual data from the event data dict
                received_data["data"] = event_data_dict.get("data") if isinstance(event_data_dict, dict) else event_data_dict
            else:
                received_data["data"] = None

        target.set_logic(target_logic)
        target.set_activation_policy(immediate_policy())

        flow.add_routine(source, "source")
        flow.add_routine(target, "target")
        flow.connect("source", "output", "target", "input")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")
        runtime.post("test_flow", "source", "trigger", {"start": True}, job_id=job_state.job_id)

        import time

        time.sleep(0.5)

        # Interface contract: Complex nested structure should be preserved exactly
        assert "data" in received_data
        data = received_data["data"]
        assert data is not None
        assert data["nested"]["level1"]["level2"] == "value"
        assert data["list"] == [1, 2, 3]
        assert data["mixed"]["key"][0]["item"] == "value"

        runtime.shutdown(wait=True)

    def test_nested_data_passed_correctly(self):
        """Test: Nested data structures are passed correctly without transformation."""
        flow = Flow("test_flow")
        received_data = {}

        source = Routine()
        source.define_slot("trigger")  # Add trigger slot for posting data
        source.define_event("output", ["payload"])

        def source_logic(trigger_data, policy_message, job_state):
            nested = {
                "user": {"id": 123, "name": "test"},
                "items": [{"id": 1, "qty": 2}, {"id": 2, "qty": 3}],
            }
            # Get runtime from job_state (set by JobExecutor)
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                source.emit(
                    "output", runtime=runtime, job_state=job_state, payload=nested
                )

        source.set_logic(source_logic)
        source.set_activation_policy(immediate_policy())

        target = Routine()
        target.define_slot("input")

        def target_logic(input_data, policy_message, job_state):
            # Event data is passed as {"payload": nested} when event is defined with ["payload"]
            # So input_data[0] is {"payload": nested}, and we need to extract the actual data
            if input_data and len(input_data) > 0:
                event_data_dict = input_data[0]
                # Extract the actual data from the event data dict
                # Event was defined with ["payload"], so data is in "payload" key
                received_data["data"] = event_data_dict.get("payload") if isinstance(event_data_dict, dict) else event_data_dict
            else:
                received_data["data"] = None

        target.set_logic(target_logic)
        target.set_activation_policy(immediate_policy())

        flow.add_routine(source, "source")
        flow.add_routine(target, "target")
        flow.connect("source", "output", "target", "input")

        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        runtime = Runtime()

        job_state = runtime.exec("test_flow")
        runtime.post("test_flow", "source", "trigger", {"start": True}, job_id=job_state.job_id)

        import time

        time.sleep(0.5)

        # Interface contract: Nested structures should be identical
        assert "data" in received_data
        payload = received_data["data"]
        assert payload is not None
        assert payload["user"]["id"] == 123
        assert payload["user"]["name"] == "test"
        assert len(payload["items"]) == 2
        assert payload["items"][0]["id"] == 1
        assert payload["items"][0]["qty"] == 2

        runtime.shutdown(wait=True)


class TestBackwardCompatibility:
    """Test backward compatibility with old serialized data containing param_mapping."""

    def test_old_serialized_data_with_param_mapping(self):
        """Test: Old serialized data with param_mapping can be deserialized."""
        # Create connection and serialize
        flow = Flow()
        routine1 = Routine()
        routine2 = Routine()

        routine1.define_event("output", ["data"])
        routine2.define_slot("input")

        flow.add_routine(routine1, "source")
        flow.add_routine(routine2, "target")

        connection = flow.connect("source", "output", "target", "input")
        serialized = connection.serialize()

        # Add old param_mapping field (simulating old data)
        old_serialized = serialized.copy()
        old_serialized["param_mapping"] = {"old_field": "new_field"}

        # Interface contract: Should deserialize without error
        new_connection = Connection()
        new_connection.deserialize(old_serialized)

        # Note: Connection.deserialize() only saves reference information (_source_event_name, etc.)
        # Actual source_event and target_slot are restored by Flow.deserialize() which has
        # access to routines. For this test, we just verify deserialization doesn't error
        # and reference information is saved correctly.
        assert hasattr(new_connection, "_source_event_name") or new_connection.source_event is not None
        assert hasattr(new_connection, "_target_slot_name") or new_connection.target_slot is not None

    def test_migration_from_param_mapping(self):
        """Test: Migration scenario from code using param_mapping."""
        # This test verifies that code that previously used param_mapping
        # can be migrated to direct data passing

        flow = Flow("migration_test")
        received_data = {}

        # Old code would have used param_mapping to rename fields
        # New code should pass data directly with correct field names

        source = Routine()
        source.define_slot("trigger")  # Add trigger slot for posting data
        source.define_event("output", ["user_id", "user_name"])

        def source_logic(trigger_data, policy_message, job_state):
            # Emit with field names that target expects
            # Get runtime from job_state (set by JobExecutor)
            runtime = getattr(job_state, "_current_runtime", None)
            if runtime:
                source.emit(
                    "output",
                    runtime=runtime,
                    job_state=job_state,
                user_id=123,
                user_name="test_user",
            )

        source.set_logic(source_logic)
        source.set_activation_policy(immediate_policy())

        target = Routine()
        target.define_slot("input")

        def target_logic(input_data, policy_message, job_state):
            if input_data:
                received_data.update(input_data[0])

        target.set_logic(target_logic)
        target.set_activation_policy(immediate_policy())

        flow.add_routine(source, "source")
        flow.add_routine(target, "target")
        # No param_mapping needed - field names match
        flow.connect("source", "output", "target", "input")

        FlowRegistry.get_instance().register_by_name("migration_test", flow)
        runtime = Runtime()

        job_state = runtime.exec("migration_test")
        runtime.post("migration_test", "source", "trigger", {"start": True}, job_id=job_state.job_id)

        import time

        time.sleep(0.5)

        # Interface contract: Data should arrive with correct field names
        assert "user_id" in received_data
        assert "user_name" in received_data
        assert received_data["user_id"] == 123
        assert received_data["user_name"] == "test_user"

        runtime.shutdown(wait=True)
