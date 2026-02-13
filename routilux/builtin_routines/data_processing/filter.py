"""
Filter routine for conditional data filtering.
"""

from __future__ import annotations

from typing import Any, Callable

from routilux.core import Routine


class Filter(Routine):
    """Routine for filtering data based on conditions.

    This routine evaluates data against a condition and emits to
    different events based on the result. Useful for data validation,
    routing, and quality filtering.

    Configuration Options:
        condition: Filter condition. Can be:
            - Callable: Function that returns bool
            - dict: Field-value match conditions
            - str: Field name (truthy check)
            - list: List of values (membership check)
        pass_event: Event name for passing items (default: "passed")
        reject_event: Event name for rejected items (default: "rejected")
        invert: Invert the condition (default: False)
        include_reason: Include rejection reason in output (default: True)

    Examples:
        Using a callable:

        >>> filter_routine = Filter()
        >>> filter_routine.set_config(
        ...     condition=lambda x: x.get("age", 0) >= 18
        ... )

        Using dict conditions:

        >>> filter_routine = Filter()
        >>> filter_routine.set_config(
        ...     condition={"status": "active", "verified": True}
        ... )

        Using field existence:

        >>> filter_routine = Filter()
        >>> filter_routine.set_config(condition="email")  # Must have email field

        With inversion:

        >>> filter_routine = Filter()
        >>> filter_routine.set_config(
        ...     condition={"banned": True},
        ...     invert=True  # Pass if NOT banned
        ... )
    """

    def __init__(self) -> None:
        """Initialize Filter routine."""
        super().__init__()

        # Set default configuration
        self.set_config(
            condition=None,  # Filter condition
            pass_event="passed",  # Event for passing items
            reject_event="rejected",  # Event for rejected items
            invert=False,  # Invert condition
            include_reason=True,  # Include rejection reason
        )

        # Define input slot
        self.add_slot("input")

        # Define output events (will be configured dynamically)
        self._pass_event = self.add_event("passed", ["data"])
        self._reject_event = self.add_event("rejected", ["data", "reason"])

        # Set up activation policy and logic
        self.set_activation_policy(self._activation_policy)
        self.set_logic(self._run_logic)

    def _activation_policy(self, slots: dict, worker_state: Any) -> tuple[bool, dict, str]:
        """Check if we have data to filter."""
        slot = slots.get("input")
        if slot is None:
            return False, {}, "no_slot"

        has_new = len(slot.new_data) > 0
        if has_new:
            data_slice = {"input": slot.consume_all_new()}
            return True, data_slice, "slot_activated"
        return False, {}, "no_new_data"

    def _run_logic(self, **kwargs: Any) -> None:
        """Filter and route data based on condition."""
        data_list = kwargs.get("input", [])
        items = data_list if isinstance(data_list, list) else [data_list]

        condition = self.get_config("condition")
        invert = self.get_config("invert", False)
        include_reason = self.get_config("include_reason", True)

        for item in items:
            try:
                passes, reason = self._evaluate_condition(item, condition)

                # Apply inversion
                if invert:
                    passes = not passes
                    reason = f"Inverted: {reason}" if include_reason else None

                if passes:
                    self.emit("passed", data=item)
                else:
                    emit_kwargs = {"data": item}
                    if include_reason:
                        emit_kwargs["reason"] = reason
                    self.emit("rejected", **emit_kwargs)

            except Exception as e:
                # On error, reject with error reason
                emit_kwargs = {"data": item}
                if include_reason:
                    emit_kwargs["reason"] = f"Evaluation error: {str(e)}"
                self.emit("rejected", **emit_kwargs)

    def _evaluate_condition(self, item: Any, condition: Any) -> tuple[bool, str | None]:
        """Evaluate if item passes the condition.

        Args:
            item: Data item to evaluate
            condition: Condition to evaluate against

        Returns:
            Tuple of (passes, reason)
        """
        if condition is None:
            # No condition means pass all
            return True, None

        # Callable condition
        if callable(condition):
            try:
                result = condition(item)
                if isinstance(result, tuple) and len(result) == 2:
                    return result
                return bool(result), None
            except Exception as e:
                return False, f"Condition raised: {str(e)}"

        # Dict condition (field-value matching)
        if isinstance(condition, dict):
            if not isinstance(item, dict):
                return False, "Item is not a dict"

            for field, expected in condition.items():
                if field not in item:
                    return False, f"Missing field: {field}"
                if item[field] != expected:
                    return False, f"Field '{field}' != {expected}"

            return True, None

        # String condition (field existence/truthy check)
        if isinstance(condition, str):
            if isinstance(item, dict):
                if condition not in item:
                    return False, f"Missing field: {condition}"
                if not item[condition]:
                    return False, f"Field '{condition}' is falsy"
                return True, None
            else:
                # Check attribute
                if not hasattr(item, condition):
                    return False, f"Missing attribute: {condition}"
                if not getattr(item, condition):
                    return False, f"Attribute '{condition}' is falsy"
                return True, None

        # List condition (membership check)
        if isinstance(condition, (list, tuple, set)):
            if item in condition:
                return True, None
            return False, "Item not in allowed list"

        # Unknown condition type
        return False, f"Unknown condition type: {type(condition).__name__}"

    def set_condition(self, condition: Any) -> None:
        """Set the filter condition.

        Args:
            condition: The condition to use for filtering
        """
        self.set_config(condition=condition)

    def set_callable(self, func: Callable[[Any], bool]) -> None:
        """Set a callable filter function.

        Args:
            func: Function that takes an item and returns bool
        """
        self.set_config(condition=func)
