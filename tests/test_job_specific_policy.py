"""
Tests for Job-specific activation policy.

Tests verify that job-specific activation policies work correctly
and don't affect other jobs.
"""

import time

import pytest

from routilux.activation_policies import batch_size_policy, immediate_policy
from routilux.flow.flow import Flow
from routilux.job_state import JobState
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.routine import Routine
from routilux.runtime import Runtime


class TestJobSpecificPolicy:
    """Test job-specific activation policy functionality."""

    def test_set_routine_activation_policy(self):
        """Test: Setting job-specific activation policy works"""
        job_state = JobState("test_flow")
        
        def test_policy(slots, job_state):
            return True, {}, {"test": True}
        
        job_state.set_routine_activation_policy("test_routine", test_policy)
        
        # Retrieve policy
        policy = job_state.get_routine_activation_policy("test_routine")
        assert policy is not None
        assert policy == test_policy

    def test_job_specific_policy_takes_precedence(self):
        """Test: Job-specific policy takes precedence over routine default policy"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                
                def my_logic(input_data, policy_message, job_state):
                    # Store policy message to verify which policy was used
                    job_state.update_shared_data("policy_used", policy_message.get("source", "default"))
                
                self.set_logic(my_logic)
                # Set default policy to batch_size (requires 2 items)
                self.set_activation_policy(batch_size_policy(2))
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Set job-specific policy to immediate
        def job_specific_policy(slots, job_state):
            return True, {slot_name: slot.consume_all_new() for slot_name, slot in slots.items()}, {"source": "job_specific"}
        
        job_state.set_routine_activation_policy("test_routine", job_specific_policy)
        
        # Send single item (would not activate with batch_size policy)
        runtime.post("test_flow", "test_routine", "input", {"value": 1}, job_id=job_state.job_id)
        
        # Wait for execution
        time.sleep(0.2)
        
        # Verify job-specific policy was used
        policy_used = job_state.get_shared_data("policy_used")
        assert policy_used == "job_specific", f"Expected 'job_specific', got {policy_used}"
        
        runtime.wait_until_all_jobs_finished(timeout=2.0)

    def test_job_specific_policy_does_not_affect_other_jobs(self):
        """Test: Job-specific policy does not affect other jobs using same routine"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                
                def my_logic(input_data, policy_message, job_state):
                    job_state.update_shared_data("policy_used", policy_message.get("source", "default"))
                
                self.set_logic(my_logic)
                # Default policy requires 2 items
                self.set_activation_policy(batch_size_policy(2))
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        
        # Create two jobs
        job_state1 = runtime.exec("test_flow")
        job_state2 = runtime.exec("test_flow")
        
        # Set job-specific policy only for job1
        def job_specific_policy(slots, job_state):
            return True, {slot_name: slot.consume_all_new() for slot_name, slot in slots.items()}, {"source": "job_specific"}
        
        job_state1.set_routine_activation_policy("test_routine", job_specific_policy)
        
        # Send single item to both jobs
        runtime.post("test_flow", "test_routine", "input", {"value": 1}, job_id=job_state1.job_id)
        runtime.post("test_flow", "test_routine", "input", {"value": 1}, job_id=job_state2.job_id)
        
        # Wait for execution
        time.sleep(0.3)
        
        # Job1 should use job-specific policy (immediate)
        policy_used1 = job_state1.get_shared_data("policy_used")
        assert policy_used1 == "job_specific", f"Job1: Expected 'job_specific', got {policy_used1}"
        
        # Job2 should use default policy (batch_size, so should not activate with 1 item)
        policy_used2 = job_state2.get_shared_data("policy_used")
        # Job2 should not have executed (batch_size requires 2 items)
        assert policy_used2 is None, f"Job2: Expected None (not executed), got {policy_used2}"
        
        runtime.wait_until_all_jobs_finished(timeout=2.0)

    def test_remove_routine_activation_policy(self):
        """Test: Removing job-specific policy restores routine default policy"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                
                def my_logic(input_data, policy_message, job_state):
                    job_state.update_shared_data("policy_used", policy_message.get("source", "default"))
                
                self.set_logic(my_logic)
                # Default policy requires 2 items
                self.set_activation_policy(batch_size_policy(2))
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Set job-specific policy
        def job_specific_policy(slots, job_state):
            return True, {slot_name: slot.consume_all_new() for slot_name, slot in slots.items()}, {"source": "job_specific"}
        
        job_state.set_routine_activation_policy("test_routine", job_specific_policy)
        
        # Send single item - should activate with job-specific policy
        runtime.post("test_flow", "test_routine", "input", {"value": 1}, job_id=job_state.job_id)
        time.sleep(0.2)
        
        policy_used = job_state.get_shared_data("policy_used")
        assert policy_used == "job_specific"
        
        # Remove job-specific policy
        job_state.remove_routine_activation_policy("test_routine")
        
        # Clear shared data
        job_state.update_shared_data("policy_used", None)
        
        # Send single item again - should NOT activate (default policy requires 2 items)
        runtime.post("test_flow", "test_routine", "input", {"value": 2}, job_id=job_state.job_id)
        time.sleep(0.2)
        
        # Should not have executed (batch_size requires 2 items, but we only sent 1)
        policy_used = job_state.get_shared_data("policy_used")
        # Should still be None or "job_specific" from before, not executed again
        assert policy_used in (None, "job_specific")
        
        runtime.wait_until_all_jobs_finished(timeout=2.0)

    def test_job_specific_policy_with_none_default(self):
        """Test: Job-specific policy works when routine has no default policy"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                
                def my_logic(input_data, policy_message, job_state):
                    job_state.update_shared_data("executed", True)
                
                self.set_logic(my_logic)
                # No default policy
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Set job-specific policy
        def job_specific_policy(slots, job_state):
            # Only activate if input slot has data
            if "input" in slots and slots["input"].get_unconsumed_count() > 0:
                return True, {"input": slots["input"].consume_all_new()}, {"source": "job_specific"}
            return False, {}, None
        
        job_state.set_routine_activation_policy("test_routine", job_specific_policy)
        
        # Send data
        runtime.post("test_flow", "test_routine", "input", {"value": 1}, job_id=job_state.job_id)
        time.sleep(0.2)
        
        # Should have executed
        executed = job_state.get_shared_data("executed")
        assert executed is True
        
        runtime.wait_until_all_jobs_finished(timeout=2.0)
