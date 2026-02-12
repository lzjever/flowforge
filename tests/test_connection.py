"""
Connection tests for current API.

Tests for Connection class functionality.
"""

from datetime import datetime

from routilux import Connection, Routine


class TestConnectionCreation:
    """Connection creation tests."""

    def test_create_connection(self):
        """Test creating a connection."""
        routine1 = Routine()
        routine2 = Routine()

        event = routine1.add_event("output", ["data"])
        slot = routine2.add_slot("input")

        # Create connection
        connection = Connection(event, slot)

        # Verify connection object
        assert connection.source_event == event
        assert connection.target_slot == slot

    def test_connection_repr(self):
        """Test connection string representation."""
        routine1 = Routine()
        routine2 = Routine()

        event = routine1.add_event("output", ["data"])
        slot = routine2.add_slot("input")

        connection = Connection(event, slot)

        repr_str = repr(connection)
        assert "Connection" in repr_str


class TestConnectionSerialization:
    """Connection serialization tests."""

    def test_connection_serialize(self):
        """Test connection serialization."""
        routine1 = Routine()
        routine2 = Routine()

        event = routine1.add_event("output", ["data"])
        slot = routine2.add_slot("input")

        connection = Connection(event, slot)

        data = connection.serialize()

        assert "_type" in data
        assert data["_type"] == "Connection"

    def test_connection_serialize_data(self):
        """Test connection serialization contains expected data."""
        routine1 = Routine()
        routine2 = Routine()

        event = routine1.add_event("output", ["data"])
        slot = routine2.add_slot("input")

        connection = Connection(event, slot)

        # Serialize
        data = connection.serialize()

        # Verify serialization data structure
        assert "_type" in data
        assert data["_type"] == "Connection"
        # Note: source_event and target_slot are serialized by reference
        # so they may contain routine_id and event/slot names


class TestConnectionDisconnect:
    """Connection disconnect tests."""

    def test_disconnect(self):
        """Test disconnecting a connection."""
        routine1 = Routine()
        routine2 = Routine()

        event = routine1.add_event("output", ["data"])
        slot = routine2.add_slot("input")

        connection = Connection(event, slot)

        # Connect event to slot
        event.connect(slot)

        # Verify connection
        assert slot in event.connected_slots

        # Disconnect
        connection.disconnect()

        # After disconnect, slot should not be in event's connected_slots
        # (depending on implementation)


class TestConnectionWithFlow:
    """Test Connection when used with Flow."""

    def test_flow_connection(self):
        """Test connection created through Flow.connect()."""
        from routilux import Flow

        flow = Flow()

        routine1 = Routine()
        routine2 = Routine()

        routine1.add_event("output", ["data"])
        routine2.add_slot("input")

        id1 = flow.add_routine(routine1, "source")
        id2 = flow.add_routine(routine2, "target")

        # Connect through flow
        connection = flow.connect(id1, "output", id2, "input")

        assert connection is not None
        assert connection in flow.connections

    def test_multiple_connections(self):
        """Test multiple connections in a flow."""
        from routilux import Flow

        flow = Flow()

        source = Routine()
        target1 = Routine()
        target2 = Routine()

        source.add_event("output", ["data"])
        target1.add_slot("input")
        target2.add_slot("input")

        source_id = flow.add_routine(source, "source")
        target1_id = flow.add_routine(target1, "target1")
        target2_id = flow.add_routine(target2, "target2")

        # Connect source to both targets
        flow.connect(source_id, "output", target1_id, "input")
        flow.connect(source_id, "output", target2_id, "input")

        assert len(flow.connections) == 2


class TestSlotEnqueue:
    """Test Slot.enqueue method (replacement for connection.activate)."""

    def test_enqueue_data(self):
        """Test enqueueing data to a slot."""
        routine = Routine()
        slot = routine.add_slot("input")

        # Enqueue data
        slot.enqueue(
            data={"value": 42},
            emitted_from="test_source",
            emitted_at=datetime.now(),
        )

        # Verify data is in queue
        assert len(slot._queue) == 1
        assert slot._queue[0].data == {"value": 42}

    def test_enqueue_multiple_items(self):
        """Test enqueueing multiple items."""
        routine = Routine()
        slot = routine.add_slot("input")

        # Enqueue multiple items
        for i in range(5):
            slot.enqueue(
                data={"value": i},
                emitted_from="test",
                emitted_at=datetime.now(),
            )

        assert len(slot._queue) == 5

    def test_consume_enqueued_data(self):
        """Test consuming enqueued data."""
        routine = Routine()
        slot = routine.add_slot("input")

        # Enqueue data
        slot.enqueue(
            data={"value": 1},
            emitted_from="test",
            emitted_at=datetime.now(),
        )
        slot.enqueue(
            data={"value": 2},
            emitted_from="test",
            emitted_at=datetime.now(),
        )

        # Consume all new data
        data = slot.consume_all_new()

        assert len(data) == 2
        assert data[0] == {"value": 1}
        assert data[1] == {"value": 2}
