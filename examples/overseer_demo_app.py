#!/usr/bin/env python
"""
Simplified Overseer Demo App for Routilux

Simple, practical routines and flows for testing and demonstration.

This demo provides:
✓ Simple routines with clear input/output formats
✓ Practical flows for testing routed stdout, batch processing, and pipelines
✓ Clear documentation in docstrings for each routine

Author: Routilux Overseer Team
Date: 2025-01-XX
"""

import time
from datetime import datetime

from routilux import Flow, Routine
from routilux.activation_policies import batch_size_policy, immediate_policy
from routilux.monitoring.registry import MonitoringRegistry

# ===== Routines =====


class CountdownTimer(Routine):
    """Countdown timer that emits progress events and prints to stdout.

    Purpose:
        Test routed stdout capture and display progress in client UI.
        Receives a delay in milliseconds, then loops: sleep 1 second,
        print remaining time, emit tick event. Continues until delay is exhausted.

    Configuration:
        None (all configuration comes from input data)

    Input (via trigger slot):
        {
            "delay_ms": 5000  # Total delay in milliseconds (required)
        }

    Output (tick event):
        {
            "remaining_ms": 4000,    # Remaining milliseconds
            "elapsed_ms": 1000,       # Elapsed milliseconds
            "progress": 0.2,          # Progress ratio (0.0 to 1.0)
            "total_ms": 5000          # Total delay
        }

    Print Output:
        [CountdownTimer] Starting countdown: 5000ms
        [CountdownTimer] Remaining: 4000ms (80% complete)
        [CountdownTimer] Remaining: 3000ms (60% complete)
        [CountdownTimer] Remaining: 2000ms (40% complete)
        [CountdownTimer] Remaining: 1000ms (20% complete)
        [CountdownTimer] Countdown complete!
    """

    def __init__(self):
        super().__init__()
        self.trigger_slot = self.add_slot("trigger")
        self.tick_event = self.add_event(
            "tick", ["remaining_ms", "elapsed_ms", "progress", "total_ms"]
        )
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_countdown)

    def _handle_countdown(self, *slot_data_lists, policy_message, worker_state):
        trigger_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []
        data_dict = trigger_data[0] if trigger_data else {}

        delay_ms = data_dict.get("delay_ms") if isinstance(data_dict, dict) else None
        if delay_ms is None:
            print("[CountdownTimer] Error: delay_ms not provided")
            return

        total_ms = int(delay_ms)
        elapsed_ms = 0
        remaining_ms = total_ms

        print(f"[CountdownTimer] Starting countdown: {total_ms}ms")

        while remaining_ms > 0:
            # Sleep for 1 second (1000ms) or remaining time if less
            sleep_ms = min(1000, remaining_ms)
            time.sleep(sleep_ms / 1000.0)

            elapsed_ms += sleep_ms
            remaining_ms = total_ms - elapsed_ms
            progress = elapsed_ms / total_ms if total_ms > 0 else 0.0

            # Print progress
            progress_pct = int(progress * 100)
            print(f"[CountdownTimer] Remaining: {remaining_ms}ms ({100 - progress_pct}% complete)")

            # Emit tick event
            self.emit(
                "tick",
                worker_state=worker_state,
                remaining_ms=remaining_ms,
                elapsed_ms=elapsed_ms,
                progress=progress,
                total_ms=total_ms,
            )

        print("[CountdownTimer] Countdown complete!")


class BatchProcessor(Routine):
    """Processes data in batches with configurable batch size.

    Purpose:
        Generic test routine that collects N messages before processing.
        Uses batch_size_policy to control when to activate. Prints the entire
        batch and emits it as output.

    Configuration:
        {
            "batch_size": 3  # Number of items to collect before processing (required)
        }

    Input (via input slot):
        {
            "data": "item1",  # Data item
            "index": 1        # Optional index
        }

    Output (output event):
        {
            "batch": [
                {"data": "item1", "index": 1},
                {"data": "item2", "index": 2},
                {"data": "item3", "index": 3}
            ],
            "batch_size": 3,
            "processed_at": "2025-01-20T10:00:00"
        }

    Print Output:
        [BatchProcessor] Processing batch of 3 items:
          - Item 1: item1
          - Item 2: item2
          - Item 3: item3
    """

    def __init__(self):
        super().__init__()
        self.input_slot = self.add_slot("input")
        self.output_event = self.add_event("output", ["batch", "batch_size", "processed_at"])
        # Default batch_size, will be updated from config if provided
        self.set_activation_policy(batch_size_policy(3))
        self.set_logic(self._handle_batch)

    def set_config(self, **kwargs):
        """Override set_config to update activation policy when batch_size changes."""
        super().set_config(**kwargs)
        # Update activation policy if batch_size is in config
        if "batch_size" in kwargs:
            batch_size = kwargs["batch_size"]
            self.set_activation_policy(batch_size_policy(batch_size))

    def _handle_batch(self, *slot_data_lists, policy_message, worker_state):
        input_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []

        batch_size = len(input_data)
        print(f"[BatchProcessor] Processing batch of {batch_size} items:")

        # Process and print each item
        batch = []
        for i, data_dict in enumerate(input_data, 1):
            if not isinstance(data_dict, dict):
                continue
            data = data_dict.get("data", "unknown")
            index = data_dict.get("index", i)
            print(f"  - Item {i}: {data}")
            batch.append({"data": data, "index": index})

        # Emit batch
        self.emit(
            "output",
            worker_state=worker_state,
            batch=batch,
            batch_size=batch_size,
            processed_at=datetime.now().isoformat(),
        )


