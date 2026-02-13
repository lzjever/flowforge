"""
Batcher routine for collecting data into batches.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from routilux.core import Routine


class Batcher(Routine):
    """Routine for collecting data into batches before processing.

    This routine accumulates data until either:
    - A specified batch size is reached
    - A timeout expires
    - Explicit flush is triggered
    - Maximum batch size limit is reached

    Useful for optimizing I/O operations, bulk processing, and rate limiting.

    Configuration Options:
        batch_size: Number of items to collect before emitting (default: 100)
        batch_timeout: Maximum time to wait in seconds (default: 5.0)
        flush_on_shutdown: Emit remaining items on shutdown (default: True)
        max_batches: Maximum batches to keep in memory (default: 10)
        emit_empty: Whether to emit empty batches on timeout (default: False)
        max_batch_size: Hard limit on batch size to prevent OOM (default: 10000, 0 = unlimited)

    Examples:
        Basic batching:

        >>> batcher = Batcher()
        >>> batcher.set_config(batch_size=50, batch_timeout=10.0)

        Small frequent batches:

        >>> batcher = Batcher()
        >>> batcher.set_config(batch_size=10, batch_timeout=1.0)

        Large batches for bulk operations:

        >>> batcher = Batcher()
        >>> batcher.set_config(
        ...     batch_size=1000,
        ...     batch_timeout=60.0,
        ...     flush_on_shutdown=True
        ... )
    """

    def __init__(self) -> None:
        """Initialize Batcher routine."""
        super().__init__()

        # Set default configuration
        self.set_config(
            batch_size=100,  # Items per batch
            batch_timeout=5.0,  # Max wait time
            flush_on_shutdown=True,  # Emit remaining on shutdown
            max_batches=10,  # Max batches in memory
            emit_empty=False,  # Emit empty batches
            max_batch_size=10000,  # Hard limit on batch size (0 = unlimited)
        )

        # Define input slot
        self.add_slot("input")

        # Define output events
        self.add_event("batch", ["items", "count", "batch_number"])
        self.add_event("timeout", ["items", "count"])
        self.add_event("error", ["error"])

        # Internal state
        self._batch: list[Any] = []
        self._lock = threading.Lock()
        self._first_item_time: float | None = None
        self._batch_number = 0

        # Set up activation policy and logic
        self.set_activation_policy(self._activation_policy)
        self.set_logic(self._run_logic)

    def _activation_policy(self, slots: dict, worker_state: Any) -> tuple[bool, dict, str]:
        """Check if batch is ready or timeout has occurred."""
        batch_size = self.get_config("batch_size", 100)
        batch_timeout = self.get_config("batch_timeout", 5.0)
        max_batch_size = self.get_config("max_batch_size", 10000)

        slot = slots.get("input")
        if slot is None:
            return False, {}, "no_slot"

        with self._lock:
            # Collect new data
            new_items = slot.consume_all_new()
            if new_items:
                self._batch.extend(new_items)
                if self._first_item_time is None:
                    self._first_item_time = time.time()

            # Check for hard limit first (prevents OOM)
            if max_batch_size > 0 and len(self._batch) >= max_batch_size:
                return True, {"_trigger": "max_limit"}, "max_batch_size_reached"

            # Check if batch is full
            if len(self._batch) >= batch_size:
                return True, {"_trigger": "size"}, "batch_full"

            # Check timeout
            if self._first_item_time is not None:
                elapsed = time.time() - self._first_item_time
                if elapsed >= batch_timeout:
                    return True, {"_trigger": "timeout"}, "timeout"

            return False, {}, "collecting"

    def _run_logic(self, **kwargs: Any) -> None:
        """Emit the current batch."""
        emit_empty = self.get_config("emit_empty", False)

        with self._lock:
            if not self._batch and not emit_empty:
                return

            items = self._batch.copy()
            count = len(items)
            trigger = kwargs.get("_trigger", "unknown")

            # Increment batch number
            self._batch_number += 1

            # Emit based on trigger
            if trigger == "timeout":
                self.emit("timeout", items=items, count=count)
            else:
                self.emit(
                    "batch",
                    items=items,
                    count=count,
                    batch_number=self._batch_number,
                )

            # Reset batch
            self._batch = []
            self._first_item_time = None

    def flush(self) -> None:
        """Force emit the current batch regardless of size.

        This method can be called externally to trigger an immediate emission.
        """
        with self._lock:
            if self._batch:
                items = self._batch.copy()
                count = len(items)
                self._batch_number += 1
                self.emit("batch", items=items, count=count, batch_number=self._batch_number)
                self._batch = []
                self._first_item_time = None

    def get_pending_count(self) -> int:
        """Get the number of items waiting in the current batch.

        Returns:
            Number of pending items
        """
        with self._lock:
            return len(self._batch)

    def get_batch_number(self) -> int:
        """Get the current batch number.

        Returns:
            Current batch number (number of batches emitted)
        """
        return self._batch_number
