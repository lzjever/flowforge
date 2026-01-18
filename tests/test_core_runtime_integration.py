"""Integration tests for Runtime - event routing and multi-routine flows."""

import time

import pytest
from routilux.core import Flow, JobStatus, Runtime, Routine


class TestEventRouting:
    """Test event routing between routines."""

    def test_simple_event_routing(self):
        """Test routing an event from one routine to another."""
        received_data = []
        
        class SourceRoutine(Routine):
            def setup(self):
                self.add_slot("input")
                self.add_event("output")
            
            def logic(self, input_data, **kwargs):
                self.emit("output", data=input_data)
                return {}
        
        class TargetRoutine(Routine):
            def setup(self):
                self.add_slot("input")
            
            def logic(self, input_data, **kwargs):
                received_data.append(input_data)
                return {}
        
        flow = Flow()
        source = SourceRoutine()
        source.setup()
        target = TargetRoutine()
        target.setup()
        
        source_id = flow.add_routine(source, "source")
        target_id = flow.add_routine(target, "target")
        flow.connect(source_id, "output", target_id, "input")
        
        runtime = Runtime()
        runtime.exec("test_flow", flow)
        
        runtime.post("test_flow", "source", "input", {"value": 42})
        
        # Wait for event routing
        time.sleep(0.2)
        
        assert len(received_data) == 1
        assert received_data[0]["value"] == 42

    def test_multi_hop_event_routing(self):
        """Test routing events through multiple routines."""
        results = []
        
        class R1(Routine):
            def setup(self):
                self.add_slot("input")
                self.add_event("output")
            
            def logic(self, input_data, **kwargs):
                self.emit("output", data={"step": 1, **input_data})
                return {}
        
        class R2(Routine):
            def setup(self):
                self.add_slot("input")
                self.add_event("output")
            
            def logic(self, input_data, **kwargs):
                self.emit("output", data={"step": 2, **input_data})
                return {}
        
        class R3(Routine):
            def setup(self):
                self.add_slot("input")
            
            def logic(self, input_data, **kwargs):
                results.append(input_data)
                return {}
        
        flow = Flow()
        r1 = R1()
        r1.setup()
        r2 = R2()
        r2.setup()
        r3 = R3()
        r3.setup()
        
        r1_id = flow.add_routine(r1, "r1")
        r2_id = flow.add_routine(r2, "r2")
        r3_id = flow.add_routine(r3, "r3")
        
        flow.connect(r1_id, "output", r2_id, "input")
        flow.connect(r2_id, "output", r3_id, "input")
        
        runtime = Runtime()
        runtime.exec("test_flow", flow)
        
        runtime.post("test_flow", "r1", "input", {"value": 10})
        
        time.sleep(0.3)
        
        assert len(results) == 1
        assert results[0]["step"] == 2
        assert results[0]["value"] == 10

    def test_fan_out_event_routing(self):
        """Test routing one event to multiple routines."""
        results = []
        
        class SourceRoutine(Routine):
            def setup(self):
                self.add_slot("input")
                self.add_event("output")
            
            def logic(self, input_data, **kwargs):
                self.emit("output", data=input_data)
                return {}
        
        class Target1(Routine):
            def setup(self):
                self.add_slot("input")
            
            def logic(self, input_data, **kwargs):
                results.append(("target1", input_data))
                return {}
        
        class Target2(Routine):
            def setup(self):
                self.add_slot("input")
            
            def logic(self, input_data, **kwargs):
                results.append(("target2", input_data))
                return {}
        
        flow = Flow()
        source = SourceRoutine()
        source.setup()
        target1 = Target1()
        target1.setup()
        target2 = Target2()
        target2.setup()
        
        source_id = flow.add_routine(source, "source")
        t1_id = flow.add_routine(target1, "target1")
        t2_id = flow.add_routine(target2, "target2")
        
        flow.connect(source_id, "output", t1_id, "input")
        flow.connect(source_id, "output", t2_id, "input")
        
        runtime = Runtime()
        runtime.exec("test_flow", flow)
        
        runtime.post("test_flow", "source", "input", {"value": 5})
        
        time.sleep(0.3)
        
        assert len(results) == 2
        target_names = {r[0] for r in results}
        assert target_names == {"target1", "target2"}
        assert all(r[1]["value"] == 5 for r in results)


class TestJobContextPropagation:
    """Test that JobContext propagates through routines."""

    def test_job_context_available_in_routines(self):
        """Test that JobContext is available in routine logic."""
        job_ids = []
        
        class TestRoutine(Routine):
            def setup(self):
                self.add_slot("input")
                self.add_event("output")
            
            def logic(self, input_data, **kwargs):
                from routilux.core import get_current_job
                job = get_current_job()
                if job:
                    job_ids.append(job.job_id)
                self.emit("output", data=input_data)
                return {}
        
        class TargetRoutine(Routine):
            def setup(self):
                self.add_slot("input")
            
            def logic(self, input_data, **kwargs):
                from routilux.core import get_current_job
                job = get_current_job()
                if job:
                    job_ids.append(job.job_id)
                return {}
        
        flow = Flow()
        source = TestRoutine()
        source.setup()
        target = TargetRoutine()
        target.setup()
        
        source_id = flow.add_routine(source, "source")
        target_id = flow.add_routine(target, "target")
        flow.connect(source_id, "output", target_id, "input")
        
        runtime = Runtime()
        runtime.exec("test_flow", flow)
        
        worker_state, job = runtime.post("test_flow", "source", "input", {"test": "data"})
        
        time.sleep(0.3)
        
        # Both routines should see the same job_id
        assert len(job_ids) == 2
        assert job_ids[0] == job.job_id
        assert job_ids[1] == job.job_id
