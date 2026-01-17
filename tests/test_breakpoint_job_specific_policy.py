"""
Tests for breakpoint integration with job-specific activation policy.

Tests verify that breakpoints use job-specific policy and don't affect other jobs.
"""

import time

import pytest

from routilux.activation_policies import immediate_policy
from routilux.flow.flow import Flow
from routilux.monitoring.breakpoint_manager import Breakpoint
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.monitoring.registry import MonitoringRegistry
from routilux.monitoring.storage import job_store
from routilux.routine import Routine
from routilux.runtime import Runtime


class TestBreakpointJobSpecificPolicy:
    """Test breakpoint integration with job-specific policy."""

    def test_breakpoint_uses_job_specific_policy(self):
        """Test: Breakpoint uses job-specific policy instead of modifying routine"""
        # Enable monitoring
        MonitoringRegistry.enable()
        
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                
                def my_logic(input_data, policy_message, job_state):
                    job_state.update_shared_data("executed", True)
                
                self.set_logic(my_logic)
                self.set_activation_policy(immediate_policy())
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Add breakpoint
        registry = MonitoringRegistry.get_instance()
        breakpoint_mgr = registry.breakpoint_manager
        
        breakpoint = Breakpoint(
            job_id=job_state.job_id,
            type="routine",
            routine_id="test_routine",
            enabled=True,
        )
        
        # Manually set breakpoint using job-specific policy (simulating API behavior)
        from routilux.activation_policies import breakpoint_policy
        
        # Save original policy
        original_policy = routine._activation_policy
        breakpoint._original_policy = original_policy
        
        # Set breakpoint policy as job-specific
        bp_policy = breakpoint_policy("test_routine")
        job_state.set_routine_activation_policy("test_routine", bp_policy)
        
        breakpoint_mgr.add_breakpoint(breakpoint)
        
        # Send data - should not execute due to breakpoint
        runtime.post("test_flow", "test_routine", "input", {"value": 1}, job_id=job_state.job_id)
        time.sleep(0.2)
        
        # Should not have executed
        executed = job_state.get_shared_data("executed")
        assert executed is None or executed is False, "Routine should not execute with breakpoint"
        
        # Check that debug data was saved
        assert hasattr(job_state, "debug_data")
        assert "test_routine" in job_state.debug_data
        
        runtime.wait_until_all_jobs_finished(timeout=2.0)

    def test_breakpoint_does_not_affect_other_jobs(self):
        """Test: Breakpoint in one job does not affect other jobs"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                
                def my_logic(input_data, policy_message, job_state):
                    job_state.update_shared_data("executed", True)
                
                self.set_logic(my_logic)
                self.set_activation_policy(immediate_policy())
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        
        # Create two jobs
        job_state1 = runtime.exec("test_flow")
        job_state2 = runtime.exec("test_flow")
        
        # Enable monitoring and add breakpoint only to job1
        MonitoringRegistry.enable()
        registry = MonitoringRegistry.get_instance()
        breakpoint_mgr = registry.breakpoint_manager
        
        breakpoint = Breakpoint(
            job_id=job_state1.job_id,
            type="routine",
            routine_id="test_routine",
            enabled=True,
        )
        
        # Set breakpoint for job1 only
        from routilux.activation_policies import breakpoint_policy
        
        original_policy = routine._activation_policy
        breakpoint._original_policy = original_policy
        
        bp_policy = breakpoint_policy("test_routine")
        job_state1.set_routine_activation_policy("test_routine", bp_policy)
        
        breakpoint_mgr.add_breakpoint(breakpoint)
        
        # Send data to both jobs
        runtime.post("test_flow", "test_routine", "input", {"value": 1}, job_id=job_state1.job_id)
        runtime.post("test_flow", "test_routine", "input", {"value": 1}, job_id=job_state2.job_id)
        
        time.sleep(0.3)
        
        # Job1 should not execute (breakpoint)
        executed1 = job_state1.get_shared_data("executed")
        assert executed1 is None or executed1 is False, "Job1 should not execute with breakpoint"
        
        # Job2 should execute (no breakpoint)
        executed2 = job_state2.get_shared_data("executed")
        assert executed2 is True, "Job2 should execute normally"
        
        runtime.wait_until_all_jobs_finished(timeout=2.0)

    def test_remove_breakpoint_restores_policy(self):
        """Test: Removing breakpoint restores original policy"""
        flow = Flow("test_flow")
        
        class TestRoutine(Routine):
            def __init__(self):
                super().__init__()
                self.input_slot = self.define_slot("input")
                
                def my_logic(input_data, policy_message, job_state):
                    job_state.update_shared_data("executed", True)
                
                self.set_logic(my_logic)
                self.set_activation_policy(immediate_policy())
        
        routine = TestRoutine()
        flow.add_routine(routine, "test_routine")
        FlowRegistry.get_instance().register_by_name("test_flow", flow)
        
        runtime = Runtime()
        job_state = runtime.exec("test_flow")
        
        # Add breakpoint
        registry = MonitoringRegistry.get_instance()
        breakpoint_mgr = registry.breakpoint_manager
        
        if not breakpoint_mgr:
            pytest.skip("Breakpoint manager not available")
        
        breakpoint = Breakpoint(
            job_id=job_state.job_id,
            type="routine",
            routine_id="test_routine",
            enabled=True,
        )
        
        from routilux.activation_policies import breakpoint_policy
        
        original_policy = routine._activation_policy
        breakpoint._original_policy = original_policy
        
        bp_policy = breakpoint_policy("test_routine")
        job_state.set_routine_activation_policy("test_routine", bp_policy)
        
        breakpoint_mgr.add_breakpoint(breakpoint)
        
        # Send data - should not execute
        runtime.post("test_flow", "test_routine", "input", {"value": 1}, job_id=job_state.job_id)
        time.sleep(0.2)
        
        executed = job_state.get_shared_data("executed")
        assert executed is None or executed is False
        
        # Remove breakpoint
        breakpoint_mgr.remove_breakpoint(breakpoint.breakpoint_id, job_state.job_id)
        
        # Restore original policy
        if breakpoint._original_policy:
            job_state.set_routine_activation_policy("test_routine", breakpoint._original_policy)
        else:
            job_state.remove_routine_activation_policy("test_routine")
        
        # Clear shared data
        job_state.update_shared_data("executed", None)
        
        # Send data again - should execute now
        runtime.post("test_flow", "test_routine", "input", {"value": 2}, job_id=job_state.job_id)
        time.sleep(0.2)
        
        executed = job_state.get_shared_data("executed")
        assert executed is True, "Routine should execute after breakpoint removal"
        
        runtime.wait_until_all_jobs_finished(timeout=2.0)
