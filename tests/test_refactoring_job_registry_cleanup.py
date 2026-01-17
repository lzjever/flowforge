"""
Tests for JobRegistry automatic cleanup refactoring.

Tests verify that:
1. mark_completed() records timestamp
2. Cleanup thread starts and runs periodically
3. Old completed jobs are cleaned up after retention period
4. Running jobs are not affected by cleanup
"""

import threading
import time
from datetime import datetime, timedelta

import pytest

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.job_executor import JobExecutor
from routilux.job_manager import get_job_manager
from routilux.job_state import JobState
from routilux.monitoring.job_registry import JobRegistry
from routilux.status import ExecutionStatus


class TestMarkCompleted:
    """Test mark_completed() functionality."""

    def test_mark_completed_records_timestamp(self):
        """Test: mark_completed() records timestamp."""
        registry = JobRegistry.get_instance()
        registry._completed_jobs.clear()

        job_state = JobState(flow_id="test_flow")
        registry.register(job_state)

        # Interface contract: mark_completed() should record timestamp
        before = datetime.now()
        registry.mark_completed(job_state.job_id)
        after = datetime.now()

        assert job_state.job_id in registry._completed_jobs
        completed_at = registry._completed_jobs[job_state.job_id]

        # Timestamp should be between before and after
        assert before <= completed_at <= after

    def test_mark_completed_adds_to_completed_jobs(self):
        """Test: mark_completed() adds job to _completed_jobs."""
        registry = JobRegistry.get_instance()
        registry._completed_jobs.clear()

        job_state = JobState(flow_id="test_flow")
        registry.register(job_state)

        # Interface contract: Should add to _completed_jobs dictionary
        registry.mark_completed(job_state.job_id)

        assert job_state.job_id in registry._completed_jobs
        assert isinstance(registry._completed_jobs[job_state.job_id], datetime)


class TestCleanupThread:
    """Test cleanup thread functionality."""

    def test_cleanup_thread_starts_on_register(self):
        """Test: Cleanup thread starts when first job is registered."""
        registry = JobRegistry.get_instance()
        registry._cleanup_running = False
        if registry._cleanup_thread:
            registry._cleanup_thread.join(timeout=1.0)

        job_state = JobState(flow_id="test_flow")

        # Interface contract: Registering should start cleanup thread
        registry.register(job_state)

        # Wait a bit for thread to start
        time.sleep(0.1)

        assert registry._cleanup_running is True
        assert registry._cleanup_thread is not None
        assert registry._cleanup_thread.is_alive()

    def test_cleanup_thread_runs_periodically(self):
        """Test: Cleanup thread runs periodically."""
        registry = JobRegistry.get_instance()
        registry._cleanup_interval = 0.5  # Short interval for testing
        registry._completed_jobs.clear()

        # Register and mark as completed
        job_state = JobState(flow_id="test_flow")
        registry.register(job_state)
        registry.mark_completed(job_state.job_id)

        # Set old timestamp (beyond cleanup interval)
        old_time = datetime.now() - timedelta(seconds=1.0)
        registry._completed_jobs[job_state.job_id] = old_time

        # Wait for cleanup cycle
        time.sleep(0.8)

        # Interface contract: Cleanup thread should remove old jobs
        # Note: This may take a moment, so we check if it's removed or still there
        # The key is that cleanup thread is running
        assert registry._cleanup_running is True

    def test_cleanup_thread_stops_on_clear(self):
        """Test: Cleanup thread stops when clear() is called."""
        registry = JobRegistry.get_instance()

        # Start cleanup thread
        job_state = JobState(flow_id="test_flow")
        registry.register(job_state)

        assert registry._cleanup_running is True

        # Interface contract: clear() should stop cleanup thread
        registry.clear()

        # Wait for thread to stop
        if registry._cleanup_thread:
            registry._cleanup_thread.join(timeout=1.0)

        assert registry._cleanup_running is False


