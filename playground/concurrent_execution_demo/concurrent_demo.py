"""
Concurrent execution demonstration for routilux.

This demo shows:
1. Complex workflow with multiple routines
2. Concurrent execution of 4 jobs simultaneously
3. Thread pool management with max_workers < 4
4. Detailed monitoring and logging of all job states
5. Data and timestamp tracking across all routines
"""

import time
import threading
from datetime import datetime
from typing import List, Dict, Any
from routilux import Flow
from routilux.core import WorkerState
from playground.concurrent_execution_demo.data_generator_routines import (
    DataSourceRoutine,
    DataProcessorRoutine,
    DataValidatorRoutine,
    DataAggregatorRoutine,
    DataReporterRoutine,
)


class ConcurrentExecutionMonitor:
    """Monitor for tracking concurrent execution of multiple jobs."""
    
    def __init__(self):
        """Initialize monitor."""
        self.job_states: Dict[str, JobState] = {}
        self.lock = threading.Lock()
        self.start_time = time.time()
    
    def register_job(self, job_id: str, job_state: JobState):
        """Register a job for monitoring.
        
        Args:
            job_id: Job identifier.
            job_state: JobState object.
        """
        with self.lock:
            self.job_states[job_id] = job_state
    
    def get_all_job_states(self) -> Dict[str, JobState]:
        """Get all registered job states.
        
        Returns:
            Dictionary of job_id -> JobState.
        """
        with self.lock:
            return self.job_states.copy()
    
    def print_status(self):
        """Print current status of all jobs."""
        with self.lock:
            elapsed = time.time() - self.start_time
            print(f"\n{'='*80}")
            print(f"[{elapsed:.3f}s] Current Status of All Jobs")
            print(f"{'='*80}")
            
            for job_id, job_state in self.job_states.items():
                status = job_state.status
                history_count = len(job_state.execution_history)
                log_count = len(job_state.shared_log)
                
                print(f"  Job {job_id[:8]}... | Status: {status:10s} | "
                      f"History: {history_count:3d} | Log: {log_count:3d}")
    
    def print_timeline(self):
        """Print timeline visualization showing routine execution intervals."""
        with self.lock:
            print(f"\n{'='*80}")
            print("Timeline Visualization - Routine Execution Intervals")
            print(f"{'='*80}")
            print("Each line shows a routine's execution time. Overlapping lines indicate concurrent execution.")
            print()
            
            # Routine display names
            routine_names = {
                "data_source": "Source",
                "data_processor": "Processor",
                "data_validator": "Validator",
                "data_aggregator": "Aggregator",
                "data_reporter": "Reporter",
            }
            
            # Extract timing data from all jobs
            all_timings = {}  # job_id -> routine_id -> (start_time, end_time, relative_start)
            
            # Find the earliest start time across all jobs
            earliest_time = None
            for job_id, job_state in self.job_states.items():
                if job_state.execution_history:
                    first_record = job_state.execution_history[0]
                    record_time = first_record.timestamp
                    if isinstance(record_time, str):
                        record_time = datetime.fromisoformat(record_time.replace('Z', '+00:00'))
                    if earliest_time is None or record_time < earliest_time:
                        earliest_time = record_time
            
            if earliest_time is None:
                print("  No execution history available")
                return
            
            # Process each job's execution history
            for job_id, job_state in sorted(self.job_states.items()):
                all_timings[job_id] = {}
                
                if not job_state.execution_history:
                    continue
                
                # Get first record time as reference for this job
                first_record = job_state.execution_history[0]
                first_time = first_record.timestamp
                if isinstance(first_time, str):
                    first_time = datetime.fromisoformat(first_time.replace('Z', '+00:00'))
                
                # Track routine execution times
                routine_starts = {}  # routine_id -> start_time (relative to first_time)
                routine_ends = {}    # routine_id -> end_time (relative to first_time)
                
                for record in job_state.execution_history:
                    record_time = record.timestamp
                    if isinstance(record_time, str):
                        record_time = datetime.fromisoformat(record_time.replace('Z', '+00:00'))
                    
                    relative_time = (record_time - first_time).total_seconds()
                    
                    if record.event_name == "start":
                        routine_starts[record.routine_id] = relative_time
                    elif record.event_name == "output":
                        routine_ends[record.routine_id] = relative_time
                
                # Calculate start and end for each routine
                routine_order = ["data_source", "data_processor", "data_validator", "data_aggregator", "data_reporter"]
                previous_end = 0.0
                
                for routine_id in routine_order:
                    if routine_id in routine_ends:
                        start_time = routine_starts.get(routine_id, previous_end)
                        end_time = routine_ends[routine_id]
                        # Calculate absolute start time relative to earliest_time
                        absolute_start = (first_time - earliest_time).total_seconds() + start_time
                        all_timings[job_id][routine_id] = (start_time, end_time, absolute_start)
                        previous_end = end_time
            
            # Find time range for visualization
            all_absolute_times = []
            for job_timings in all_timings.values():
                for routine_id, (start, end, abs_start) in job_timings.items():
                    all_absolute_times.append(abs_start)
                    all_absolute_times.append(abs_start + (end - start))
            
            if not all_absolute_times:
                print("  No timing data available")
                return
            
            min_time = min(all_absolute_times)
            max_time = max(all_absolute_times)
            time_range = max_time - min_time if max_time > min_time else 1.0
            
            # Print timeline for each job
            for job_id in sorted(self.job_states.keys()):
                job_state = self.job_states[job_id]
                timings = all_timings.get(job_id, {})
                
                print(f"\n  📋 Job: {job_id[:40]}")
                print(f"  {'─'*76}")
                
                routine_order = ["data_source", "data_processor", "data_validator", "data_aggregator", "data_reporter"]
                
                for routine_id in routine_order:
                    if routine_id in timings:
                        start, end, abs_start = timings[routine_id]
                        duration = end - start
                        display_name = routine_names.get(routine_id, routine_id)
                        
                        # Calculate position in timeline (0-60 chars)
                        timeline_width = 60
                        start_pos = int(((abs_start - min_time) / time_range) * timeline_width) if time_range > 0 else 0
                        end_pos = int(((abs_start + duration - min_time) / time_range) * timeline_width) if time_range > 0 else timeline_width
                        
                        # Ensure minimum width
                        if end_pos <= start_pos:
                            end_pos = start_pos + 1
                        
                        # Create timeline bar
                        timeline_bar = [' '] * timeline_width
                        for i in range(start_pos, min(end_pos, timeline_width)):
                            timeline_bar[i] = '█'
                        
                        # Format output with absolute times
                        abs_end = abs_start + duration
                        print(f"    {display_name:12s} [abs: {abs_start:6.3f}s → {abs_end:6.3f}s] "
                              f"│{''.join(timeline_bar)}│ ⏱️ {duration:.3f}s")
                    else:
                        display_name = routine_names.get(routine_id, routine_id)
                        print(f"    {display_name:12s} (not executed)")
            
            # Print time scale
            print(f"\n  Time Scale: {min_time:.3f}s {'─'*60} {max_time:.3f}s")
            print(f"  Total Duration: {max_time - min_time:.3f}s")
            
            # Print concurrent execution summary
            print(f"\n  📊 Concurrent Execution Analysis:")
            # Count overlapping routines at different time points
            time_points = sorted(set([t for job_timings in all_timings.values() 
                                     for routine_id, (start, end, abs_start) in job_timings.items()
                                     for t in [abs_start, abs_start + (end - start)]]))
            
            if time_points:
                max_concurrent = 0
                for t in time_points:
                    concurrent_count = sum(1 for job_timings in all_timings.values()
                                          for routine_id, (start, end, abs_start) in job_timings.items()
                                          if abs_start <= t <= abs_start + (end - start))
                    max_concurrent = max(max_concurrent, concurrent_count)
                
                print(f"      Maximum concurrent routines: {max_concurrent}")
                print(f"      Thread pool limit (max_workers): 2")
                if max_concurrent <= 2:
                    print(f"      ✅ Concurrent execution is properly limited by thread pool")
                else:
                    print(f"      ⚠️  More routines than max_workers (may be due to timing precision)")
            
            print(f"\n  💡 Note: Overlapping timeline bars indicate concurrent execution.")
            print(f"      All times are absolute (relative to earliest job start).")
    
    def print_detailed_report(self):
        """Print detailed report for all jobs."""
        with self.lock:
            elapsed = time.time() - self.start_time
            print(f"\n{'='*80}")
            print(f"Detailed Execution Report (Total Time: {elapsed:.3f}s)")
            print(f"{'='*80}")
            
            for job_id, job_state in self.job_states.items():
                print(f"\n{'─'*80}")
                print(f"Job ID: {job_id}")
                print(f"Flow ID: {job_state.flow_id}")
                print(f"Status: {job_state.status}")
                print(f"Execution History: {len(job_state.execution_history)} records")
                print(f"Shared Log: {len(job_state.shared_log)} entries")
                
                # Print execution history
                print(f"\n  Execution History:")
                for i, record in enumerate(job_state.execution_history, 1):
                    print(f"    {i:2d}. [{record.timestamp}] {record.routine_id}.{record.event_name}")
                
                # Print shared data with timestamps
                print(f"\n  Shared Data (with timestamps):")
                for key, value in job_state.shared_data.items():
                    if isinstance(value, dict) and "timestamp" in str(value) or "generated_at" in str(value) or "processed_at" in str(value) or "validated_at" in str(value) or "aggregated_at" in str(value):
                        if isinstance(value, dict):
                            # Extract timestamp if available
                            timestamp = value.get("generated_at") or value.get("processed_at") or value.get("validated_at") or value.get("aggregated_at") or "N/A"
                            print(f"    {key:30s}: timestamp={timestamp}")
                        else:
                            print(f"    {key:30s}: {value}")
                    else:
                        print(f"    {key:30s}: {value}")
                
                # Print routine states
                print(f"\n  Routine States:")
                for routine_id, state in job_state.routine_states.items():
                    status = state.get("status", "unknown")
                    timestamp = state.get("timestamp", "N/A")
                    print(f"    {routine_id:20s}: status={status:10s}, timestamp={timestamp}")
                
                # Print final report if available
                if "final_report" in job_state.shared_data:
                    report = job_state.shared_data["final_report"]
                    print(f"\n  Final Report:")
                    print(f"    Report ID: {report.get('report_id', 'N/A')}")
                    print(f"    Generated At: {report.get('generated_at', 'N/A')}")
                    print(f"    Summary: {report.get('summary', {})}")