class SimplePrinter(Routine):
    """Receives input and prints it (sink routine for testing).

    Purpose:
        Simple sink routine that receives data and prints it.
        No output events - used as a terminal node in flows.

    Configuration:
        None

    Input (via input slot):
        {
            "data": "any_data",  # Any data to print
            "index": 1          # Optional index
        }

    Output:
        None (sink routine, no events)

    Print Output:
        [SimplePrinter] Received: any_data (index: 1)
    """

    def __init__(self):
        super().__init__()
        self.input_slot = self.add_slot("input")
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_print)

    def _handle_print(self, *slot_data_lists, policy_message, worker_state):
        input_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []

        for data_dict in input_data:
            if not isinstance(data_dict, dict):
                continue
            data = data_dict.get("data", "unknown")
            index = data_dict.get("index", "N/A")
            print(f"[SimplePrinter] Received: {data} (index: {index})")


class DelayRoutine(Routine):
    """Delays data transmission by configured milliseconds.

    Purpose:
        Receives input data, sleeps for configured milliseconds, then emits
        the same data. Useful for testing timing and simulating slow processing.

    Configuration:
        {
            "delay_ms": 2000  # Delay in milliseconds before emitting (required)
        }

    Input (via input slot):
        {
            "data": "any_data"  # Data to delay
        }

    Output (output event):
        {
            "data": "any_data",      # Original data
            "delayed_by_ms": 2000,    # Delay applied
            "emitted_at": "2025-01-20T10:00:00"
        }

    Print Output:
        [DelayRoutine] Delaying data for 2000ms...
        [DelayRoutine] Data emitted after delay
    """

    def __init__(self):
        super().__init__()
        self.input_slot = self.add_slot("input")
        self.output_event = self.add_event("output", ["data", "delayed_by_ms", "emitted_at"])
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_delay)

    def _handle_delay(self, *slot_data_lists, policy_message, worker_state):
        input_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []
        data_dict = input_data[0] if input_data else {}

        delay_ms = self.get_config("delay_ms", 1000)
        data = data_dict.get("data") if isinstance(data_dict, dict) else data_dict

        print(f"[DelayRoutine] Delaying data for {delay_ms}ms...")
        time.sleep(delay_ms / 1000.0)

        print("[DelayRoutine] Data emitted after delay")
        self.emit(
            "output",
            worker_state=worker_state,
            data=data,
            delayed_by_ms=delay_ms,
            emitted_at=datetime.now().isoformat(),
        )


class EchoRoutine(Routine):
    """Simple echo - receives input and emits it unchanged.

    Purpose:
        Simple pass-through routine for testing event routing.
        Receives input and emits the same data unchanged.
        Can be triggered via trigger slot or input slot.

    Configuration:
        None

    Input (via trigger or input slot):
        {
            "data": "any_data"  # Data to echo
        }

    Output (output event):
        {
            "data": "any_data"  # Same as input
        }

    Print Output:
        [EchoRoutine] Echo: any_data
    """

    def __init__(self):
        super().__init__()
        self.trigger_slot = self.add_slot("trigger")
        self.input_slot = self.add_slot("input")
        self.output_event = self.add_event("output", ["data"])
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_echo)

    def _handle_echo(self, *slot_data_lists, policy_message, worker_state):
        # Check trigger slot first, then input slot
        trigger_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []
        input_data = slot_data_lists[1] if len(slot_data_lists) > 1 and slot_data_lists[1] else []

        # Use trigger data if available, otherwise use input data
        data_list = trigger_data if trigger_data else input_data
        data_dict = data_list[0] if data_list else {}

        # If data_dict has a "data" key, use that; otherwise use the whole dict
        if isinstance(data_dict, dict) and "data" in data_dict:
            data = data_dict["data"]
        else:
            data = data_dict if isinstance(data_dict, dict) else data_dict

        print(f"[EchoRoutine] Echo: {data}")
        # Emit the data directly (not wrapped in a "data" field)
        # This allows downstream routines to receive the actual data
        if isinstance(data, dict):
            self.emit("output", worker_state=worker_state, **data)
        else:
            self.emit("output", worker_state=worker_state, data=data)