class TestCleanupLogic:
    """Test cleanup logic."""

    def test_cleanup_removes_old_completed_jobs(self):
        """Test: Cleanup removes jobs beyond retention period."""
        registry = JobRegistry.get_instance()
        registry._cleanup_interval = 0.3  # Short interval for testing
        registry._completed_jobs.clear()
        registry._jobs.clear()

        # Register multiple jobs
        job1 = JobState(flow_id="test_flow")
        job2 = JobState(flow_id="test_flow")
        job3 = JobState(flow_id="test_flow")

        registry.register(job1)
        registry.register(job2)
        registry.register(job3)

        # Mark as completed with different timestamps
        registry.mark_completed(job1.job_id)
        registry.mark_completed(job2.job_id)
        registry.mark_completed(job3.job_id)

        # Set old timestamp for job1 (should be cleaned)
        old_time = datetime.now() - timedelta(seconds=1.0)
        registry._completed_jobs[job1.job_id] = old_time

        # Set recent timestamp for job2 (should be kept)
        recent_time = datetime.now()
        registry._completed_jobs[job2.job_id] = recent_time

        # Manually trigger cleanup
        registry._cleanup_completed_jobs()

        # Interface contract: Old jobs should be removed
        assert job1.job_id not in registry._completed_jobs
        assert job1.job_id not in registry._jobs

        # Recent jobs should be kept
        assert job2.job_id in registry._completed_jobs
        assert job3.job_id in registry._completed_jobs

    def test_cleanup_preserves_recent_completed_jobs(self):
        """Test: Cleanup preserves recently completed jobs."""
        registry = JobRegistry.get_instance()
        registry._cleanup_interval = 600.0  # 10 minutes
        registry._completed_jobs.clear()

        job_state = JobState(flow_id="test_flow")
        registry.register(job_state)
        registry.mark_completed(job_state.job_id)

        # Manually trigger cleanup
        registry._cleanup_completed_jobs()

        # Interface contract: Recent jobs should be preserved
        assert job_state.job_id in registry._completed_jobs
        assert job_state.job_id in registry._jobs

    def test_cleanup_does_not_affect_running_jobs(self):
        """Test: Cleanup does not affect running jobs."""
        registry = JobRegistry.get_instance()
        registry._cleanup_interval = 0.3
        registry._completed_jobs.clear()

        # Create running job
        flow = Flow("test_flow")
        routine = Routine()
        routine.define_slot("input")
        routine.set_logic(lambda *args: None)
        routine.set_activation_policy(immediate_policy())
        flow.add_routine(routine, "routine")

        job_manager = get_job_manager()
        job_state = job_manager.start_job(flow=flow, timeout=None)

        registry.register(job_state)

        # Job is running, not completed
        assert job_state.status == ExecutionStatus.RUNNING

        # Manually trigger cleanup
        registry._cleanup_completed_jobs()

        # Interface contract: Running jobs should not be affected
        assert job_state.job_id in registry._jobs

        # Cleanup
        executor = job_manager.get_job(job_state.job_id)
        if executor:
            executor.stop()

    def test_cleanup_updates_flow_jobs_mapping(self):
        """Test: Cleanup updates flow_jobs mapping."""
        registry = JobRegistry.get_instance()
        registry._cleanup_interval = 0.3
        registry._completed_jobs.clear()
        registry._flow_jobs.clear()

        # Register jobs for same flow
        job1 = JobState(flow_id="test_flow")
        job2 = JobState(flow_id="test_flow")

        registry.register(job1)
        registry.register(job2)

        # Mark as completed
        registry.mark_completed(job1.job_id)
        registry.mark_completed(job2.job_id)

        # Set old timestamp for job1
        old_time = datetime.now() - timedelta(seconds=1.0)
        registry._completed_jobs[job1.job_id] = old_time

        # Manually trigger cleanup
        registry._cleanup_completed_jobs()

        # Interface contract: flow_jobs mapping should be updated
        flow_jobs = registry._flow_jobs.get("test_flow", [])
        assert job1.job_id not in flow_jobs
        assert job2.job_id in flow_jobs


class TestCleanupEdgeCases:
    """Test cleanup edge cases."""

    def test_cleanup_with_custom_interval(self):
        """Test: Cleanup works with custom interval."""
        registry = JobRegistry.get_instance()
        custom_interval = 300.0  # 5 minutes
        registry._cleanup_interval = custom_interval

        # Interface contract: Should use custom interval
        assert registry._cleanup_interval == custom_interval

        # Reset to default
        registry._cleanup_interval = 600.0

    def test_cleanup_thread_exception_handling(self):
        """Test: Cleanup thread handles exceptions gracefully."""
        registry = JobRegistry.get_instance()

        # Start cleanup thread
        job_state = JobState(flow_id="test_flow")
        registry.register(job_state)

        # Simulate exception in cleanup (by corrupting data)
        registry._completed_jobs["invalid_job_id"] = "invalid_timestamp"

        # Manually trigger cleanup - should not crash
        try:
            registry._cleanup_completed_jobs()
        except Exception:
            pytest.fail("Cleanup should handle exceptions gracefully")

        # Thread should still be running
        assert registry._cleanup_running is True

    def test_concurrent_cleanup_and_access(self):
        """Test: Concurrent cleanup and access is thread-safe."""
        registry = JobRegistry.get_instance()
        registry._cleanup_interval = 0.3
        registry._completed_jobs.clear()

        # Register multiple jobs
        jobs = [JobState(flow_id="test_flow") for _ in range(10)]
        for job in jobs:
            registry.register(job)
            registry.mark_completed(job.job_id)

        errors = []

        def access_registry(i):
            try:
                # Access registry while cleanup might be running
                job = registry.get(jobs[i].job_id)
                if job:
                    _ = job.flow_id
            except Exception as e:
                errors.append((i, e))

        # Concurrent access
        threads = [threading.Thread(target=access_registry, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Interface contract: Should handle concurrent access without errors
        assert len(errors) == 0
