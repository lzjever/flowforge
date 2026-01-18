"""Tests for WorkerState class."""

import pytest
from routilux.core import ExecutionRecord, ExecutionStatus, Flow, WorkerState


class TestWorkerState:
    """Test WorkerState class."""

    def test_worker_state_creation(self):
        """Test creating a WorkerState."""
        flow = Flow()
        worker_state = WorkerState(flow_id=flow.flow_id)
        
        assert worker_state.flow_id == flow.flow_id
        assert worker_state.worker_id is not None
        assert worker_state.status == ExecutionStatus.IDLE
        assert worker_state.routine_states == {}
        assert worker_state.execution_history == []
        assert worker_state.jobs_processed == 0
        assert worker_state.jobs_failed == 0

    def test_worker_state_update_routine_state(self):
        """Test updating routine state."""
        flow = Flow()
        worker_state = WorkerState(flow_id=flow.flow_id)
        
        worker_state.update_routine_state("routine1", "active")
        
        assert worker_state.routine_states["routine1"] == "active"

    def test_worker_state_record_execution(self):
        """Test recording execution."""
        flow = Flow()
        worker_state = WorkerState(flow_id=flow.flow_id)
        
        record = worker_state.record_execution(
            routine_id="routine1",
            event_name="output",
            data={"value": 42}
        )
        
        assert isinstance(record, ExecutionRecord)
        assert record.routine_id == "routine1"
        assert record.event_name == "output"
        assert record.data == {"value": 42}
        assert len(worker_state.execution_history) == 1

    def test_worker_state_serialization(self):
        """Test WorkerState serialization."""
        flow = Flow()
        worker_state = WorkerState(flow_id=flow.flow_id)
        worker_state.update_routine_state("routine1", "active")
        worker_state.record_execution("routine1", "output", {"test": "data"})
        
        data = worker_state.serialize()
        
        assert data["flow_id"] == flow.flow_id
        assert data["worker_id"] == worker_state.worker_id
        assert "routine_states" in data
        assert "execution_history" in data

    def test_worker_state_deserialization(self):
        """Test WorkerState deserialization."""
        flow = Flow()
        worker_state = WorkerState(flow_id=flow.flow_id)
        worker_state.update_routine_state("routine1", "active")
        
        data = worker_state.serialize()
        restored = WorkerState.deserialize(data)
        
        assert restored.flow_id == worker_state.flow_id
        assert restored.worker_id == worker_state.worker_id
        assert restored.routine_states == worker_state.routine_states


class TestExecutionRecord:
    """Test ExecutionRecord class."""

    def test_execution_record_creation(self):
        """Test creating an ExecutionRecord."""
        record = ExecutionRecord(
            routine_id="routine1",
            event_name="output",
            data={"value": 42}
        )
        
        assert record.routine_id == "routine1"
        assert record.event_name == "output"
        assert record.data == {"value": 42}
        assert record.timestamp is not None

    def test_execution_record_serialization(self):
        """Test ExecutionRecord serialization."""
        record = ExecutionRecord(
            routine_id="routine1",
            event_name="output",
            data={"value": 42}
        )
        
        data = record.serialize()
        
        assert data["routine_id"] == "routine1"
        assert data["event_name"] == "output"
        assert data["data"] == {"value": 42}
        assert "timestamp" in data