class CounterRoutine(Routine):
    """Counts received messages and emits count.

    Purpose:
        Maintains a counter of received messages and emits the current count.
        Uses WorkerState to persist counter across multiple activations.

    Configuration:
        None

    Input (via input slot):
        {
            "data": "any_data"  # Any data (ignored, only count matters)
        }

    Output (output event):
        {
            "count": 5,  # Current message count
            "message": "Received 5 messages"
        }

    Print Output:
        [CounterRoutine] Counter: 5 messages received
    """

    def __init__(self):
        super().__init__()
        self.input_slot = self.add_slot("input")
        self.output_event = self.add_event("output", ["count", "message"])
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_count)

    def _handle_count(self, *slot_data_lists, policy_message, worker_state):
        input_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []

        # Get routine_id - REQUIRED, no fallback
        ctx = self.get_execution_context()
        routine_id = ctx.routine_id if ctx else None
        if routine_id is None:
            raise RuntimeError(
                "CounterRoutine requires routine_id. "
                "This routine must be added to a flow before execution."
            )

        # Get current count from WorkerState (already isolated by routine_id)
        routine_state = worker_state.get_routine_state(routine_id) or {}
        count = routine_state.get("count", 0) + len(input_data)
        worker_state.update_routine_state(routine_id, {"count": count})

        print(f"[CounterRoutine] Counter: {count} messages received")
        self.emit(
            "output",
            worker_state=worker_state,
            count=count,
            message=f"Received {count} messages",
        )


class FilterRoutine(Routine):
    """Filters data based on simple threshold condition.

    Purpose:
        Receives a value and compares it with a threshold from config.
        Only emits output if value >= threshold. Always prints the result.

    Configuration:
        {
            "threshold": 50  # Only emit if value >= threshold (required)
        }

    Input (via input slot):
        {
            "value": 42  # Value to filter
        }

    Output (output event, only if value >= threshold):
        {
            "value": 42,
            "threshold": 50,
            "passed": False  # Whether value passed filter
        }

    Print Output:
        [FilterRoutine] Filter: value=42, threshold=50, passed=False
    """

    def __init__(self):
        super().__init__()
        self.input_slot = self.add_slot("input")
        self.output_event = self.add_event("output", ["value", "threshold", "passed"])
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_filter)

    def _handle_filter(self, *slot_data_lists, policy_message, worker_state):
        input_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []
        data_dict = input_data[0] if input_data else {}

        threshold = self.get_config("threshold", 0)
        value = data_dict.get("value") if isinstance(data_dict, dict) else None

        if value is None:
            print("[FilterRoutine] Error: value not provided")
            return

        passed = value >= threshold

        print(f"[FilterRoutine] Filter: value={value}, threshold={threshold}, passed={passed}")

        # Only emit if passed
        if passed:
            self.emit(
                "output",
                worker_state=worker_state,
                value=value,
                threshold=threshold,
                passed=passed,
            )


class DataProcessorRoutine(Routine):
    """Generic data processing routine that executes code on input data.

    Purpose:
        Receives input data and applies a code snippet from config to process it.
        Uses eval() or exec() to execute the code snippet. The code should modify
        the input data and return the result.

    Configuration:
        {
            "code": "data['value'] = data.get('value', 0) + 1; result = data"  # Python code string (required)
            # OR
            "code": "data['value'] = data.get('value', 0) * 2"  # Code that modifies data in-place
        }

    Input (via input slot):
        {
            "value": 5,  # Any data structure
            "other": "field"
        }

    Output (output event):
        {
            "value": 6,  # Processed data (after code execution)
            "other": "field"
        }

    Print Output:
        [DataProcessorRoutine] Processing data with code...
        [DataProcessorRoutine] Result: {'value': 6, 'other': 'field'}
    """

    def __init__(self):
        super().__init__()
        self.input_slot = self.add_slot("input")
        self.output_event = self.add_event("output", ["data", "processed"])
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_process)

    def _handle_process(self, *slot_data_lists, policy_message, worker_state):
        input_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []
        data_dict = input_data[0] if input_data else {}

        code = self.get_config("code", "")
        if not code:
            print("[DataProcessorRoutine] Error: code not provided in config")
            return

        # Use the whole dict as data (events emit data as dict fields)
        data = dict(data_dict) if isinstance(data_dict, dict) else {"value": data_dict}

        # Ensure data has at least a "value" field if empty
        if not data:
            data = {"value": 0}

        try:
            print("[DataProcessorRoutine] Processing data with code...")
            # Execute code in a safe namespace
            namespace = {"data": data.copy() if isinstance(data, dict) else data}
            # Try exec first (for statements), then eval (for expressions)
            try:
                # Try exec for statements
                exec(code, namespace)
                # Get result from namespace
                result = namespace.get("result")
                if result is not None:
                    data = (
                        result if isinstance(result, dict) else {"result": result, "original": data}
                    )
                else:
                    data = namespace.get("data", data)
            except SyntaxError:
                # If exec fails, try eval for expressions
                try:
                    result = eval(code, namespace)
                    if result is not None:
                        data = (
                            result
                            if isinstance(result, dict)
                            else {"result": result, "original": data}
                        )
                    else:
                        data = namespace.get("data", data)
                except Exception:
                    # If both fail, use modified data from namespace
                    data = namespace.get("data", data)

            print(f"[DataProcessorRoutine] Result: {data}")
            # Emit data fields directly (not wrapped in "data" field)
            # This allows LoopController to receive the actual data
            emit_data = dict(data) if isinstance(data, dict) else {"result": data}
            emit_data["processed"] = True
            self.emit("output", worker_state=worker_state, **emit_data)
        except Exception as e:
            print(f"[DataProcessorRoutine] Error executing code: {e}")
            import traceback

            traceback.print_exc()
            # Emit error result
            self.emit(
                "output",
                worker_state=worker_state,
                data={"error": str(e), "original": data},
                processed=False,
            )


