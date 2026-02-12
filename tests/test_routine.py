"""
Routine tests for current API.

Tests for Routine class functionality using add_slot/add_event methods.
"""

import pytest

from routilux import Routine


class TestRoutineBasic:
    """Routine basic functionality tests."""

    def test_create_routine(self):
        """Test creating a Routine object."""
        routine = Routine()
        assert routine._id is not None
        assert isinstance(routine._config, dict)
        assert len(routine._config) == 0

    def test_add_slot(self):
        """Test adding a slot."""
        routine = Routine()

        slot = routine.add_slot("input")
        assert slot.name == "input"
        assert slot.routine == routine
        assert "input" in routine._slots

    def test_add_event(self):
        """Test adding an event."""
        routine = Routine()

        event = routine.add_event("output", ["result", "status"])
        assert event.name == "output"
        assert event.routine == routine
        assert event.output_params == ["result", "status"]
        assert "output" in routine._events

    def test_define_slot_alias(self):
        """Test that define_slot works as alias for add_slot."""
        routine = Routine()

        slot = routine.define_slot("input")
        assert slot.name == "input"
        assert "input" in routine._slots

    def test_define_event_alias(self):
        """Test that define_event works as alias for add_event."""
        routine = Routine()

        event = routine.define_event("output", ["data"])
        assert event.name == "output"
        assert "output" in routine._events

    def test_config_method(self):
        """Test config() method."""
        routine = Routine()

        # Initial state is empty
        config = routine.config()
        assert isinstance(config, dict)
        assert len(config) == 0

        # Update config
        routine.set_config(count=1, result="success")

        # Verify config() returns a copy
        config = routine.config()
        assert config["count"] == 1
        assert config["result"] == "success"

        # Modifying returned dict should not affect internal state
        config["new_key"] = "new_value"
        assert "new_key" not in routine._config


class TestRoutineEdgeCases:
    """Routine edge case tests."""

    def test_empty_routine(self):
        """Test empty routine works."""
        routine = Routine()

        # Routine without slots and events should work
        assert len(routine._slots) == 0
        assert len(routine._events) == 0

    def test_duplicate_slot_name(self):
        """Test duplicate slot name raises error."""
        routine = Routine()

        routine.add_slot("input")

        # Duplicate slot name should raise error
        with pytest.raises(ValueError):
            routine.add_slot("input")

    def test_duplicate_event_name(self):
        """Test duplicate event name raises error."""
        routine = Routine()

        routine.add_event("output")

        # Duplicate event name should raise error
        with pytest.raises(ValueError):
            routine.add_event("output")

    def test_get_event(self):
        """Test get_event method."""
        routine = Routine()

        event = routine.add_event("output", ["data"])
        assert routine.get_event("output") == event
        assert routine.get_event("nonexistent") is None

    def test_get_slot(self):
        """Test get_slot method."""
        routine = Routine()

        slot = routine.add_slot("input")
        assert routine.get_slot("input") == slot
        assert routine.get_slot("nonexistent") is None


class TestRoutineIntegration:
    """Routine integration tests."""

    def test_routine_lifecycle(self):
        """Test Routine complete lifecycle."""
        routine = Routine()

        # 1. Add slots and events
        routine.add_slot("input")
        routine.add_event("output", ["result"])

        # 2. Update config
        routine.set_config(initialized=True)

        # 3. Query config
        config = routine.config()
        assert config["initialized"] is True
        assert "output" in routine._events
        assert "input" in routine._slots

    def test_multiple_slots_and_events(self):
        """Test routine with multiple slots and events."""
        routine = Routine()

        # Add multiple slots
        routine.add_slot("input1")
        routine.add_slot("input2")

        # Add multiple events
        routine.add_event("output1", ["data"])
        routine.add_event("output2", ["result"])

        assert len(routine._slots) == 2
        assert len(routine._events) == 2


class TestRoutineSerialization:
    """Routine serialization tests."""

    def test_routine_serialize(self):
        """Test routine serialization."""
        routine = Routine()
        routine.add_slot("input")
        routine.add_event("output", ["data"])
        routine.set_config(key="value")

        data = routine.serialize()

        assert "_id" in data
        assert "_config" in data

    def test_routine_config_serialization(self):
        """Test config is properly serialized."""
        routine = Routine()
        routine.set_config(count=42, name="test")

        data = routine.serialize()
        assert data["_config"]["count"] == 42
        assert data["_config"]["name"] == "test"
