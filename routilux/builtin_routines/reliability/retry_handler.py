"""
Retry handler routine for retrying failed operations.
"""

from __future__ import annotations

import random
import threading
import time
from typing import Any, Callable

from routilux.core import Routine


class RetryHandler(Routine):
    """Routine for handling retries of failed operations.

    This routine wraps operations with retry logic, supporting various
    backoff strategies and configurable retry conditions.

    Configuration Options:
        max_attempts: Maximum number of retry attempts (default: 3)
        backoff: Backoff strategy:
            - "fixed": Fixed delay between retries
            - "linear": Linearly increasing delay
            - "exponential": Exponentially increasing delay
            - "exponential_jitter": Exponential with random jitter
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay cap in seconds (default: 60.0)
        retryable_exceptions: List of exception types to retry (default: [Exception])
        retryable_error_codes: List of error codes to retry (default: None)
        on_retry: Callback function called on each retry
        on_exhausted: Callback function called when retries exhausted

    Examples:
        Basic retry with exponential backoff:

        >>> retry_handler = RetryHandler()
        >>> retry_handler.set_config(
        ...     max_attempts=3,
        ...     backoff="exponential",
        ...     base_delay=1.0
        ... )

        Retry specific exceptions:

        >>> retry_handler = RetryHandler()
        >>> retry_handler.set_config(
        ...     max_attempts=5,
        ...     retryable_exceptions=[ConnectionError, TimeoutError]
        ... )

        With callbacks:

        >>> def on_retry(attempt, error, delay):
        ...     print(f"Retry {attempt} after {delay}s: {error}")
        >>>
        >>> retry_handler = RetryHandler()
        >>> retry_handler.set_config(
        ...     max_attempts=3,
        ...     on_retry=on_retry
        ... )
    """

    def __init__(self) -> None:
        """Initialize RetryHandler routine."""
        super().__init__()

        # Set default configuration
        self.set_config(
            max_attempts=3,  # Max retry attempts
            backoff="exponential",  # "fixed", "linear", "exponential", "exponential_jitter"
            base_delay=1.0,  # Base delay in seconds
            max_delay=60.0,  # Maximum delay cap
            retryable_exceptions=None,  # None = all exceptions
            retryable_error_codes=None,  # Error codes to retry
            on_retry=None,  # Retry callback
            on_exhausted=None,  # Exhausted callback
        )

        # Define input slot
        self.add_slot("input")

        # Define output events
        self.add_event("success", ["data", "attempts"])
        self.add_event("retry", ["data", "attempt", "error", "delay"])
        self.add_event("exhausted", ["data", "attempts", "errors"])
        self.add_event("error", ["error", "data"])

        # Internal state
        self._lock = threading.Lock()

        # Set up activation policy and logic
        self.set_activation_policy(self._activation_policy)
        self.set_logic(self._run_logic)

    def _activation_policy(self, slots: dict, worker_state: Any) -> tuple[bool, dict, str]:
        """Check if we have data to process."""
        slot = slots.get("input")
        if slot is None:
            return False, {}, "no_slot"

        has_new = len(slot.new_data) > 0
        if has_new:
            data_slice = {"input": slot.consume_all_new()}
            return True, data_slice, "slot_activated"
        return False, {}, "no_new_data"

    def _run_logic(self, **kwargs: Any) -> None:
        """Process data with retry logic."""
        data_list = kwargs.get("input", [])
        items = data_list if isinstance(data_list, list) else [data_list]

        max_attempts = self.get_config("max_attempts", 3)
        backoff = self.get_config("backoff", "exponential")
        base_delay = self.get_config("base_delay", 1.0)
        max_delay = self.get_config("max_delay", 60.0)
        retryable_exceptions = self.get_config("retryable_exceptions")
        on_retry = self.get_config("on_retry")
        on_exhausted = self.get_config("on_exhausted")

        for item in items:
            # Extract operation if item is a dict with operation
            if isinstance(item, dict) and "operation" in item:
                operation = item["operation"]
                data = item.get("data", item)
            else:
                operation = None
                data = item

            # If no operation, treat as pass-through
            if operation is None:
                self.emit("success", data=item, attempts=1)
                continue

            errors = []
            attempt = 0

            while attempt < max_attempts:
                attempt += 1

                try:
                    # Execute the operation
                    if callable(operation):
                        result = operation(data if data is not item else item)
                    else:
                        result = operation

                    # Success
                    self.emit("success", data=result, attempts=attempt)
                    break

                except Exception as e:
                    errors.append(str(e))

                    # Check if this exception is retryable
                    if not self._is_retryable(e, retryable_exceptions):
                        self.emit("error", error=str(e), data=item)
                        break

                    # Check if we have more attempts
                    if attempt >= max_attempts:
                        # Exhausted retries
                        if on_exhausted and callable(on_exhausted):
                            try:
                                on_exhausted(attempt, errors, item)
                            except Exception:
                                pass
                        self.emit("exhausted", data=item, attempts=attempt, errors=errors)
                        break

                    # Calculate delay
                    delay = self._calculate_delay(attempt, backoff, base_delay, max_delay)

                    # Emit retry event
                    self.emit("retry", data=item, attempt=attempt, error=str(e), delay=delay)

                    # Call retry callback
                    if on_retry and callable(on_retry):
                        try:
                            on_retry(attempt, e, delay)
                        except Exception:
                            pass

                    # Wait before retry
                    time.sleep(delay)

    def _is_retryable(
        self,
        exception: Exception,
        retryable_exceptions: list[type[Exception]] | None,
    ) -> bool:
        """Check if an exception is retryable.

        Args:
            exception: The exception that occurred
            retryable_exceptions: List of retryable exception types

        Returns:
            True if the exception should be retried
        """
        if retryable_exceptions is None:
            # Retry all exceptions by default
            return True

        return any(isinstance(exception, exc_type) for exc_type in retryable_exceptions)

    def _calculate_delay(
        self,
        attempt: int,
        backoff: str,
        base_delay: float,
        max_delay: float,
    ) -> float:
        """Calculate the delay before next retry.

        Args:
            attempt: Current attempt number
            backoff: Backoff strategy
            base_delay: Base delay in seconds
            max_delay: Maximum delay cap

        Returns:
            Delay in seconds
        """
        if backoff == "fixed":
            delay = base_delay

        elif backoff == "linear":
            delay = base_delay * attempt

        elif backoff == "exponential":
            delay = base_delay * (2 ** (attempt - 1))

        elif backoff == "exponential_jitter":
            # Exponential with full jitter
            exponential_delay = base_delay * (2 ** (attempt - 1))
            delay = random.uniform(0, exponential_delay)  # noqa: S311

        else:
            delay = base_delay

        # Cap at max delay
        return min(delay, max_delay)

    def wrap_operation(self, operation: Callable, data: Any = None) -> dict:
        """Wrap an operation for retry handling.

        Args:
            operation: The operation to wrap
            data: Optional data to pass to the operation

        Returns:
            A dict that can be sent to the retry handler
        """
        return {"operation": operation, "data": data}

    def execute_with_retry(
        self,
        operation: Callable,
        data: Any = None,
        **config: Any,
    ) -> Any:
        """Execute an operation with retry logic synchronously.

        This is a convenience method for direct use without the flow.

        Args:
            operation: The operation to execute
            data: Data to pass to the operation
            **config: Override configuration options

        Returns:
            The result of the operation

        Raises:
            Exception: If all retries are exhausted
        """
        max_attempts = config.get("max_attempts", self.get_config("max_attempts", 3))
        backoff = config.get("backoff", self.get_config("backoff", "exponential"))
        base_delay = config.get("base_delay", self.get_config("base_delay", 1.0))
        max_delay = config.get("max_delay", self.get_config("max_delay", 60.0))
        retryable_exceptions = config.get(
            "retryable_exceptions", self.get_config("retryable_exceptions")
        )

        errors = []
        attempt = 0

        while attempt < max_attempts:
            attempt += 1

            try:
                if data is not None:
                    return operation(data)
                return operation()

            except Exception as e:
                errors.append(e)

                if not self._is_retryable(e, retryable_exceptions):
                    raise

                if attempt >= max_attempts:
                    raise

                delay = self._calculate_delay(attempt, backoff, base_delay, max_delay)
                time.sleep(delay)

        # Should not reach here, but just in case
        raise errors[-1] if errors else RuntimeError("Unknown error")