def create_complex_workflow(flow_id: str = None, max_workers: int = 2) -> Flow:
    """Create a complex workflow with multiple routines.
    
    Workflow Structure:
        DataSource -> DataProcessor -> DataValidator -> DataAggregator -> DataReporter
    
    Args:
        flow_id: Flow identifier.
        max_workers: Maximum number of worker threads.
    
    Returns:
        Flow object.
    """
    flow = Flow(
        flow_id=flow_id or f"complex_workflow_{int(time.time())}",
        execution_strategy="concurrent",
        max_workers=max_workers,
    )
    
    # Create routines
    source = DataSourceRoutine(delay=0.1)
    processor = DataProcessorRoutine(delay=0.15)
    validator = DataValidatorRoutine(delay=0.12)
    aggregator = DataAggregatorRoutine(delay=0.18)
    reporter = DataReporterRoutine(delay=0.1)
    
    # Add routines to flow
    source_id = flow.add_routine(source, "data_source")
    processor_id = flow.add_routine(processor, "data_processor")
    validator_id = flow.add_routine(validator, "data_validator")
    aggregator_id = flow.add_routine(aggregator, "data_aggregator")
    reporter_id = flow.add_routine(reporter, "data_reporter")
    
    # Connect routines
    flow.connect(source_id, "output", processor_id, "input")
    flow.connect(processor_id, "output", validator_id, "input")
    flow.connect(validator_id, "output", aggregator_id, "input")
    flow.connect(aggregator_id, "output", reporter_id, "input")
    
    return flow, source_id


