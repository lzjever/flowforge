"""Tests for Routine class."""

import pytest

from routilux.core import Routine
from routilux.core.context import (
    ExecutionContext,
    JobContext,
    set_current_execution_context,
    set_current_job,
    set_current_worker_state,
)
from routilux.core.flow import Flow
from routilux.core.worker import WorkerState


class TestRoutine:
    """Test Routine class."""

    def test_routine_creation(self):
        """Test creating a routine."""

        class TestRoutine(Routine):
            def setup(self):
                pass

        routine = TestRoutine()

        assert routine._id is not None
        assert routine._slots == {}
        assert routine._events == {}
        assert routine._config == {}

    def test_routine_add_slot(self):
        """Test adding a slot to a routine."""

        class TestRoutine(Routine):
            def setup(self):
                self.add_slot("input")

        routine = TestRoutine()
        routine.setup()

        assert "input" in routine._slots
        assert routine._slots["input"].name == "input"

    def test_routine_add_event(self):
        """Test adding an event to a routine."""

        class TestRoutine(Routine):
            def setup(self):
                self.add_event("output")

        routine = TestRoutine()
        routine.setup()

        assert "output" in routine._events
        assert routine._events["output"].name == "output"

    def test_routine_set_config(self):
        """Test setting routine configuration."""

        class TestRoutine(Routine):
            def setup(self):
                pass

        routine = TestRoutine()
        routine.set_config(name="test", timeout=30)

        assert routine._config["name"] == "test"
        assert routine._config["timeout"] == 30

    def test_routine_get_execution_context_no_context(self):
        """Test getting execution context when not in execution."""

        class TestRoutine(Routine):
            def setup(self):
                pass

        routine = TestRoutine()
        context = routine.get_execution_context()

        # Should return None when not in execution context
        assert context is None

    def test_routine_emit_requires_context(self):
        """Test that emit requires execution context."""

        class TestRoutine(Routine):
            def setup(self):
                self.add_event("output")

        routine = TestRoutine()
        routine.setup()

        # Emit should fail without execution context
        with pytest.raises((AttributeError, RuntimeError)):
            routine.emit("output", data={"test": "value"})


class TestRoutineLogic:
    """Test routine logic execution."""

    def test_routine_logic_execution(self):
        """Test that routine logic can be executed."""

        class ProcessorRoutine(Routine):
            def setup(self):
                self.add_slot("input")
                self.add_event("output")

            def logic(self, input_data, **kwargs):
                return {"result": input_data.get("value", 0) * 2}

        routine = ProcessorRoutine()
        routine.setup()

        # Test logic directly (not through slot call)
        result = routine.logic({"value": 5})
        assert result == {"result": 10}

    def test_routine_logic_with_kwargs(self):
        """Test routine logic with additional kwargs."""

        class TestRoutine(Routine):
            def setup(self):
                self.add_slot("input")

            def logic(self, input_data, **kwargs):
                return {"data": input_data, "extra": kwargs.get("extra", None)}

        routine = TestRoutine()
        routine.setup()

        result = routine.logic({"test": "data"}, extra="value")
        assert result["data"] == {"test": "data"}
        assert result["extra"] == "value"


