#!/usr/bin/env python
"""
Basic Example: Simple data processing flow

This example demonstrates:
- Creating routines with slots and events
- Using activation policies and logic functions
- Connecting routines in a flow
- Registering flows with FlowRegistry
- Executing a flow using Runtime
- Checking execution status
"""

from routilux import Flow, Routine
from routilux.activation_policies import immediate_policy
from routilux.monitoring.flow_registry import FlowRegistry
from routilux.runtime import Runtime


class DataSource(Routine):
    """A routine that generates data"""

    def __init__(self):
        super().__init__()
        self.trigger = self.define_slot("trigger")
        self.output = self.define_event("output", ["data"])

        def my_logic(slot_data, policy_message, job_state):
            """Handle trigger and emit data through the output event"""
            # Extract data from trigger
            trigger_list = slot_data.get("trigger", [])
            data = trigger_list[0].get("data", "default_data") if trigger_list else "default_data"

            # Emit the result
            self.emit("output", data=data)

        self.set_logic(my_logic)
        self.set_activation_policy(immediate_policy())


class DataProcessor(Routine):
    """A routine that processes data"""

    def __init__(self):
        super().__init__()
        self.input = self.define_slot("input")
        self.output = self.define_event("output", ["result"])

        def my_logic(slot_data, policy_message, job_state):
            """Process incoming data"""
            # Extract data from input slot
            input_list = slot_data.get("input", [])
            if input_list:
                data_value = input_list[0].get("data", "")
            else:
                data_value = ""

            # Process the data
            processed_data = f"Processed: {data_value}"

            # Store in JobState
            job_state.update_routine_state("processor", {"processed": processed_data})

            # Emit the result
            self.emit("output", result=processed_data)

        self.set_logic(my_logic)
        self.set_activation_policy(immediate_policy())


class DataSink(Routine):
    """A routine that receives final data"""

    def __init__(self):
        super().__init__()
        self.input = self.define_slot("input")

        def my_logic(slot_data, policy_message, job_state):
            """Receive and store the final result"""
            # Extract data from input slot
            input_list = slot_data.get("input", [])
            if input_list:
                result_value = input_list[0].get("result", "")
            else:
                result_value = None

            # Store in JobState
            job_state.update_routine_state("sink", {"final_result": result_value})
            print(f"Final result: {result_value}")

        self.set_logic(my_logic)
        self.set_activation_policy(immediate_policy())


def main():
    """Main function"""
    # Create a flow
    flow = Flow(flow_id="basic_example")

    # Create routine instances
    source = DataSource()
    processor = DataProcessor()
    sink = DataSink()

    # Add routines to the flow
    flow.add_routine(source, "source")
    flow.add_routine(processor, "processor")
    flow.add_routine(sink, "sink")

    # Connect routines: source -> processor -> sink
    flow.connect("source", "output", "processor", "input")
    flow.connect("processor", "output", "sink", "input")

    # Register flow with FlowRegistry
    registry = FlowRegistry.get_instance()
    registry.register_by_name("basic_example", flow)

    # Create runtime and execute
    print("Executing flow...")
    with Runtime(thread_pool_size=5) as runtime:
        job_state = runtime.exec("basic_example", entry_params={"data": "Hello, World!"})

        # Wait for execution to complete
        runtime.wait_until_all_jobs_finished(timeout=5.0)

        # Check results
        print(f"\nExecution Status: {job_state.status}")

        sink_state = job_state.get_routine_state("sink", {})
        final_result = sink_state.get("final_result")
        print(f"Final Result: {final_result}")
        print(f"Execution History: {len(job_state.execution_history)} records")

        assert job_state.status.name in ["completed", "failed", "running"]
        if final_result:
            assert final_result == "Processed: Hello, World!"


if __name__ == "__main__":
    main()
