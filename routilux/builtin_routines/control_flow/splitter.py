"""
Splitter routine for splitting data into individual items.
"""

from __future__ import annotations

from typing import Any

from routilux.core import Routine


class Splitter(Routine):
    """Routine for splitting collections into individual items.

    This routine takes a collection (list, dict, string) and emits
    each item separately. Useful for processing items in parallel
    after a batch operation.

    Configuration Options:
        field: Field name to split if input is a dict (default: None = split the input itself)
        split_strings: Whether to split strings into characters (default: False)
        dict_mode: How to handle dict splitting:
            - "items": Emit (key, value) tuples
            - "keys": Emit keys only
            - "values": Emit values only
            - "entries": Emit {key, value} dicts
        include_index: Include item index in output (default: False)
        include_count: Include total count in output (default: False)

    Examples:
        Split a list:

        >>> splitter = Splitter()
        >>> # Input: [1, 2, 3]
        >>> # Outputs: 1, 2, 3 (each as separate event)

        Split a dict field:

        >>> splitter = Splitter()
        >>> splitter.set_config(field="items")
        >>> # Input: {"items": [1, 2, 3], "other": "data"}
        >>> # Outputs: 1, 2, 3

        Split dict entries:

        >>> splitter = Splitter()
        >>> splitter.set_config(dict_mode="entries")
        >>> # Input: {"a": 1, "b": 2}
        >>> # Outputs: {"key": "a", "value": 1}, {"key": "b", "value": 2}
    """

    def __init__(self) -> None:
        """Initialize Splitter routine."""
        super().__init__()

        # Set default configuration
        self.set_config(
            field=None,  # Field to split
            split_strings=False,  # Split strings into chars
            dict_mode="values",  # "items", "keys", "values", "entries"
            include_index=False,  # Include item index
            include_count=False,  # Include total count
        )

        # Define input slot
        self.add_slot("input")

        # Define output events
        self.add_event("item", ["item", "index", "count"])
        self.add_event("empty", [])
        self.add_event("error", ["error", "data"])

        # Set up activation policy and logic
        self.set_activation_policy(self._activation_policy)
        self.set_logic(self._run_logic)

    def _activation_policy(self, slots: dict, worker_state: Any) -> tuple[bool, dict, str]:
        """Check if we have data to split."""
        slot = slots.get("input")
        if slot is None:
            return False, {}, "no_slot"

        has_new = len(slot.new_data) > 0
        if has_new:
            data_slice = {"input": slot.consume_all_new()}
            return True, data_slice, "slot_activated"
        return False, {}, "no_new_data"

    def _run_logic(self, **kwargs: Any) -> None:
        """Split and emit individual items."""
        data_list = kwargs.get("input", [])
        items = data_list if isinstance(data_list, list) else [data_list]

        field = self.get_config("field")
        split_strings = self.get_config("split_strings", False)
        dict_mode = self.get_config("dict_mode", "values")
        include_index = self.get_config("include_index", False)
        include_count = self.get_config("include_count", False)

        for data in items:
            try:
                # Extract field if specified
                if field and isinstance(data, dict):
                    target = data.get(field)
                else:
                    target = data

                if target is None:
                    self.emit("empty")
                    continue

                # Split based on type
                split_items = self._split_target(target, split_strings, dict_mode)

                if not split_items:
                    self.emit("empty")
                    continue

                total = len(split_items)

                # Emit each item
                for idx, item in enumerate(split_items):
                    emit_kwargs = {"item": item}
                    if include_index:
                        emit_kwargs["index"] = idx
                    if include_count:
                        emit_kwargs["count"] = total
                    self.emit("item", **emit_kwargs)

            except Exception as e:
                self.emit("error", error=str(e), data=data)

    def _split_target(self, target: Any, split_strings: bool, dict_mode: str) -> list[Any]:
        """Split the target data into items.

        Args:
            target: Data to split
            split_strings: Whether to split strings
            dict_mode: How to handle dicts

        Returns:
            List of split items
        """
        # Handle strings
        if isinstance(target, str):
            if split_strings:
                return list(target)
            return [target]

        # Handle dicts
        if isinstance(target, dict):
            if dict_mode == "items":
                return list(target.items())
            elif dict_mode == "keys":
                return list(target.keys())
            elif dict_mode == "entries":
                return [{"key": k, "value": v} for k, v in target.items()]
            else:  # values
                return list(target.values())

        # Handle lists/tuples/sets
        if isinstance(target, (list, tuple, set)):
            return list(target)

        # Handle other iterables
        try:
            return list(target)
        except TypeError:
            # Not iterable, return as single item
            return [target]
