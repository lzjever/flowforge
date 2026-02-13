"""
Debouncer routine for debouncing rapid input events.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from routilux.core import Routine


class Debouncer(Routine):
    """Routine for debouncing rapid input events.

    This routine emits data only after a quiet period, useful for:
    - Search-as-you-type inputs
    - Resize events
    - Any high-frequency event that should be throttled

    Configuration Options:
        wait: Time to wait in seconds after last input (default: 0.3)
        leading: Emit on the leading edge (first call) (default: False)
        trailing: Emit on the trailing edge (after quiet period) (default: True)
        max_wait: Maximum time to wait before forcing emission (default: None)

    Examples:
        Basic debouncing:

        >>> debouncer = Debouncer()
        >>> debouncer.set_config(wait=0.5)  # Wait 500ms after last input

        With leading edge:

        >>> debouncer = Debouncer()
        >>> debouncer.set_config(wait=0.3, leading=True)
        >>> # First input emits immediately, subsequent inputs debounced

        With max wait time:

        >>> debouncer = Debouncer()
        >>> debouncer.set_config(wait=0.5, max_wait=2.0)
        >>> # Will emit after 2 seconds even with continuous input
    """

    def __init__(self) -> None:
        """Initialize Debouncer routine."""
        super().__init__()

        # Set default configuration
        self.set_config(
            wait=0.3,  # Debounce wait time
            leading=False,  # Emit on first call
            trailing=True,  # Emit after quiet period
            max_wait=None,  # Max wait before forced emission
        )

        # Define input slot
        self.add_slot("input")

        # Define output events
        self.add_event("debounced", ["data"])
        self.add_event("leading", ["data"])

        # Internal state
        self._lock = threading.Lock()
        self._last_data: Any = None
        self._last_input_time: float | None = None
        self._first_input_time: float | None = None
        self._has_leading_emitted = False
        self._pending = False

        # Set up activation policy and logic
        self.set_activation_policy(self._activation_policy)
        self.set_logic(self._run_logic)

    def _activation_policy(self, slots: dict, worker_state: Any) -> tuple[bool, dict, str]:
        """Check if debounced output should be emitted."""
        wait = self.get_config("wait", 0.3)
        leading = self.get_config("leading", False)
        max_wait = self.get_config("max_wait")

        slot = slots.get("input")
        if slot is None:
            return False, {}, "no_slot"

        current_time = time.time()

        with self._lock:
            # Collect new data
            new_items = slot.consume_all_new()
            if new_items:
                # Store the latest data
                self._last_data = new_items[-1] if len(new_items) == 1 else new_items
                self._last_input_time = current_time

                if self._first_input_time is None:
                    self._first_input_time = current_time

                # Check for leading edge emission
                if leading and not self._has_leading_emitted:
                    self._has_leading_emitted = True
                    return True, {"_type": "leading"}, "leading_edge"

                self._pending = True

            # Check if enough time has passed since last input
            if self._pending and self._last_input_time is not None:
                elapsed_since_input = current_time - self._last_input_time

                # Check max_wait
                if max_wait is not None and self._first_input_time is not None:
                    elapsed_since_first = current_time - self._first_input_time
                    if elapsed_since_first >= max_wait:
                        return True, {"_type": "max_wait"}, "max_wait_reached"

                # Check normal wait time
                if elapsed_since_input >= wait:
                    return True, {"_type": "trailing"}, "trailing_edge"

            return False, {}, "waiting"

    def _run_logic(self, **kwargs: Any) -> None:
        """Emit the debounced data."""
        emit_type = kwargs.get("_type", "trailing")

        with self._lock:
            data = self._last_data

            if emit_type == "leading":
                self.emit("leading", data=data)
            else:
                self.emit("debounced", data=data)
                # Reset state after trailing emission
                self._has_leading_emitted = False
                self._first_input_time = None
                self._pending = False

            self._last_data = None
            if emit_type != "leading":
                self._last_input_time = None

    def cancel(self) -> None:
        """Cancel any pending debounced emission."""
        with self._lock:
            self._last_data = None
            self._last_input_time = None
            self._first_input_time = None
            self._has_leading_emitted = False
            self._pending = False

    def flush(self) -> None:
        """Immediately emit pending data if any."""
        with self._lock:
            if self._last_data is not None:
                self.emit("debounced", data=self._last_data)
                self._last_data = None
                self._last_input_time = None
                self._first_input_time = None
                self._has_leading_emitted = False
                self._pending = False

    def is_pending(self) -> bool:
        """Check if there is pending data waiting to be emitted.

        Returns:
            True if there is pending data
        """
        with self._lock:
            return self._pending
