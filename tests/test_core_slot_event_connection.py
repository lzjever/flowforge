"""Tests for Slot, Event, and Connection classes."""

import pytest
from routilux.core import Connection, Event, Slot, SlotQueueFullError


class TestSlot:
    """Test Slot class."""

    def test_slot_creation(self):
        """Test creating a slot."""
        slot = Slot(name="input", routine=None)
        
        assert slot.name == "input"
        assert slot.routine is None

    def test_slot_set_handler(self):
        """Test setting a handler function for a slot."""
        slot = Slot(name="input", routine=None)
        
        def handler(data, **kwargs):
            return {"result": data}
        
        slot.set_handler(handler)
        assert slot.handler == handler

    def test_slot_call_handler(self):
        """Test calling a slot's handler."""
        slot = Slot(name="input", routine=None)
        
        result_data = None
        
        def handler(data, **kwargs):
            nonlocal result_data
            result_data = data
            return {"processed": True}
        
        slot.set_handler(handler)
        result = slot.call({"test": "data"})
        
        assert result_data == {"test": "data"}
        assert result == {"processed": True}

    def test_slot_queue_status(self):
        """Test getting slot queue status."""
        slot = Slot(name="input", routine=None, max_queue_size=10)
        
        status = slot.get_queue_status()
        
        assert "size" in status
        assert "max_size" in status
        assert status["max_size"] == 10
        assert status["size"] == 0


class TestEvent:
    """Test Event class."""

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(name="output", routine=None)
        
        assert event.name == "output"
        assert event.routine is None

    def test_event_emit_requires_runtime(self):
        """Test that emit requires a runtime."""
        from routilux.core.flow import Flow
        from routilux.core.routine import Routine
        
        class TestRoutine(Routine):
            def setup(self):
                self.add_event("output")
        
        routine = TestRoutine()
        flow = Flow()
        flow.add_routine(routine, "test")
        
        event = routine.events["output"]
        
        # Emit should fail without runtime
        with pytest.raises((AttributeError, TypeError)):
            event.emit(None, None, data={"test": "value"})


class TestConnection:
    """Test Connection class."""

    def test_connection_creation(self):
        """Test creating a connection."""
        connection = Connection(
            source_routine_id="source",
            source_event="output",
            target_routine_id="target",
            target_slot="input"
        )
        
        assert connection.source_routine_id == "source"
        assert connection.source_event == "output"
        assert connection.target_routine_id == "target"
        assert connection.target_slot == "input"

    def test_connection_equality(self):
        """Test connection equality."""
        conn1 = Connection("source", "output", "target", "input")
        conn2 = Connection("source", "output", "target", "input")
        conn3 = Connection("source", "output", "target", "input2")
        
        assert conn1 == conn2
        assert conn1 != conn3

    def test_connection_serialization(self):
        """Test connection serialization."""
        connection = Connection("source", "output", "target", "input")
        
        data = connection.serialize()
        
        assert data["source_routine_id"] == "source"
        assert data["source_event"] == "output"
        assert data["target_routine_id"] == "target"
        assert data["target_slot"] == "input"
        
        # Test deserialization
        restored = Connection.deserialize(data)
        assert restored == connection