class LoopControllerRoutine(Routine):
    """Controls loop execution with exit condition.

    Purpose:
        Controls loop execution by checking exit conditions. Maintains iteration
        count and checks if loop should continue or exit based on config conditions.

    Configuration:
        {
            "max_iterations": 5,  # Maximum number of iterations (required)
            "exit_condition": "data.get('value', 0) >= 10"  # Python expression for exit condition (optional)
        }

    Input (via input slot):
        {
            "value": 5,  # Data to check
            "data": {...}
        }

    Output (continue event, if loop should continue):
        {
            "data": {...},  # Data to continue with
            "iteration": 2,  # Current iteration number
            "should_continue": True
        }

    Output (done event, if loop should exit):
        {
            "data": {...},  # Final data
            "iteration": 5,  # Final iteration number
            "should_continue": False,
            "reason": "max_iterations_reached"  # or "condition_met"
        }

    Print Output:
        [LoopControllerRoutine] Iteration 2/5: Continuing loop
        [LoopControllerRoutine] Iteration 5/5: Exiting loop (max_iterations_reached)
    """

    def __init__(self):
        super().__init__()
        self.input_slot = self.add_slot("input")
        self.continue_event = self.add_event("continue", ["data", "iteration", "should_continue"])
        self.done_event = self.add_event("done", ["data", "iteration", "should_continue", "reason"])
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_control)

    def _handle_control(self, *slot_data_lists, policy_message, worker_state):
        input_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []
        data_dict = input_data[0] if input_data else {}

        # Use the whole dict as data (events emit data as dict fields)
        actual_data = dict(data_dict) if isinstance(data_dict, dict) else {"value": data_dict}

        # Get job context - REQUIRED, no fallback
        from routilux.core import get_current_job

        job = get_current_job()
        if job is None:
            raise RuntimeError(
                "LoopControllerRoutine requires job context. "
                "This routine must be executed within a job execution context."
            )

        # Get routine_id - REQUIRED, no fallback
        ctx = self.get_execution_context()
        routine_id = ctx.routine_id if ctx else None
        if routine_id is None:
            raise RuntimeError(
                "LoopControllerRoutine requires routine_id. "
                "This routine must be added to a flow before execution."
            )

        # Use convenient method (automatically namespaced by routine_id)
        iteration = self.get_job_data("loop_iteration", 0) + 1
        self.set_job_data("loop_iteration", iteration)

        max_iterations = self.get_config("max_iterations", 5)
        exit_condition = self.get_config("exit_condition", "")

        # Check exit condition first (if provided)
        condition_met = False
        if exit_condition:
            try:
                namespace = {"data": actual_data, "__builtins__": __builtins__}
                condition_met = bool(eval(exit_condition, namespace))
            except Exception as e:
                print(f"[LoopControllerRoutine] Error evaluating exit condition: {e}")
                condition_met = False

        # Decide whether to continue or exit
        # Check exit condition first (priority), then max_iterations
        if condition_met:
            reason = "condition_met"
            print(
                f"[LoopControllerRoutine] Iteration {iteration}/{max_iterations}: Exiting loop ({reason})"
            )
            self.emit(
                "done",
                worker_state=worker_state,
                data=actual_data,
                iteration=iteration,
                should_continue=False,
                reason=reason,
            )
        elif iteration >= max_iterations:
            reason = "max_iterations_reached"
            print(
                f"[LoopControllerRoutine] Iteration {iteration}/{max_iterations}: Exiting loop ({reason})"
            )
            self.emit(
                "done",
                worker_state=worker_state,
                data=actual_data,
                iteration=iteration,
                should_continue=False,
                reason=reason,
            )
        else:
            print(
                f"[LoopControllerRoutine] Iteration {iteration}/{max_iterations}: Continuing loop"
            )
            # For continue, send data fields directly (not wrapped) so DataProcessor can process it
            emit_data = (
                dict(actual_data) if isinstance(actual_data, dict) else {"value": actual_data}
            )
            emit_data["iteration"] = iteration
            emit_data["should_continue"] = True
            self.emit("continue", worker_state=worker_state, **emit_data)


