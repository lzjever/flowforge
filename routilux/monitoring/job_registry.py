"""
Global job registry for API discovery.

This registry tracks all JobState instances created in the system,
allowing the API to discover jobs started outside the API.
Uses weak references to avoid preventing garbage collection.
"""

import logging
import threading
import time
import weakref
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from threading import RLock as LockType
else:
    LockType = object  # type: ignore

if TYPE_CHECKING:
    from routilux.job_state import JobState

logger = logging.getLogger(__name__)


class JobRegistry:
    """Global registry for JobState instances.

    Thread-safe singleton that uses weak references to track JobState instances.
    Maintains flow_id to job_id mapping for efficient querying.
    """

    _instance: Optional["JobRegistry"] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize registry (private - use get_instance())."""
        self._jobs: Dict[str, weakref.ref] = {}
        self._flow_jobs: Dict[str, List[str]] = {}  # flow_id -> [job_id, ...]
        self._lock: threading.RLock = threading.RLock()
        # Critical fix: Use try-lock to prevent deadlock in GC callback
        self._gc_cleanup_lock: threading.Lock = threading.Lock()
        # Queue for cleanup operations to avoid GC callback locking
        self._cleanup_queue: List[str] = []
        self._cleanup_queue_lock: threading.Lock = threading.Lock()

        # Completed jobs tracking for automatic cleanup
        self._completed_jobs: Dict[str, datetime] = {}  # job_id -> completed_at
        self._cleanup_interval: float = 600.0  # 10 minutes in seconds
        self._cleanup_thread: Optional[threading.Thread] = None
        self._cleanup_running: bool = False
        self._cleanup_thread_lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "JobRegistry":
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register(self, job_state: "JobState") -> None:
        """Register a job state instance.

        Args:
            job_state: JobState instance to register.
        """
        if not hasattr(job_state, "job_id") or not hasattr(job_state, "flow_id"):
            raise TypeError("job_state must be a JobState instance with job_id and flow_id")

        with self._lock:

            def cleanup_callback(ref):
                """Callback when job is garbage collected.

                Critical fix: Use non-blocking cleanup to prevent deadlock
                when garbage collector runs in a different thread.
                """
                # Find job_id for this ref without holding main lock
                job_id = None
                # Safe to access _jobs without lock since we're just reading
                # and GC won't modify it during callback
                for jid, r in list(self._jobs.items()):
                    if r is ref:
                        job_id = jid
                        break

                if job_id:
                    # Add to cleanup queue instead of immediately removing
                    # This avoids holding locks during GC callback
                    with self._cleanup_queue_lock:
                        self._cleanup_queue.append(job_id)

                    # Process cleanup queue if possible (non-blocking)
                    self._process_cleanup_queue()

            self._jobs[job_state.job_id] = weakref.ref(job_state, cleanup_callback)

            # Update flow_jobs mapping
            flow_id = job_state.flow_id
            if flow_id not in self._flow_jobs:
                self._flow_jobs[flow_id] = []
            self._flow_jobs[flow_id].append(job_state.job_id)

            # Start cleanup thread if not already running
            self._start_cleanup_thread()

    def _process_cleanup_queue(self) -> None:
        """Process queued cleanup operations.

        Critical fix: This method is called from GC callback and other methods
        to clean up dead jobs. Uses try-lock to avoid blocking GC thread.
        """
        # Try to acquire lock without blocking
        if self._gc_cleanup_lock.acquire(blocking=False):
            try:
                with self._cleanup_queue_lock:
                    job_ids_to_clean = self._cleanup_queue.copy()
                    self._cleanup_queue.clear()

                with self._lock:
                    for job_id in job_ids_to_clean:
                        self._jobs.pop(job_id, None)
                        # Clean up flow_jobs mapping
                        for flow_id, job_list in list(self._flow_jobs.items()):
                            if job_id in job_list:
                                job_list.remove(job_id)
                                if not job_list:
                                    self._flow_jobs.pop(flow_id, None)
            finally:
                self._gc_cleanup_lock.release()
        # If lock is not available, cleanup will be done on next operation

    def get(self, job_id: str) -> Optional["JobState"]:
        """Get job by ID."""
        with self._lock:
            ref = self._jobs.get(job_id)
            if ref is None:
                return None
            job = ref()
            if job is None:
                self._jobs.pop(job_id, None)
            return job

    def get_by_flow(self, flow_id: str) -> List["JobState"]:
        """Get all jobs for a flow."""
        with self._lock:
            job_ids = self._flow_jobs.get(flow_id, [])
            jobs = []
            dead_job_ids = []

            for job_id in job_ids:
                ref = self._jobs.get(job_id)
                if ref is None:
                    dead_job_ids.append(job_id)
                    continue
                job = ref()
                if job is None:
                    dead_job_ids.append(job_id)
                    self._jobs.pop(job_id, None)
                else:
                    jobs.append(job)

            # Clean up dead references
            for job_id in dead_job_ids:
                if flow_id in self._flow_jobs:
                    try:
                        self._flow_jobs[flow_id].remove(job_id)
                    except ValueError:
                        pass
                if not self._flow_jobs.get(flow_id):
                    self._flow_jobs.pop(flow_id, None)

            return jobs

    def list_all(self) -> List["JobState"]:
        """List all registered jobs."""
        with self._lock:
            jobs = []
            dead_job_ids = []

            for job_id, ref in self._jobs.items():
                job = ref()
                if job is None:
                    dead_job_ids.append(job_id)
                else:
                    jobs.append(job)

            # Clean up
            for job_id in dead_job_ids:
                self._jobs.pop(job_id, None)
                # Also clean up flow_jobs mapping
                for flow_id, job_list in list(self._flow_jobs.items()):
                    if job_id in job_list:
                        job_list.remove(job_id)
                        if not job_list:
                            self._flow_jobs.pop(flow_id, None)

            return jobs

    def mark_completed(self, job_id: str) -> None:
        """Mark a job as completed for cleanup tracking.

        Args:
            job_id: Job identifier.
        """
        with self._lock:
            self._completed_jobs[job_id] = datetime.now()
            logger.debug(f"Marked job {job_id} as completed for cleanup tracking")

    def _start_cleanup_thread(self) -> None:
        """Start the cleanup thread if not already running."""
        with self._cleanup_thread_lock:
            if self._cleanup_running:
                return
            self._cleanup_running = True
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop, daemon=True, name="JobRegistryCleanup"
            )
            self._cleanup_thread.start()
            logger.debug("Started JobRegistry cleanup thread")

    def _cleanup_loop(self) -> None:
        """Background thread loop for cleaning up completed jobs."""
        while self._cleanup_running:
            try:
                time.sleep(self._cleanup_interval)
                self._cleanup_completed_jobs()
            except Exception as e:
                logger.exception(f"Error in cleanup loop: {e}")

    def _cleanup_completed_jobs(self) -> None:
        """Clean up completed jobs that have exceeded retention period."""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self._cleanup_interval)

        with self._lock:
            jobs_to_remove = [
                job_id
                for job_id, completed_at in self._completed_jobs.items()
                if completed_at < cutoff_time
            ]

            for job_id in jobs_to_remove:
                # Remove from registry
                self._jobs.pop(job_id, None)
                self._completed_jobs.pop(job_id, None)

                # Clean up flow_jobs mapping
                for flow_id, job_list in list(self._flow_jobs.items()):
                    if job_id in job_list:
                        job_list.remove(job_id)
                        if not job_list:
                            self._flow_jobs.pop(flow_id, None)

            if jobs_to_remove:
                logger.debug(f"Cleaned up {len(jobs_to_remove)} completed jobs from registry")

    def clear(self) -> None:
        """Clear all registered jobs (for testing only)."""
        with self._lock:
            self._jobs.clear()
            self._flow_jobs.clear()
            self._completed_jobs.clear()

        # Stop cleanup thread
        with self._cleanup_thread_lock:
            self._cleanup_running = False