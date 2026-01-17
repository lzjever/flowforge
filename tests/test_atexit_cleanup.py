"""
Test that atexit cleanup doesn't block process exit.

This test verifies that the atexit cleanup handler for GlobalJobManager
doesn't block process exit, especially when Ctrl+C is pressed.
"""

import pytest
import sys
import time
import threading
from unittest.mock import Mock, patch

from routilux.job_manager import get_job_manager, _cleanup_global_job_manager


def test_atexit_cleanup_doesnt_block():
    """Test: atexit cleanup completes quickly without blocking."""
    # Get job manager instance
    manager = get_job_manager()
    
    # Create a mock executor that might take time to stop
    mock_executor = Mock()
    mock_executor.stop = Mock()
    
    # Add mock executor to running jobs
    manager.running_jobs["test_job"] = mock_executor
    
    # Call cleanup function directly (simulating atexit)
    start_time = time.time()
    _cleanup_global_job_manager()
    elapsed = time.time() - start_time
    
    # Cleanup should complete quickly (< 0.5 seconds)
    assert elapsed < 0.5, f"Cleanup took too long: {elapsed:.2f}s"
    
    # Verify executor.stop was called with fast_cleanup
    mock_executor.stop.assert_called_once_with(wait_thread=False)


def test_shutdown_with_fast_cleanup():
    """Test: shutdown with fast_cleanup=True doesn't wait for threads."""
    manager = get_job_manager()
    
    # Create mock executor
    mock_executor = Mock()
    mock_executor.stop = Mock()
    manager.running_jobs["test_job"] = mock_executor
    
    # Shutdown with fast_cleanup
    start_time = time.time()
    manager.shutdown(wait=False, timeout=0.0, fast_cleanup=True)
    elapsed = time.time() - start_time
    
    # Should complete quickly
    assert elapsed < 0.5, f"Shutdown took too long: {elapsed:.2f}s"
    
    # Verify executor.stop was called with wait_thread=False
    mock_executor.stop.assert_called_once_with(wait_thread=False)


def test_shutdown_without_fast_cleanup():
    """Test: shutdown without fast_cleanup waits for threads (normal mode)."""
    # Create a fresh manager for this test
    from routilux.job_manager import GlobalJobManager
    manager = GlobalJobManager()
    
    # Create mock executor
    mock_executor = Mock()
    mock_executor.stop = Mock()
    manager.running_jobs["test_job"] = mock_executor
    
    # Shutdown without fast_cleanup (normal mode)
    manager.shutdown(wait=False, timeout=0.0, fast_cleanup=False)
    
    # Verify executor.stop was called with wait_thread=True (default)
    mock_executor.stop.assert_called_once_with(wait_thread=True)


def test_executor_stop_with_wait_thread_false():
    """Test: executor.stop(wait_thread=False) doesn't block."""
    from routilux.job_executor import JobExecutor
    from routilux.job_state import JobState
    from routilux import Flow
    
    # Create a minimal flow and job state
    flow = Flow("test_flow")
    job_state = JobState("test_flow")  # JobState takes only flow_id
    
    # Get global thread pool
    job_manager = get_job_manager()
    global_thread_pool = job_manager.global_thread_pool
    
    # Create executor
    executor = JobExecutor(
        flow=flow,
        job_state=job_state,
        global_thread_pool=global_thread_pool
    )
    
    # Start executor (creates daemon thread)
    executor.start()
    
    # Stop without waiting for thread
    start_time = time.time()
    executor.stop(wait_thread=False)
    elapsed = time.time() - start_time
    
    # Should complete immediately (< 0.1 seconds)
    assert elapsed < 0.1, f"stop(wait_thread=False) took too long: {elapsed:.2f}s"
    
    # Verify executor is stopped
    assert not executor.is_running()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