class DataSource(Routine):
    """Generates sample data for testing pipelines.

    Purpose:
        Generates a configurable number of data items. Used as a source
        routine in test pipelines (data_source -> data_transformer -> data_sink).

    Configuration:
        {
            "count": 3  # Number of data items to generate (default: 3)
        }

    Input (via trigger slot):
        None (can be triggered externally)

    Output (output event):
        {
            "data": "item1",  # Generated data item
            "index": 1,       # Item index (1-based)
            "total": 3        # Total items to generate
        }

    Print Output:
        [DataSource] Generating 3 items...
        [DataSource] Generated item 1/3
        [DataSource] Generated item 2/3
        [DataSource] Generated item 3/3
    """

    def __init__(self):
        super().__init__()
        self.trigger_slot = self.add_slot("trigger")
        self.output_event = self.add_event("output", ["data", "index", "total"])
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_generate)

    def _handle_generate(self, *slot_data_lists, policy_message, worker_state):
        count = self.get_config("count", 3)
        print(f"[DataSource] Generating {count} items...")

        for i in range(1, count + 1):
            item_data = f"item{i}"
            print(f"[DataSource] Generated item {i}/{count}")
            self.emit(
                "output",
                worker_state=worker_state,
                data=item_data,
                index=i,
                total=count,
            )


class DataTransformer(Routine):
    """Transforms input data (simple transformation for testing).

    Purpose:
        Simple transformation routine that receives data and transforms it.
        Used in test pipelines (data_source -> data_transformer -> data_sink).

    Configuration:
        None

    Input (via input slot):
        {
            "data": "item1",  # Input data
            "index": 1        # Optional index
        }

    Output (output event):
        {
            "data": "transformed_item1",  # Transformed data
            "index": 1,                    # Original index
            "transformed": True            # Transformation marker
        }

    Print Output:
        [DataTransformer] Transforming: item1
        [DataTransformer] Transformed to: transformed_item1
    """

    def __init__(self):
        super().__init__()
        self.input_slot = self.add_slot("input")
        self.output_event = self.add_event("output", ["data", "index", "transformed"])
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_transform)

    def _handle_transform(self, *slot_data_lists, policy_message, worker_state):
        input_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []

        for data_dict in input_data:
            if not isinstance(data_dict, dict):
                continue

            original_data = data_dict.get("data", "unknown")
            index = data_dict.get("index", 0)

            print(f"[DataTransformer] Transforming: {original_data}")
            transformed_data = f"transformed_{original_data}"
            print(f"[DataTransformer] Transformed to: {transformed_data}")

            self.emit(
                "output",
                worker_state=worker_state,
                data=transformed_data,
                index=index,
                transformed=True,
            )


class DataSink(Routine):
    """Receives and stores final results (sink routine for testing).

    Purpose:
        Simple sink routine that receives transformed data and stores it.
        Used as terminal node in test pipelines (data_source -> data_transformer -> data_sink).

    Configuration:
        None

    Input (via input slot):
        {
            "data": "transformed_item1",  # Transformed data
            "index": 1,                    # Item index
            "transformed": True            # Optional transformation marker
        }

    Output:
        None (sink routine, no events)

    Print Output:
        [DataSink] Received: transformed_item1 (index: 1)
    """

    def __init__(self):
        super().__init__()
        self.input_slot = self.add_slot("input")
        self.set_activation_policy(immediate_policy())
        self.set_logic(self._handle_sink)

    def _handle_sink(self, *slot_data_lists, policy_message, worker_state):
        input_data = slot_data_lists[0] if slot_data_lists and slot_data_lists[0] else []

        for data_dict in input_data:
            if not isinstance(data_dict, dict):
                continue

            data = data_dict.get("data", "unknown")
            index = data_dict.get("index", "N/A")
            print(f"[DataSink] Received: {data} (index: {index})")


# ===== Flows =====


def create_simple_pipeline_flow():
    """Simple linear flow: Echo -> Delay -> Printer

    Flow ID: simple_pipeline_flow
    Entry Point: echo.trigger

    Structure:
        EchoRoutine -> DelayRoutine -> SimplePrinter

    Use Case: Test basic event routing, delay functionality
    """
    from routilux.tools.factory import ObjectFactory

    factory = ObjectFactory.get_instance()
    flow = Flow(flow_id="simple_pipeline_flow")

    echo = factory.create("echo_routine", config={})
    delay = factory.create("delay_routine", config={"delay_ms": 1000})
    printer = factory.create("simple_printer", config={})

    echo_id = flow.add_routine(echo, "echo")
    delay_id = flow.add_routine(delay, "delay")
    printer_id = flow.add_routine(printer, "printer")

    flow.connect(echo_id, "output", delay_id, "input")
    flow.connect(delay_id, "output", printer_id, "input")

    return flow, echo_id