def execute_job(flow: Flow, entry_id: str, job_id: str, monitor: ConcurrentExecutionMonitor):
    """Execute a single job.
    
    Args:
        flow: Flow object.
        entry_id: Entry routine ID.
        job_id: Job identifier.
        monitor: Execution monitor.
    """
    print(f"[{time.time() - monitor.start_time:.3f}s] Starting job {job_id[:8]}...")
    
    try:
        job_state = flow.execute(entry_id, entry_params={"job_id": job_id})
        monitor.register_job(job_id, job_state)
        
        # Wait for completion using proper method
        start_time = time.time()
        completed = JobState.wait_for_completion(flow, job_state, timeout=30.0)
        
        elapsed = time.time() - start_time
        if completed:
            # Ensure status is set to completed if all tasks are done
            if job_state.status == "running":
                # Check if all tasks are actually complete
                queue_empty = flow._task_queue.empty()
                with flow._execution_lock:
                    active_tasks = [f for f in flow._active_tasks if not f.done()]
                    if queue_empty and len(active_tasks) == 0:
                        job_state.status = "completed"
            
            print(f"[{time.time() - monitor.start_time:.3f}s] Job {job_id[:8]}... completed with status: {job_state.status} (took {elapsed:.3f}s)")
        else:
            print(f"[{time.time() - monitor.start_time:.3f}s] Job {job_id[:8]}... timed out after {elapsed:.3f}s (status: {job_state.status})")
        
    except Exception as e:
        print(f"[{time.time() - monitor.start_time:.3f}s] Job {job_id[:8]}... failed with error: {e}")


