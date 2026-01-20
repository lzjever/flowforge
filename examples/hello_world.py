#!/usr/bin/env python
"""Hello World - Minimal Routilux example.

This example demonstrates the basic concepts of Routilux:
- Creating a Routine with slots and events
- Creating a Flow and adding routines
- Registering flows with FlowRegistry
- Executing with Runtime
"""

from routilux import Flow, FlowRegistry, Routine, Runtime
from routilux.activation_policies import immediate_policy


class HelloWorld(Routine):
    """A simple routine that prints a greeting."""

    def __init__(self):
        super().__init__()
        # Add an input slot
        self.add_slot("trigger")
        # Add an output event
        self.add_event("greeting", ["message"])

        def say_hello(slot_data, policy_message, worker_state):
            # Print the greeting
            print("Hello, World!")
            # Emit the greeting event
            self.emit("greeting", message="Hello, World!")

        # Set the logic function and activation policy
        self.set_logic(say_hello)
        self.set_activation_policy(immediate_policy())


def main():
    """Run the hello world example."""
    # Create a flow
    flow = Flow("hello_flow")

    # Add the routine to the flow
    flow.add_routine(HelloWorld(), "greeter")

    # Register the flow with FlowRegistry (REQUIRED!)
    FlowRegistry.get_instance().register_by_name("hello_flow", flow)

    # Create a runtime and execute
    with Runtime(thread_pool_size=2) as runtime:
        # Start the flow
        runtime.exec("hello_flow")

        # Trigger the routine by sending data to its slot
        runtime.post("hello_flow", "greeter", "trigger", {})

        # Wait for all jobs to complete
        runtime.wait_until_all_jobs_finished(timeout=5.0)

    print("\nDone!")


if __name__ == "__main__":
    main()