def create_batch_processing_flow():
    """Batch processing flow: Echo -> BatchProcessor -> Printer

    Flow ID: batch_processing_flow
    Entry Point: echo.trigger

    Structure:
        EchoRoutine -> BatchProcessor -> SimplePrinter

    Use Case: Test batch processing, demonstrate batch_size_policy
    """
    from routilux.tools.factory import ObjectFactory

    factory = ObjectFactory.get_instance()
    flow = Flow(flow_id="batch_processing_flow")

    echo = factory.create("echo_routine", config={})
    # BatchProcessor will update its activation policy when config is set
    batch_processor = factory.create("batch_processor", config={"batch_size": 3})
    printer = factory.create("simple_printer", config={})

    echo_id = flow.add_routine(echo, "echo")
    batch_id = flow.add_routine(batch_processor, "batch_processor")
    printer_id = flow.add_routine(printer, "printer")

    flow.connect(echo_id, "output", batch_id, "input")
    flow.connect(batch_id, "output", printer_id, "input")

    return flow, echo_id


def create_countdown_flow():
    """Countdown flow: CountdownTimer -> Printer

    Flow ID: countdown_flow
    Entry Point: countdown.trigger

    Structure:
        CountdownTimer -> SimplePrinter

    Use Case: Test routed stdout capture, progress display in UI
    """
    from routilux.tools.factory import ObjectFactory

    factory = ObjectFactory.get_instance()
    flow = Flow(flow_id="countdown_flow")

    countdown = factory.create("countdown_timer", config={})
    printer = factory.create("simple_printer", config={})

    countdown_id = flow.add_routine(countdown, "countdown")
    printer_id = flow.add_routine(printer, "printer")

    flow.connect(countdown_id, "tick", printer_id, "input")

    return flow, countdown_id


def create_loop_processing_flow():
    """Loop processing flow with exit condition: Echo -> DataProcessor -> LoopController -> (loop or exit)

    Flow ID: loop_processing_flow
    Entry Point: echo.trigger

    Structure:
        EchoRoutine -> DataProcessorRoutine -> LoopControllerRoutine -> (loop back to DataProcessor or exit to Printer)

    Loop Logic:
        - DataProcessor increments value by 1 each iteration
        - LoopController checks if value >= 10 or max_iterations reached
        - If condition met or max_iterations reached, exits to Printer
        - Otherwise, loops back to DataProcessor

    Use Case: Test loop processing with exit conditions
    """
    from routilux.tools.factory import ObjectFactory

    factory = ObjectFactory.get_instance()
    flow = Flow(flow_id="loop_processing_flow")

    echo = factory.create("echo_routine", config={})
    processor = factory.create(
        "data_processor",
        config={"code": "data['value'] = data.get('value', 0) + 1; result = data"},
    )
    loop_controller = factory.create(
        "loop_controller",
        config={"max_iterations": 10, "exit_condition": "data.get('value', 0) >= 10"},
    )
    printer = factory.create("simple_printer", config={})

    echo_id = flow.add_routine(echo, "echo")
    processor_id = flow.add_routine(processor, "processor")
    controller_id = flow.add_routine(loop_controller, "controller")
    printer_id = flow.add_routine(printer, "printer")

    # Initial flow: echo -> processor -> controller
    flow.connect(echo_id, "output", processor_id, "input")
    flow.connect(processor_id, "output", controller_id, "input")

    # Loop: controller.continue -> processor (loop back)
    flow.connect(controller_id, "continue", processor_id, "input")

    # Exit: controller.done -> printer
    flow.connect(controller_id, "done", printer_id, "input")

    return flow, echo_id


# ===== Main =====


