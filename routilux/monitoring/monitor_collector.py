"""
Monitor collector for execution metrics and events.

Collects execution metrics, traces, and events for monitoring and analysis.
"""

import threading
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict


@dataclass
class ExecutionEvent:
    """Execution event record.
    
    Attributes:
        event_id: Unique event identifier.
        job_id: Job ID.
        routine_id: Routine ID.
        event_type: Type of event (routine_start, routine_end, slot_call, event_emit).
        timestamp: Event timestamp.
        data: Event-specific data.
        duration: Duration in seconds (for end events).
        status: Status (for end events).
    """
    event_id: str
    job_id: str
    routine_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    duration: Optional[float] = None
    status: Optional[str] = None


@dataclass
class RoutineMetrics:
    """Metrics for a single routine.
    
    Attributes:
        routine_id: Routine identifier.
        execution_count: Number of times routine executed.
        total_duration: Total execution time in seconds.
        avg_duration: Average execution time in seconds.
        min_duration: Minimum execution time in seconds.
        max_duration: Maximum execution time in seconds.
        error_count: Number of errors.
        last_execution: Timestamp of last execution.
    """
    routine_id: str
    execution_count: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None
    error_count: int = 0
    last_execution: Optional[datetime] = None
    
    def update(self, duration: float, status: str = "completed") -> None:
        """Update metrics with new execution.
        
        Args:
            duration: Execution duration in seconds.
            status: Execution status.
        """
        self.execution_count += 1
        self.total_duration += duration
        self.avg_duration = self.total_duration / self.execution_count
        
        if self.min_duration is None or duration < self.min_duration:
            self.min_duration = duration
        if self.max_duration is None or duration > self.max_duration:
            self.max_duration = duration
        
        if status in ("failed", "error"):
            self.error_count += 1
        
        self.last_execution = datetime.now()


@dataclass
class ErrorRecord:
    """Error record.
    
    Attributes:
        error_id: Unique error identifier.
        job_id: Job ID.
        routine_id: Routine ID where error occurred.
        timestamp: Error timestamp.
        error_type: Error type (exception class name).
        error_message: Error message.
        traceback: Optional traceback.
    """
    error_id: str
    job_id: str
    routine_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    traceback: Optional[str] = None


@dataclass
class ExecutionMetrics:
    """Aggregated execution metrics.
    
    Attributes:
        job_id: Job identifier.
        flow_id: Flow identifier.
        start_time: Execution start time.
        end_time: Execution end time (None if still running).
        duration: Total duration in seconds (None if still running).
        routine_metrics: Metrics per routine.
        total_events: Total number of events.
        total_slot_calls: Total number of slot calls.
        total_event_emits: Total number of event emissions.
        errors: List of error records.
    """
    job_id: str
    flow_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    routine_metrics: Dict[str, RoutineMetrics] = field(default_factory=dict)
    total_events: int = 0
    total_slot_calls: int = 0
    total_event_emits: int = 0
    errors: List[ErrorRecord] = field(default_factory=list)


