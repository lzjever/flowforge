#!/usr/bin/env python
"""
Basic Example: Simple data processing flow

This example demonstrates:
- Creating routines with slots and events
- Connecting routines in a flow
- Executing a flow
- Checking execution status
"""

from routilux import Flow, Routine


class DataSource(Routine):
    """A routine that generates data"""

    def __init__(self):
        super().__init__()
        # Define trigger slot for entry routine
        self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
        self.output_event = self.define_event("output", ["data"])

    def _handle_trigger(self, data=None, **kwargs):
        """Handle trigger and emit data through the output event"""
        # Extract data from kwargs if not provided directly
        output_data = data or kwargs.get("data", "default_data")
        # Execution state should be stored in JobState, not routine._stats
        self.emit("output", data=output_data)


class DataProcessor(Routine):
    """A routine that processes data"""

    def __init__(self):
        super().__init__()
        self.input_slot = self.define_slot("input", handler=self.process)
        self.output_event = self.define_event("output", ["result"])
        self.processed_data = None

    def process(self, data):
        """Process incoming data"""
        # Handle both dict and direct value
        if isinstance(data, dict):
            data_value = data.get("data", data)
        else:
            data_value = data

        # Process the data
        self.processed_data = f"Processed: {data_value}"
        # Execution state should be stored in JobState, not routine._stats

        # Emit the result
        self.emit("output", result=self.processed_data)


class DataSink(Routine):
    """A routine that receives final data"""

    def __init__(self):
        super().__init__()
        self.input_slot = self.define_slot("input", handler=self.receive)
        self.final_result = None

    def receive(self, result):
        """Receive and store the final result"""
        # Handle both dict and direct value
        if isinstance(result, dict):
            result_value = result.get("result", result)
        else:
            result_value = result

        self.final_result = result_value
        # Execution state should be stored in JobState, not routine._stats
        print(f"Final result: {self.final_result}")


def main():
    """Main function"""
    # Create a flow
    flow = Flow(flow_id="basic_example")

    # Create routine instances
    source = DataSource()
    processor = DataProcessor()
    sink = DataSink()

    # Add routines to the flow
    source_id = flow.add_routine(source, "source")
    processor_id = flow.add_routine(processor, "processor")
    sink_id = flow.add_routine(sink, "sink")

    # Connect routines: source -> processor -> sink
    flow.connect(source_id, "output", processor_id, "input")
    flow.connect(processor_id, "output", sink_id, "input")

    # Execute the flow
    print("Executing flow...")
    job_state = flow.execute(source_id, entry_params={"data": "Hello, World!"})

    # Wait for execution to complete
    from routilux.core import WorkerState

    JobState.wait_for_completion(flow, job_state, timeout=2.0)

    # Check results
    print(f"\nExecution Status: {job_state.status}")
    print(f"Final Result: {sink.final_result}")
    # Execution state is tracked in JobState, not routine._stats
    print(f"Execution History: {len(job_state.execution_history)} records")

    assert job_state.status == "completed"
    assert sink.final_result == "Processed: Hello, World!"


if __name__ == "__main__":
    main()
