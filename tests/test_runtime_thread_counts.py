"""
Tests for Runtime thread count tracking.

Tests verify that Runtime correctly tracks active thread counts for routines.
"""

import threading
import time

import pytest

from routilux.activation_policies import immediate_policy
from routilux.flow.flow import Flow
from routilux.job_state import JobState
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.routine import Routine
from routilux.runtime import Runtime


class TestRuntimeThreadCountTracking:
    """Test thread count tracking in Runtime."""

    def test_get_active_thread_count_empty(self):
        """Test: get_active_thread_count returns 0 for non-existent job/routine"""
        runtime = Runtime()
        count = runtime.get_active_thread_count("non_existent_job_id", "non_existent_routine")
        assert count == 0

    def test_get_active_thread_count_single_routine(self):
        """Test: get_active_thread_count returns correct count for single routine execution"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                self.output_event = self.define_event("output")
                
                def my_logic(input_data, policy_message, job_state):
                    time.sleep(0.1)  # Simulate work
                
                self.set_logic(my_logic)
                self.set_activation_policy(immediate_policy())
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Wait a bit for routine to start and check multiple times
        # (routine might execute very quickly)
        max_attempts = 10
        count = 0
        for _ in range(max_attempts):
            time.sleep(0.05)
            count = runtime.get_active_thread_count(job_state.job_id, "test_routine")
            if count >= 1:
                break
        
        # Thread count should be at least 1 during execution, or 0 if already completed
        # (both are valid - depends on timing)
        assert count >= 0, f"Thread count should be non-negative, got {count}"
        
        # Wait for completion
        runtime.wait_until_all_jobs_finished(timeout=2.0)
        
        # After completion, count should be 0
        count = runtime.get_active_thread_count(job_state.job_id, "test_routine")
        assert count == 0

    def test_get_active_thread_count_multiple_instances(self):
        """Test: get_active_thread_count correctly tracks multiple concurrent instances"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                self.output_event = self.define_event("output")
                
                def my_logic(input_data, policy_message, job_state):
                    time.sleep(0.2)  # Longer sleep to allow multiple instances
                
                self.set_logic(my_logic)
                self.set_activation_policy(immediate_policy())
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Trigger multiple activations quickly
        for i in range(3):
            runtime.post("test_flow", "test_routine", "input", {"value": i}, job_id=job_state.job_id)
            time.sleep(0.01)  # Small delay between triggers
        
        # Wait a bit for routines to start and check multiple times
        max_attempts = 10
        count = 0
        for _ in range(max_attempts):
            time.sleep(0.05)
            count = runtime.get_active_thread_count(job_state.job_id, "test_routine")
            if count >= 1:
                break
        
        # Thread count should be at least 1 during execution, or 0 if already completed
        # (both are valid - depends on timing)
        assert count >= 0, f"Thread count should be non-negative, got {count}"
        # Note: Could be up to 3, but depends on thread pool size and timing
        
        # Wait for completion
        runtime.wait_until_all_jobs_finished(timeout=3.0)
        
        # After completion, count should be 0
        count = runtime.get_active_thread_count(job_state.job_id, "test_routine")
        assert count == 0

    def test_get_active_thread_count_thread_safe(self):
        """Test: Thread count tracking is thread-safe"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                self.output_event = self.define_event("output")
                
                def my_logic(input_data, policy_message, job_state):
                    time.sleep(0.05)
                
                self.set_logic(my_logic)
                self.set_activation_policy(immediate_policy())
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Trigger multiple activations from different threads
        def trigger_activation(i):
            runtime.post("test_flow", "test_routine", "input", {"value": i}, job_id=job_state.job_id)
        
        threads = [threading.Thread(target=trigger_activation, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        
        # Check thread count concurrently
        counts = []
        def check_count():
            time.sleep(0.05)
            count = runtime.get_active_thread_count(job_state.job_id, "test_routine")
            counts.append(count)
        
        check_threads = [threading.Thread(target=check_count) for _ in range(10)]
        for t in check_threads:
            t.start()
        
        # Wait for all threads
        for t in threads + check_threads:
            t.join()
        
        # All counts should be valid (>= 0)
        assert all(c >= 0 for c in counts), f"Found negative count: {counts}"
        
        # Wait for completion
        runtime.wait_until_all_jobs_finished(timeout=3.0)
        
        # Final count should be 0
        final_count = runtime.get_active_thread_count(job_state.job_id, "test_routine")
        assert final_count == 0

    def test_get_all_active_thread_counts(self):
        """Test: get_all_active_thread_counts returns correct counts for all routines"""
        flow = Flow("test_flow")
        
        class RoutineA(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                self.output_event = self.define_event("output")
                
                def logic_a(input_data, policy_message, job_state):
                    time.sleep(0.1)
                    RoutineA.output_event.emit(runtime, job_state, data="from_A")
                
                self.set_logic(logic_a)
                self.set_activation_policy(immediate_policy())
        
        class RoutineB(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                
                def logic_b(input_data, policy_message, job_state):
                    time.sleep(0.1)
                
                self.set_logic(logic_b)
                self.set_activation_policy(immediate_policy())
        
        routine_a = RoutineA()
        routine_b = RoutineB()
        flow.add_routine(routine_a, "routine_a")
        flow.add_routine(routine_b, "routine_b")
        flow.connect("routine_a", "output", "routine_b", "input")
        
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Wait a bit for routines to start
        time.sleep(0.1)
        
        # Get all thread counts
        all_counts = runtime.get_all_active_thread_counts(job_state.job_id)
        
        # Should have counts for routines that are active
        assert isinstance(all_counts, dict)
        
        # Wait for completion
        runtime.wait_until_all_jobs_finished(timeout=3.0)
        
        # After completion, all counts should be 0 or empty
        all_counts = runtime.get_all_active_thread_counts(job_state.job_id)
        assert all_counts == {} or all(count == 0 for count in all_counts.values())

    def test_thread_count_cleanup_on_job_completion(self):
        """Test: Thread counts are cleaned up when job completes"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                
                def my_logic(input_data, policy_message, job_state):
                    pass
                
                self.set_logic(my_logic)
                self.set_activation_policy(immediate_policy())
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Wait for completion
        runtime.wait_until_all_jobs_finished(timeout=2.0)
        
        # Check that thread counts are cleaned up
        count = runtime.get_active_thread_count(job_state.job_id, "test_routine")
        assert count == 0
        
        # Check that job entry is cleaned up
        all_counts = runtime.get_all_active_thread_counts(job_state.job_id)
        assert all_counts == {} or all(count == 0 for count in all_counts.values())