def main():
    """Main demonstration function."""
    print("="*80)
    print("Concurrent Execution Demonstration")
    print("="*80)
    print("\nThis demo shows:")
    print("  1. Complex workflow with 5 routines (Source -> Processor -> Validator -> Aggregator -> Reporter)")
    print("  2. Concurrent execution of 4 jobs simultaneously")
    print("  3. Thread pool management with max_workers=2 (limiting concurrent routines)")
    print("  4. Detailed monitoring and logging of all job states")
    print("  5. Data and timestamp tracking across all routines")
    print()
    
    # Configuration
    num_jobs = 4
    max_workers = 2  # Less than num_jobs to demonstrate thread pool limiting
    
    print(f"Configuration:")
    print(f"  Number of concurrent jobs: {num_jobs}")
    print(f"  Max workers (thread pool size): {max_workers}")
    print(f"  Expected behavior: At most {max_workers} routines executing simultaneously")
    print()
    
    # Create workflow
    print("Creating complex workflow...")
    flow, entry_id = create_complex_workflow(max_workers=max_workers)
    print(f"  Flow ID: {flow.flow_id}")
    print(f"  Routines: {list(flow.routines.keys())}")
    print(f"  Execution Strategy: {flow.execution_strategy}")
    print(f"  Max Workers: {flow.max_workers}")
    print()
    
    # Create monitor
    monitor = ConcurrentExecutionMonitor()
    
    # Start all jobs concurrently
    print("="*80)
    print("Starting concurrent execution of 4 jobs...")
    print("="*80)
    
    threads = []
    for i in range(num_jobs):
        job_id = f"job_{i+1}_{int(time.time())}"
        thread = threading.Thread(
            target=execute_job,
            args=(flow, entry_id, job_id, monitor),
            daemon=True
        )
        threads.append(thread)
        thread.start()
        time.sleep(0.05)  # Small delay to stagger starts
    
    # Monitor execution
    print("\nMonitoring execution...")
    print("(You should see at most 2 routines executing simultaneously due to max_workers=2)")
    print()
    
    # Periodic status updates
    check_interval = 0.5
    max_monitor_time = 30.0
    start_time = time.time()
    
    while time.time() - start_time < max_monitor_time:
        all_completed = True
        with monitor.lock:
            for job_state in monitor.job_states.values():
                if job_state.status not in ["completed", "failed", "cancelled"]:
                    all_completed = False
                    break
        
        if all_completed and len(monitor.job_states) == num_jobs:
            break
        
        time.sleep(check_interval)
        monitor.print_status()
    
    # Wait for all threads
    print("\nWaiting for all threads to complete...")
    for thread in threads:
        thread.join(timeout=5.0)
    
    # Print timeline visualization
    monitor.print_timeline()
    
    # Final detailed report
    monitor.print_detailed_report()
    
    # Summary
    print(f"\n{'='*80}")
    print("Execution Summary")
    print(f"{'='*80}")
    
    with monitor.lock:
        completed = sum(1 for js in monitor.job_states.values() if js.status == "completed")
        failed = sum(1 for js in monitor.job_states.values() if js.status == "failed")
        total_time = time.time() - monitor.start_time
        
        print(f"Total Jobs: {len(monitor.job_states)}")
        print(f"Completed: {completed}")
        print(f"Failed: {failed}")
        print(f"Total Execution Time: {total_time:.3f}s")
        print(f"Average Time per Job: {total_time / len(monitor.job_states):.3f}s")
        print()
        print("✅ Demonstration completed!")


if __name__ == "__main__":
    main()

