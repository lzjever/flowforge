"""
Routed stdout for capturing and routing print() output by job_id.

This module provides a way to capture stdout output from routines and
route it to separate buffers based on the current job context.
"""

from __future__ import annotations

import logging
import sys
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, TextIO

from routilux.core.context import _current_job

logger = logging.getLogger(__name__)


class RoutedStdout:
    """Route stdout output by job_id.

    This class intercepts all print()/sys.stdout.write() calls and routes
    the output to separate buffers based on the current job context.

    Features:
        - Automatic routing by job_id via contextvars
        - Support for incremental retrieval (pop_chunks)
        - Support for full history retrieval (get_buffer)
        - Concurrent job outputs are completely isolated
        - Output without job context goes to real stdout

    Example:
        >>> # Install at program startup
        >>> routed_stdout = install_routed_stdout()
        >>>
        >>> # In routine logic (job context is automatically set)
        >>> print("Processing data...")  # Output routed to current job
        >>>
        >>> # External retrieval
        >>> chunks = routed_stdout.pop_chunks("job-001")  # Incremental
        >>> buffer = routed_stdout.get_buffer("job-001")  # Full history
    """

    def __init__(
        self,
        real_stdout: TextIO | None = None,
        keep_default: bool = True,
        max_buffer_chars: int = 200_000,
        job_ttl_seconds: float = 3600.0,
        enable_auto_cleanup: bool = True,
        cleanup_interval: float = 300.0,
    ):
        """Initialize RoutedStdout.

        Args:
            real_stdout: Real stdout to use for unboud output.
                Defaults to sys.__stdout__.
            keep_default: If True, output without job binding goes to real stdout.
                If False, such output is discarded.
            max_buffer_chars: Maximum characters to keep in buffer per job.
                Older content is trimmed when exceeded.
            job_ttl_seconds: Time-to-live for job buffers in seconds (default: 1 hour).
                Jobs older than this are eligible for cleanup.
            enable_auto_cleanup: If True, automatically start cleanup thread.
            cleanup_interval: Interval between cleanup runs in seconds (default: 5 minutes).
        """
        self.real = real_stdout if real_stdout is not None else sys.__stdout__
        self.keep_default = keep_default
        self.max_buffer_chars = max_buffer_chars
        self.job_ttl_seconds = job_ttl_seconds
        self.enable_auto_cleanup = enable_auto_cleanup
        self.cleanup_interval = cleanup_interval

        self._lock = threading.RLock()
        self._queues: dict[str, deque[str]] = defaultdict(deque)
        self._buffers: dict[str, str] = defaultdict(str)
        self._job_timestamps: dict[str, datetime] = {}

        # Cleanup thread management
        self._cleanup_running = False
        self._cleanup_thread: threading.Thread | None = None
        self._cleanup_lock = threading.Lock()

        if enable_auto_cleanup:
            self._start_cleanup_thread()

    def write(self, s: str) -> int:
        """Write string to stdout.

        Routes output to appropriate job buffer based on current context.

        Args:
            s: String to write

        Returns:
            Number of characters written
        """
        if not s:
            return 0

        job = _current_job.get(None)
        job_id = job.job_id if job else None

        with self._lock:
            if job_id is None:
                # No job bound - write to real stdout if keep_default
                if self.keep_default:
                    self.real.write(s)
                    self.real.flush()
                return len(s)

            # 1) Enqueue for incremental retrieval
            self._queues[job_id].append(s)

            # 2) Maintain cumulative buffer for history retrieval
            buf = self._buffers[job_id] + s
            if len(buf) > self.max_buffer_chars:
                buf = buf[-self.max_buffer_chars :]  # Keep tail only
            self._buffers[job_id] = buf

            # 3) Update timestamp for TTL cleanup
            self._job_timestamps[job_id] = datetime.now()

        return len(s)

    def flush(self) -> None:
        """Flush output."""
        with self._lock:
            if self.keep_default:
                self.real.flush()

    @property
    def encoding(self) -> str:
        """Return encoding."""
        return getattr(self.real, "encoding", "utf-8")

    def isatty(self) -> bool:
        """Return False (not a tty)."""
        return False

    def pop_chunks(self, job_id: str) -> list[str]:
        """Pop and return incremental output chunks for a job.

        This is a consuming operation - chunks are removed after retrieval.

        Args:
            job_id: Job ID to get chunks for

        Returns:
            List of output chunks (may be empty)

        Example:
            >>> chunks = routed_stdout.pop_chunks("job-001")
            >>> new_output = "".join(chunks)
        """
        with self._lock:
            q = self._queues.get(job_id)
            if not q:
                return []
            chunks = list(q)
            q.clear()
            return chunks

    def get_buffer(self, job_id: str) -> str:
        """Get full history buffer for a job.

        This is non-consuming - buffer remains intact.

        Args:
            job_id: Job ID to get buffer for

        Returns:
            Full output buffer (may be truncated to max_buffer_chars)

        Example:
            >>> history = routed_stdout.get_buffer("job-001")
            >>> print(f"Job output so far:\\n{history}")
        """
        with self._lock:
            return self._buffers.get(job_id, "")

    def clear_job(self, job_id: str) -> None:
        """Clear all output data for a job.

        Call this when a job is completed to free memory.

        Args:
            job_id: Job ID to clear
        """
        with self._lock:
            self._queues.pop(job_id, None)
            self._buffers.pop(job_id, None)
            self._job_timestamps.pop(job_id, None)

    def list_jobs(self) -> list[str]:
        """List all job IDs with output data.

        Returns:
            List of job IDs
        """
        with self._lock:
            return list(set(self._queues.keys()) | set(self._buffers.keys()))

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about current output buffers.

        Returns:
            Dictionary with stats
        """
        with self._lock:
            return {
                "job_count": len(set(self._queues.keys()) | set(self._buffers.keys())),
                "total_queue_items": sum(len(q) for q in self._queues.values()),
                "total_buffer_chars": sum(len(b) for b in self._buffers.values()),
                "oldest_job_age_seconds": self._get_oldest_job_age(),
            }

    def _get_oldest_job_age(self) -> float | None:
        """Get age of oldest job in seconds."""
        now = datetime.now()
        oldest_age = None
        for ts in self._job_timestamps.values():
            age = (now - ts).total_seconds()
            if oldest_age is None or age > oldest_age:
                oldest_age = age
        return oldest_age

    def _start_cleanup_thread(self) -> None:
        """Start the cleanup thread if not already running."""
        with self._cleanup_lock:
            if self._cleanup_running:
                return
            self._cleanup_running = True
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop, daemon=True, name="RoutedStdoutCleanup"
            )
            self._cleanup_thread.start()
            logger.debug("Started RoutedStdout cleanup thread")

    def _cleanup_loop(self) -> None:
        """Background thread loop for cleaning up expired job buffers."""
        while self._cleanup_running:
            try:
                time.sleep(self.cleanup_interval)
                if not self._cleanup_running:
                    break
                self._cleanup_expired_jobs()
            except Exception as e:
                logger.exception(f"Error in RoutedStdout cleanup loop: {e}")
        logger.debug("RoutedStdout cleanup thread stopped")

    def _cleanup_expired_jobs(self) -> None:
        """Clean up job buffers that have exceeded TTL."""
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=self.job_ttl_seconds)
        expired_jobs = []

        with self._lock:
            for job_id, timestamp in list(self._job_timestamps.items()):
                if timestamp < cutoff_time:
                    expired_jobs.append(job_id)

            for job_id in expired_jobs:
                self._queues.pop(job_id, None)
                self._buffers.pop(job_id, None)
                self._job_timestamps.pop(job_id, None)

        if expired_jobs:
            logger.debug(f"Cleaned up {len(expired_jobs)} expired job output buffers")

    def shutdown(self, timeout: float = 5.0) -> None:
        """Gracefully shutdown the cleanup thread.

        Args:
            timeout: Maximum time to wait for cleanup thread to stop (seconds).
        """
        with self._cleanup_lock:
            if not self._cleanup_running:
                return
            self._cleanup_running = False

        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=timeout)
            if self._cleanup_thread.is_alive():
                logger.warning("RoutedStdout cleanup thread did not stop within timeout")
            else:
                logger.debug("RoutedStdout cleanup thread stopped gracefully")


# Global instance
_routed_stdout: RoutedStdout | None = None
_original_stdout: TextIO | None = None


def install_routed_stdout(
    keep_default: bool = True,
    max_buffer_chars: int = 200_000,
    job_ttl_seconds: float = 3600.0,
    enable_auto_cleanup: bool = True,
    cleanup_interval: float = 300.0,
) -> RoutedStdout:
    """Install routed stdout globally.

    Should be called early in program startup, before any routines run.

    Args:
        keep_default: If True, output without job binding goes to real stdout
        max_buffer_chars: Maximum buffer size per job
        job_ttl_seconds: Time-to-live for job buffers in seconds (default: 1 hour)
        enable_auto_cleanup: If True, automatically start cleanup thread
        cleanup_interval: Interval between cleanup runs in seconds (default: 5 minutes)

    Returns:
        RoutedStdout instance

    Example:
        >>> # At program entry point
        >>> from routilux.core import install_routed_stdout
        >>> install_routed_stdout()
        >>>
        >>> # Now all print() calls in routines are captured by job
    """
    global _routed_stdout, _original_stdout
    if _routed_stdout is None:
        _original_stdout = sys.stdout
        _routed_stdout = RoutedStdout(
            keep_default=keep_default,
            max_buffer_chars=max_buffer_chars,
            job_ttl_seconds=job_ttl_seconds,
            enable_auto_cleanup=enable_auto_cleanup,
            cleanup_interval=cleanup_interval,
        )
        sys.stdout = _routed_stdout
    return _routed_stdout


def uninstall_routed_stdout() -> None:
    """Uninstall routed stdout and restore original.

    Shuts down the cleanup thread gracefully before uninstalling.

    Example:
        >>> uninstall_routed_stdout()
        >>> # sys.stdout is now restored to original
    """
    global _routed_stdout, _original_stdout
    if _routed_stdout is not None:
        _routed_stdout.shutdown()
    if _original_stdout is not None:
        sys.stdout = _original_stdout
        _routed_stdout = None
        _original_stdout = None


def get_routed_stdout() -> RoutedStdout | None:
    """Get the global RoutedStdout instance.

    Returns:
        RoutedStdout instance if installed, None otherwise
    """
    return _routed_stdout


def get_job_output(job_id: str, incremental: bool = True) -> str:
    """Get output for a specific job.

    Convenience function for retrieving job output.

    Args:
        job_id: Job ID to get output for
        incremental: If True, returns and clears incremental chunks.
            If False, returns full history buffer.

    Returns:
        Output string (may be empty)

    Example:
        >>> # Get incremental output (new since last call)
        >>> new_output = get_job_output("job-001", incremental=True)
        >>>
        >>> # Get full history
        >>> full_output = get_job_output("job-001", incremental=False)
    """
    if _routed_stdout is None:
        return ""

    if incremental:
        chunks = _routed_stdout.pop_chunks(job_id)
        return "".join(chunks)
    else:
        return _routed_stdout.get_buffer(job_id)


def clear_job_output(job_id: str) -> None:
    """Clear output data for a job.

    Args:
        job_id: Job ID to clear
    """
    if _routed_stdout is not None:
        _routed_stdout.clear_job(job_id)