def main():
    """Create and register all demo routines and flows"""
    print("=" * 80)
    print(" " * 20 + "Routilux Overseer - Simplified Demo")
    print("=" * 80)
    print("\nSimple, practical routines and flows for testing:")
    print("  ✓ Countdown timer with stdout output")
    print("  ✓ Batch processing with configurable size")
    print("  ✓ Simple pipeline flows")
    print("  ✓ Routed stdout testing")
    print("\n" + "=" * 80)

    # Enable monitoring BEFORE importing flow_store
    print("\n[1/5] Enabling monitoring...")
    MonitoringRegistry.enable()

    # Import AFTER enabling monitoring
    from routilux import Runtime
    from routilux.core.registry import FlowRegistry
    from routilux.monitoring.runtime_registry import RuntimeRegistry
    from routilux.monitoring.storage import flow_store
    from routilux.tools.factory import ObjectFactory, ObjectMetadata

    # Register runtimes in RuntimeRegistry
    print("\n[2/5] Registering runtimes in RuntimeRegistry...")
    runtime_registry = RuntimeRegistry.get_instance()

    # Create and register three runtimes for testing
    runtimes_to_create = [
        ("production", 0, True, "Production runtime using shared thread pool (recommended)"),
        ("development", 5, False, "Development runtime with small independent thread pool"),
        ("testing", 2, False, "Testing runtime with minimal thread pool for isolation"),
    ]

    for runtime_id, thread_pool_size, is_default, description in runtimes_to_create:
        runtime = Runtime(thread_pool_size=thread_pool_size)
        runtime_registry.register(runtime, runtime_id, is_default=is_default)
        pool_info = "shared pool" if thread_pool_size == 0 else f"{thread_pool_size} threads"
        default_info = " (default)" if is_default else ""
        print(f"  ✓ Registered: {runtime_id} ({pool_info}){default_info}")
        print(f"    {description}")

    # Register routines in factory
    print("\n[3/5] Registering routines in factory...")
    factory = ObjectFactory.get_instance()

    routine_registrations = [
        (
            "countdown_timer",
            CountdownTimer,
            "Countdown timer that emits progress events and prints to stdout",
            "testing",
            ["countdown", "timer", "stdout"],
        ),
        (
            "batch_processor",
            BatchProcessor,
            "Processes data in batches with configurable batch size",
            "processing",
            ["batch", "processor"],
        ),
        (
            "simple_printer",
            SimplePrinter,
            "Receives input and prints it (sink routine)",
            "sink",
            ["printer", "sink"],
        ),
        (
            "delay_routine",
            DelayRoutine,
            "Delays data transmission by configured milliseconds",
            "testing",
            ["delay", "timing"],
        ),
        (
            "echo_routine",
            EchoRoutine,
            "Simple echo - receives input and emits it unchanged",
            "testing",
            ["echo", "passthrough"],
        ),
        (
            "counter_routine",
            CounterRoutine,
            "Counts received messages and emits count",
            "testing",
            ["counter", "state"],
        ),
        (
            "filter_routine",
            FilterRoutine,
            "Filters data based on simple threshold condition",
            "processing",
            ["filter", "threshold"],
        ),
        (
            "data_processor",
            DataProcessorRoutine,
            "Generic data processing routine that executes code on input data",
            "processing",
            ["processor", "eval", "code"],
        ),
        (
            "loop_controller",
            LoopControllerRoutine,
            "Controls loop execution with exit condition",
            "control_flow",
            ["loop", "controller", "iteration"],
        ),
        (
            "data_source",
            DataSource,
            "Generates sample data for testing pipelines",
            "data_generation",
            ["source", "generator"],
        ),
        (
            "data_transformer",
            DataTransformer,
            "Transforms input data (simple transformation for testing)",
            "transformation",
            ["transformer", "processor"],
        ),
        (
            "data_sink",
            DataSink,
            "Receives and stores final results (sink routine for testing)",
            "sink",
            ["sink", "collector"],
        ),
    ]

    for name, routine_class, description, category, tags in routine_registrations:
        # Automatically extract docstring if available
        docstring = None
        if hasattr(routine_class, "__doc__") and routine_class.__doc__:
            docstring = routine_class.__doc__.strip()

        metadata = ObjectMetadata(
            name=name,
            description=description,
            category=category,
            tags=tags,
            example_config={},
            version="1.0.0",
            docstring=docstring,
        )
        factory.register(name, routine_class, metadata=metadata)
        print(f"  ✓ Registered: {name} ({category})")

    flows = []

    # Create all flows
    print("\n[4/5] Creating demo flows...")

    flows_to_create = [
        ("Simple Pipeline Flow", create_simple_pipeline_flow),
        ("Batch Processing Flow", create_batch_processing_flow),
        ("Countdown Flow", create_countdown_flow),
        ("Loop Processing Flow", create_loop_processing_flow),
    ]

    for i, (name, creator) in enumerate(flows_to_create, 1):
        print(f"\n  {i}. Creating {name}...")
        flow, entry = creator()
        flow_store.add(flow)
        FlowRegistry.get_instance().register(flow)
        flows.append((name, flow, entry))

        # Register flow in factory for API discovery
        flow_metadata = ObjectMetadata(
            name=flow.flow_id,
            description=f"{name} - {flow.flow_id}",
            category="demo",
            tags=["demo", "flow", flow.flow_id.split("_")[0]],
            example_config={},
            version="1.0.0",
        )
        factory.register(flow.flow_id, flow, metadata=flow_metadata)

        print(f"     ✓ Flow ID: {flow.flow_id}")
        print(f"     ✓ Routines: {len(flow.routines)} ({', '.join(flow.routines.keys())})")
        print(f"     ✓ Connections: {len(flow.connections)}")
        print(f"     ✓ Entry Point: {entry}")
        print("     ✓ Registered in factory")

    print("\n" + "=" * 80)
    print("[5/5] All flows created successfully!")
    print("=" * 80)
    print(f"\nTotal flows created: {len(flows)}")
    print("\nFlow Summary:")
    for name, flow, entry in flows:
        print(f"  • {name:25s} ({flow.flow_id})")
        print(f"    Routines: {len(flow.routines):2d} | Connections: {len(flow.connections):2d}")

    # Register flows in registry by name
    print("\n[5/5] Registering flows in registry...")
    registry = FlowRegistry.get_instance()
    for name, flow, entry in flows:
        # Use a clean name for registry
        registry_name = flow.flow_id.replace("_", "-")
        try:
            registry.register_by_name(registry_name, flow)
            print(f"  ✓ Registered flow: {registry_name}")
        except ValueError:
            # Already registered, skip
            pass

    # Print testing suggestions
    print("\n" + "=" * 80)
    print("Testing Scenarios")
    print("=" * 80)
    print("\n1️⃣  Simple Pipeline Flow - Basic event routing")
    print("   Create worker: POST /api/v1/workers")
    print('     {"flow_id": "simple_pipeline_flow"}')
    print("   Submit job: POST /api/v1/jobs")
    print(
        '     {"flow_id": "simple_pipeline_flow", "routine_id": "echo", "slot_name": "trigger", "data": {"data": "test"}}'
    )
    print("   Monitor: Data flows through echo -> delay -> printer")

    print("\n2️⃣  Batch Processing Flow - Batch processing")
    print("   Create worker: POST /api/v1/workers")
    print('     {"flow_id": "batch_processing_flow"}')
    print("   Submit multiple jobs: POST /api/v1/jobs")
    print(
        '     {"flow_id": "batch_processing_flow", "routine_id": "echo", "slot_name": "trigger", "data": {"data": "item1"}}'
    )
    print(
        '     {"flow_id": "batch_processing_flow", "routine_id": "echo", "slot_name": "trigger", "data": {"data": "item2"}}'
    )
    print(
        '     {"flow_id": "batch_processing_flow", "routine_id": "echo", "slot_name": "trigger", "data": {"data": "item3"}}'
    )
    print("   Monitor: Batch processor collects 3 items before processing")

    print("\n3️⃣  Countdown Flow - Routed stdout testing")
    print("   Create worker: POST /api/v1/workers")
    print('     {"flow_id": "countdown_flow"}')
    print("   Submit job: POST /api/v1/jobs")
    print(
        '     {"flow_id": "countdown_flow", "routine_id": "countdown", "slot_name": "trigger", "data": {"delay_ms": 5000}}'
    )
    print("   Monitor: Countdown prints progress, stdout captured by job")
    print("   API: GET /api/v1/jobs/{job_id}/output to see stdout")

    print("\n4️⃣  Loop Processing Flow - Loop with exit condition")
    print("   Create worker: POST /api/v1/workers")
    print('     {"flow_id": "loop_processing_flow"}')
    print("   Submit job: POST /api/v1/jobs")
    print(
        '     {"flow_id": "loop_processing_flow", "routine_id": "echo", "slot_name": "trigger", "data": {"value": 0}}'
    )
    print("   Monitor: DataProcessor increments value, LoopController checks exit condition")
    print("   Loop exits when value >= 10 or max_iterations (10) reached")

    print("\n📦 Factory Objects - Registered routines")
    print("   List: GET /api/factory/objects")
    print("   Details: GET /api/factory/objects/{name}")
    print("   Filter by category: GET /api/factory/objects?category=testing")

    print("\n⚙️  Runtime Management - Registered runtimes")
    print("   List: GET /api/runtimes")
    print("   Available runtimes:")
    for runtime_id, thread_pool_size, is_default, description in runtimes_to_create:
        default_marker = " (default)" if is_default else ""
        pool_info = "shared pool" if thread_pool_size == 0 else f"{thread_pool_size} threads"
        print(f"     • {runtime_id}: {description} ({pool_info}){default_marker}")

    # Start API server
    print("\n" + "=" * 80)
    print("Starting API Server...")
    print("=" * 80)
    print("\n📡 Server will start on: http://localhost:20555")
    print("🌐 Connect Overseer to: http://localhost:20555")
    print("\n💡 Quick Start:")
    print("   1. Open Overseer: http://localhost:3000")
    print("   2. Click 'Connect to Server'")
    print("   3. Enter: http://localhost:20555")
    print("   4. Click 'Connect'")
    print("   5. Explore Flows and start Jobs!")
    print("\n" + "=" * 80)
    print("Press Ctrl+C to stop the server")
    print("=" * 80 + "\n")

    # Start API server
    import uvicorn

    uvicorn.run(
        "routilux.server.main:app",
        host="0.0.0.0",
        port=20555,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
