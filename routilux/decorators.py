"""
Routilux decorators for simplified routine creation.

This module provides decorators that make it easy to convert regular Python
functions into Routine classes without boilerplate code.
"""

from __future__ import annotations

from typing import Any, Callable

from routilux.core.routine import Routine


def routine(
    input_slot: str = "input",
    output_event: str = "output",
    name: str | None = None,
) -> Callable[[Callable[..., Any]], type[Routine]]:
    """Convert a function into a Routine class.

    This decorator transforms a regular Python function into a Routine class
    that can be used in flows. The decorated function becomes the routine's
    logic, processing data from the input slot and emitting results to
    the output event.

    Args:
        input_slot: Name of the input slot (default: "input")
        output_event: Name of the output event (default: "output")
        name: Optional name for the routine class (default: function name)

    Returns:
        A Routine subclass

    Examples:
        Basic usage:

        >>> from routilux import routine, Flow, Runtime
        >>>
        >>> @routine()
        ... def process(data):
        ...     return {"processed": data}
        >>>
        >>> # Create instance and use in flow
        >>> processor = process()
        >>> flow = Flow("my_flow")
        >>> flow.add_routine(processor, "processor")

        With custom slot/event names:

        >>> @routine(input_slot="data_in", output_event="result")
        ... def transformer(item):
        ...     return item * 2

        Multiple instances with different configs:

        >>> @routine()
        ... def scaler(data):
        ...     factor = scaler.get_config("factor", 1)
        ...     return data * factor
        >>>
        >>> scaler1 = scaler()
        >>> scaler1.set_config(factor=2)
        >>> scaler2 = scaler()
        >>> scaler2.set_config(factor=10)

    Note:
        The decorated function returns a Routine CLASS, not an instance.
        You need to call it to create an instance.
    """

    def decorator(func: Callable[..., Any]) -> type[Routine]:
        """Create a Routine subclass from the function."""

        class FunctionRoutine(Routine):
            """Routine wrapper for a function."""

            def __init__(self) -> None:
                super().__init__()
                self.add_slot(input_slot)
                self.add_event(output_event)
                self._func = func
                self._input_slot_name = input_slot
                self._output_event_name = output_event

                # Set activation policy: activate when input slot has data
                self.set_activation_policy(self._check_activation)
                self.set_logic(self._run_logic)

            def _check_activation(self, slots: dict, worker_state: Any) -> tuple[bool, dict, str]:
                """Check if routine should activate based on input slot state."""
                slot = slots.get(self._input_slot_name)
                if slot is None:
                    return False, {}, "no_slot"

                has_new = len(slot.new_data) > 0
                if has_new:
                    data_slice = {self._input_slot_name: slot.consume_all_new()}
                    return True, data_slice, "slot_activated"
                return False, {}, "no_new_data"

            def _run_logic(self, **kwargs: Any) -> None:
                """Execute the wrapped function with input data."""
                data_list = kwargs.get(self._input_slot_name, [])

                # Handle single item or list
                items = data_list if isinstance(data_list, list) else [data_list]

                for item in items:
                    try:
                        # Call the wrapped function
                        result = self._func(item)
                        # Emit the result
                        self.emit(self._output_event_name, result=result)
                    except Exception as e:
                        # Emit error event if it exists, otherwise re-raise
                        if "error" in self._events:
                            self.emit("error", error=str(e), data=item)
                        else:
                            raise

        # Set class name for better debugging
        routine_name = name or func.__name__
        FunctionRoutine.__name__ = routine_name
        FunctionRoutine.__qualname__ = routine_name
        FunctionRoutine.__module__ = func.__module__
        FunctionRoutine.__doc__ = func.__doc__

        return FunctionRoutine

    return decorator


def routine_class(
    name: str | None = None,
    slots: list[str] | None = None,
    events: list[str] | None = None,
) -> Callable[[type], type[Routine]]:
    """Decorator to create a Routine class from a regular class.

    This decorator transforms a regular class into a Routine subclass.
    Useful when you need more control over initialization or want to
    define multiple methods.

    Args:
        name: Optional name for the routine class
        slots: List of input slot names to create
        events: List of output event names to create

    Returns:
        A Routine subclass

    Examples:
        >>> @routine_class(slots=["input"], events=["output", "error"])
        ... class DataProcessor:
        ...     def process(self, data):
        ...         try:
        ...             result = self.transform(data)
        ...             self.emit("output", result=result)
        ...         except Exception as e:
        ...             self.emit("error", error=str(e))
        ...
        ...     def transform(self, data):
        ...         return {"processed": data}

    Note:
        The decorated class must have a method named 'process' or 'logic'
        that will be called when the routine activates.
    """

    def decorator(cls: type) -> type[Routine]:
        """Create a Routine subclass from the class."""

        class ClassRoutine(Routine):
            """Routine wrapper for a class."""

            def __init__(self) -> None:
                super().__init__()
                # Create slots
                for slot_name in slots or ["input"]:
                    self.add_slot(slot_name)
                # Create events
                for event_name in events or ["output"]:
                    self.add_event(event_name)

                # Store the original class methods
                self._process_method = getattr(cls, "process", None) or getattr(cls, "logic", None)

                # Set activation policy
                input_slot = (slots or ["input"])[0]
                self._input_slot_name = input_slot
                self.set_activation_policy(self._activation_policy)
                self.set_logic(self._run_logic)

            def _activation_policy(
                self, slots_dict: dict, worker_state: Any
            ) -> tuple[bool, dict, str]:
                """Check if routine should activate."""
                slot = slots_dict.get(self._input_slot_name)
                if slot is None:
                    return False, {}, "no_slot"

                has_new = len(slot.new_data) > 0
                if has_new:
                    data_slice = {self._input_slot_name: slot.consume_all_new()}
                    return True, data_slice, "slot_activated"
                return False, {}, "no_new_data"

            def _run_logic(self, **kwargs: Any) -> None:
                """Execute the process method."""
                if self._process_method:
                    # Bind the method to this instance
                    bound_method = self._process_method.__get__(self, type(self))
                    data_list = kwargs.get(self._input_slot_name, [])
                    items = data_list if isinstance(data_list, list) else [data_list]
                    for item in items:
                        bound_method(item)

        # Set class name
        routine_name = name or cls.__name__
        ClassRoutine.__name__ = routine_name
        ClassRoutine.__qualname__ = routine_name
        ClassRoutine.__module__ = cls.__module__
        ClassRoutine.__doc__ = cls.__doc__

        return ClassRoutine

    return decorator
