"""
Aggregator routine for collecting and combining data from multiple sources.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from routilux.core import Routine


class Aggregator(Routine):
    """Routine for aggregating data from multiple input slots.

    This routine waits for data from multiple slots and combines them
    before emitting the aggregated result. Useful for gathering data
    from parallel processing branches.

    Configuration Options:
        slots: List of slot names to aggregate
        mode: Aggregation mode:
            - "all": Wait for all slots to have data
            - "any": Emit when any slot has data
            - "n_of_m": Wait for N of M slots (use threshold config)
        threshold: For "n_of_m" mode, minimum number of slots (default: len(slots))
        timeout: Maximum wait time in seconds (default: 30.0)
        merge_strategy: How to combine data:
            - "dict": Combine as dict keyed by slot name
            - "list": Combine as list of values
            - "flatten": Flatten all lists into one
            - callable: Custom function to merge data

    Examples:
        Wait for all inputs:

        >>> aggregator = Aggregator()
        >>> aggregator.set_config(
        ...     slots=["user_data", "order_data", "inventory_data"],
        ...     mode="all",
        ...     merge_strategy="dict"
        ... )

        Wait for any input:

        >>> aggregator = Aggregator()
        >>> aggregator.set_config(
        ...     slots=["cache", "database"],
        ...     mode="any"  # First to respond wins
        ... )

        Custom merge strategy:

        >>> def custom_merge(data):
        ...     return {
        ...         "combined": data["a"] + data["b"],
        ...         "timestamp": time.time()
        ...     }
        >>> aggregator.set_config(
        ...     slots=["a", "b"],
        ...     merge_strategy=custom_merge
        ... )
    """

    def __init__(self) -> None:
        """Initialize Aggregator routine."""
        super().__init__()

        # Set default configuration
        self.set_config(
            slots=[],  # Slot names to aggregate
            mode="all",  # "all", "any", "n_of_m"
            threshold=None,  # For n_of_m mode
            timeout=30.0,  # Max wait time
            merge_strategy="dict",  # How to combine data
        )

        # Internal state (per-worker)
        self._pending_data: dict[str, list[Any]] = {}
        self._lock = threading.Lock()
        self._first_data_time: float | None = None

        # Output events
        self.add_event("aggregated", ["data", "sources"])
        self.add_event("timeout", ["partial_data", "missing_slots"])
        self.add_event("error", ["error", "slot"])

        # Set activation policy and logic
        self.set_activation_policy(self._activation_policy)
        self.set_logic(self._run_logic)

    def setup_slots(self, slot_names: list[str]) -> None:
        """Set up the input slots for aggregation.

        Args:
            slot_names: List of slot names to create
        """
        for name in slot_names:
            self.add_slot(name)
        self.set_config(slots=slot_names)

    def _activation_policy(self, slots: dict, worker_state: Any) -> tuple[bool, dict, str]:
        """Check if we should activate based on aggregation mode."""
        config_slots = self.get_config("slots", [])
        mode = self.get_config("mode", "all")
        threshold = self.get_config("threshold")

        with self._lock:
            # Collect new data from each slot
            for slot_name in config_slots:
                slot = slots.get(slot_name)
                if slot and len(slot.new_data) > 0:
                    if slot_name not in self._pending_data:
                        self._pending_data[slot_name] = []
                    self._pending_data[slot_name].extend(slot.consume_all_new())

                    if self._first_data_time is None:
                        self._first_data_time = time.time()

            # Check timeout
            timeout = self.get_config("timeout", 30.0)
            if self._first_data_time is not None:
                elapsed = time.time() - self._first_data_time
                if elapsed >= timeout:
                    # Timeout - emit partial data
                    return True, {"_timeout": True}, "timeout"

            # Check if ready based on mode
            ready_slots = [
                s for s in config_slots if s in self._pending_data and self._pending_data[s]
            ]

            if mode == "all":
                if len(ready_slots) == len(config_slots):
                    return True, {}, "all_ready"
            elif mode == "any":
                if ready_slots:
                    return True, {}, "any_ready"
            elif mode == "n_of_m":
                n = threshold or len(config_slots)
                if len(ready_slots) >= n:
                    return True, {}, "threshold_reached"

            return False, {}, "waiting"

    def _run_logic(self, **kwargs: Any) -> None:
        """Execute the aggregation logic."""
        config_slots = self.get_config("slots", [])
        merge_strategy = self.get_config("merge_strategy", "dict")

        # Check for timeout
        if kwargs.get("_timeout"):
            missing = [s for s in config_slots if s not in self._pending_data]
            self.emit(
                "timeout",
                partial_data=dict(self._pending_data),
                missing_slots=missing,
            )
            self._reset_state()
            return

        # Merge data based on strategy
        try:
            merged = self._merge_data(self._pending_data, merge_strategy)
            sources = list(self._pending_data.keys())
            self.emit("aggregated", data=merged, sources=sources)
        except Exception as e:
            self.emit("error", error=str(e), slot="aggregator")
        finally:
            self._reset_state()

    def _merge_data(self, data: dict[str, list[Any]], strategy: Any) -> Any:
        """Merge data from multiple slots.

        Args:
            data: Dict of slot_name -> list of data items
            strategy: Merge strategy

        Returns:
            Merged data
        """
        if callable(strategy):
            # Custom merge function
            return strategy(data)

        if strategy == "dict":
            # Return dict with slot names as keys
            result = {}
            for slot_name, items in data.items():
                if len(items) == 1:
                    result[slot_name] = items[0]
                else:
                    result[slot_name] = items
            return result

        elif strategy == "list":
            # Return flat list of all items
            result = []
            for items in data.values():
                result.extend(items)
            return result

        elif strategy == "flatten":
            # Flatten nested structures
            result = []
            for items in data.values():
                for item in items:
                    if isinstance(item, (list, tuple)):
                        result.extend(item)
                    else:
                        result.append(item)
            return result

        else:
            # Default to dict strategy
            return {k: v for k, v in data.items() if v}

    def _reset_state(self) -> None:
        """Reset internal state after emission."""
        with self._lock:
            self._pending_data = {}
            self._first_data_time = None