class TestRoutineJobData:
    """Test Routine.set_job_data() and get_job_data() methods."""

    def test_set_job_data_requires_job_context(self):
        """Test that set_job_data raises error without job context."""

        class TestRoutine(Routine):
            def setup(self):
                pass

        routine = TestRoutine()
        flow = Flow()
        routine_id = flow.add_routine(routine, "test_routine")

        # Set execution context but no job context
        ctx = ExecutionContext(
            flow=flow,
            worker_state=WorkerState(flow_id="test_flow"),
            routine_id=routine_id,
            job_context=None,
        )
        set_current_execution_context(ctx)

        # Without job context, should raise RuntimeError
        with pytest.raises(RuntimeError, match="set_job_data requires job context"):
            routine.set_job_data("key", "value")

        set_current_execution_context(None)

    def test_set_job_data_requires_routine_id(self):
        """Test that set_job_data raises error without routine_id."""

        class TestRoutine(Routine):
            def setup(self):
                pass

        routine = TestRoutine()
        job = JobContext(job_id="test-job")
        flow = Flow()
        worker_state = WorkerState(flow_id="test_flow")

        # Set execution context but with empty routine_id
        ctx = ExecutionContext(
            flow=flow,
            worker_state=worker_state,
            routine_id="",  # Empty routine_id
            job_context=job,
        )
        set_current_execution_context(ctx)
        set_current_job(job)

        # Without routine_id, should raise RuntimeError
        with pytest.raises(RuntimeError, match="set_job_data requires routine_id"):
            routine.set_job_data("key", "value")

        set_current_execution_context(None)
        set_current_job(None)

    def test_get_job_data_returns_default_without_context(self):
        """Test that get_job_data returns default without context."""

        class TestRoutine(Routine):
            def setup(self):
                pass

        routine = TestRoutine()

        # Without context, should return default
        result = routine.get_job_data("key", "default_value")
        assert result == "default_value"

    def test_set_and_get_job_data_with_context(self):
        """Test setting and getting job data with proper context."""

        class TestRoutine(Routine):
            def setup(self):
                pass

        routine = TestRoutine()
        flow = Flow()
        routine_id = flow.add_routine(routine, "test_routine")

        job = JobContext(job_id="test-job")
        worker_state = WorkerState(flow_id="test_flow")

        # Set unified execution context
        ctx = ExecutionContext(
            flow=flow,
            worker_state=worker_state,
            routine_id=routine_id,
            job_context=job,
        )
        set_current_execution_context(ctx)
        set_current_job(job)
        set_current_worker_state(worker_state)

        # Set data
        routine.set_job_data("test_key", "test_value")
        routine.set_job_data("another_key", 42)

        # Get data
        assert routine.get_job_data("test_key") == "test_value"
        assert routine.get_job_data("another_key") == 42
        assert routine.get_job_data("nonexistent", "default") == "default"

        # Verify namespacing in job.data
        expected_key = f"{routine_id}_test_key"
        assert job.data[expected_key] == "test_value"
        assert f"{routine_id}_another_key" in job.data

        set_current_execution_context(None)
        set_current_job(None)
        set_current_worker_state(None)

    def test_job_data_isolation_between_routines(self):
        """Test that job data is isolated between different routine instances."""

        class TestRoutine(Routine):
            def setup(self):
                pass

        routine1 = TestRoutine()
        routine2 = TestRoutine()
        flow = Flow()
        routine_id1 = flow.add_routine(routine1, "routine1")
        routine_id2 = flow.add_routine(routine2, "routine2")

        job = JobContext(job_id="test-job")
        worker_state = WorkerState(flow_id="test_flow")

        # Set execution context for routine1
        ctx1 = ExecutionContext(
            flow=flow,
            worker_state=worker_state,
            routine_id=routine_id1,
            job_context=job,
        )
        set_current_execution_context(ctx1)
        set_current_job(job)
        set_current_worker_state(worker_state)

        # Set data in routine1
        routine1.set_job_data("shared_key", "value1")

        # Set execution context for routine2
        ctx2 = ExecutionContext(
            flow=flow,
            worker_state=worker_state,
            routine_id=routine_id2,
            job_context=job,
        )
        set_current_execution_context(ctx2)

        # Set data in routine2
        routine2.set_job_data("shared_key", "value2")

        # Each routine should see its own value
        set_current_execution_context(ctx1)
        assert routine1.get_job_data("shared_key") == "value1"

        set_current_execution_context(ctx2)
        assert routine2.get_job_data("shared_key") == "value2"

        # Verify namespacing in job.data
        assert job.data[f"{routine_id1}_shared_key"] == "value1"
        assert job.data[f"{routine_id2}_shared_key"] == "value2"

        set_current_execution_context(None)
        set_current_job(None)
        set_current_worker_state(None)