class MonitorCollector:
    """Collects execution metrics and events.
    
    Thread-safe collector that records execution events and computes metrics.
    """
    
    def __init__(self):
        """Initialize monitor collector."""
        self._metrics: Dict[str, ExecutionMetrics] = {}  # job_id -> ExecutionMetrics
        self._events: Dict[str, List[ExecutionEvent]] = {}  # job_id -> List[ExecutionEvent]
        self._routine_starts: Dict[str, Dict[str, datetime]] = {}  # job_id -> {routine_id -> start_time}
        self._lock = threading.RLock()
        self._event_counter = 0
    
    def record_flow_start(self, flow_id: str, job_id: str) -> None:
        """Record flow execution start.
        
        Args:
            flow_id: Flow identifier.
            job_id: Job identifier.
        """
        with self._lock:
            if job_id not in self._metrics:
                self._metrics[job_id] = ExecutionMetrics(
                    job_id=job_id,
                    flow_id=flow_id,
                    start_time=datetime.now(),
                )
                self._events[job_id] = []
                self._routine_starts[job_id] = {}
    
    def record_flow_end(self, job_id: str, status: str = "completed") -> None:
        """Record flow execution end.
        
        Args:
            job_id: Job identifier.
            status: Final status.
        """
        with self._lock:
            if job_id in self._metrics:
                metrics = self._metrics[job_id]
                metrics.end_time = datetime.now()
                if metrics.start_time:
                    metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
    
    def record_routine_start(self, routine_id: str, job_id: str) -> None:
        """Record routine execution start.
        
        Args:
            routine_id: Routine identifier.
            job_id: Job identifier.
        """
        with self._lock:
            if job_id not in self._routine_starts:
                self._routine_starts[job_id] = {}
            
            self._routine_starts[job_id][routine_id] = datetime.now()
            
            # Record event
            event = ExecutionEvent(
                event_id=f"event_{self._event_counter}",
                job_id=job_id,
                routine_id=routine_id,
                event_type="routine_start",
                timestamp=datetime.now(),
            )
            self._event_counter += 1
            
            if job_id not in self._events:
                self._events[job_id] = []
            self._events[job_id].append(event)
            
            if job_id in self._metrics:
                self._metrics[job_id].total_events += 1
    
    def record_routine_end(
        self,
        routine_id: str,
        job_id: str,
        status: str = "completed",
        error: Optional[Exception] = None,
    ) -> None:
        """Record routine execution end.
        
        Args:
            routine_id: Routine identifier.
            job_id: Job identifier.
            status: Execution status.
            error: Optional error that occurred.
        """
        with self._lock:
            start_time = None
            if job_id in self._routine_starts and routine_id in self._routine_starts[job_id]:
                start_time = self._routine_starts[job_id].pop(routine_id)
            
            duration = None
            if start_time:
                duration = (datetime.now() - start_time).total_seconds()
            
            # Update routine metrics
            if job_id in self._metrics:
                metrics = self._metrics[job_id]
                if routine_id not in metrics.routine_metrics:
                    metrics.routine_metrics[routine_id] = RoutineMetrics(routine_id=routine_id)
                
                routine_metrics = metrics.routine_metrics[routine_id]
                if duration is not None:
                    routine_metrics.update(duration, status)
                else:
                    routine_metrics.execution_count += 1
                    if status in ("failed", "error"):
                        routine_metrics.error_count += 1
                    routine_metrics.last_execution = datetime.now()
            
            # Record error if present
            if error and job_id in self._metrics:
                error_record = ErrorRecord(
                    error_id=f"error_{self._event_counter}",
                    job_id=job_id,
                    routine_id=routine_id,
                    timestamp=datetime.now(),
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
                self._metrics[job_id].errors.append(error_record)
            
            # Record event
            event = ExecutionEvent(
                event_id=f"event_{self._event_counter}",
                job_id=job_id,
                routine_id=routine_id,
                event_type="routine_end",
                timestamp=datetime.now(),
                duration=duration,
                status=status,
            )
            self._event_counter += 1
            
            if job_id not in self._events:
                self._events[job_id] = []
            self._events[job_id].append(event)
            
            if job_id in self._metrics:
                self._metrics[job_id].total_events += 1
    
    def record_slot_call(
        self,
        slot_name: str,
        routine_id: str,
        job_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record slot call.
        
        Args:
            slot_name: Slot name.
            routine_id: Routine identifier.
            job_id: Job identifier.
            data: Optional data passed to slot.
        """
        with self._lock:
            event = ExecutionEvent(
                event_id=f"event_{self._event_counter}",
                job_id=job_id,
                routine_id=routine_id,
                event_type="slot_call",
                timestamp=datetime.now(),
                data={"slot_name": slot_name, "data_keys": list(data.keys()) if data else []},
            )
            self._event_counter += 1
            
            if job_id not in self._events:
                self._events[job_id] = []
            self._events[job_id].append(event)
            
            if job_id in self._metrics:
                self._metrics[job_id].total_events += 1
                self._metrics[job_id].total_slot_calls += 1
    
    def record_event_emit(
        self,
        event_name: str,
        routine_id: str,
        job_id: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record event emission.
        
        Args:
            event_name: Event name.
            routine_id: Routine identifier.
            job_id: Job identifier.
            data: Optional data emitted with event.
        """
        with self._lock:
            event = ExecutionEvent(
                event_id=f"event_{self._event_counter}",
                job_id=job_id,
                routine_id=routine_id,
                event_type="event_emit",
                timestamp=datetime.now(),
                data={"event_name": event_name, "data_keys": list(data.keys()) if data else []},
            )
            self._event_counter += 1
            
            if job_id not in self._events:
                self._events[job_id] = []
            self._events[job_id].append(event)
            
            if job_id in self._metrics:
                self._metrics[job_id].total_events += 1
                self._metrics[job_id].total_event_emits += 1
    
    def get_metrics(self, job_id: str) -> Optional[ExecutionMetrics]:
        """Get execution metrics for a job.
        
        Args:
            job_id: Job identifier.
            
        Returns:
            ExecutionMetrics or None if not found.
        """
        with self._lock:
            return self._metrics.get(job_id)
    
    def get_execution_trace(self, job_id: str, limit: Optional[int] = None) -> List[ExecutionEvent]:
        """Get execution trace for a job.
        
        Args:
            job_id: Job identifier.
            limit: Optional limit on number of events to return.
            
        Returns:
            List of execution events (chronologically ordered).
        """
        with self._lock:
            events = self._events.get(job_id, [])
            if limit:
                return events[-limit:]
            return events.copy()
    
    def clear(self, job_id: str) -> None:
        """Clear all data for a job.
        
        Args:
            job_id: Job identifier.
        """
        with self._lock:
            self._metrics.pop(job_id, None)
            self._events.pop(job_id, None)
            self._routine_starts.pop(job_id, None)

