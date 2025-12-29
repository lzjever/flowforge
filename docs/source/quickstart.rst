Quick Start Guide
=================

This guide will help you get started with Routilux quickly. We'll cover everything from
basic concepts to advanced features, with practical examples you can run immediately.

Installation
------------

Install Routilux using pip:

.. code-block:: bash

   pip install routilux

For development with all dependencies:

.. code-block:: bash

   pip install routilux[dev]

Basic Concepts
--------------

Routilux is built around a few simple concepts:

* **Routine**: A unit of work that can receive input through slots and emit output through events
* **Flow**: A manager that orchestrates multiple routines and their connections
* **Event**: An output mechanism that can be connected to slots
* **Slot**: An input mechanism that can receive data from events
* **Connection**: A link between an event and a slot

Creating Your First Routine
----------------------------

Let's create a simple routine that processes data:

.. code-block:: python

   from routilux import Routine

   class DataProcessor(Routine):
       def __init__(self):
           super().__init__()
           # Define an input slot with a handler
           self.input_slot = self.define_slot("input", handler=self.process_data)
           # Define an output event
           self.output_event = self.define_event("output", ["result"])
       
       def process_data(self, data=None, **kwargs):
           # Extract input data using helper method
           extracted_data = self._extract_input_data(data, **kwargs)
           
           # Process the data
           result = f"Processed: {extracted_data}"
           
           # Track operation statistics
           self._track_operation("processing", success=True)
           
           # Emit the result (flow is automatically detected)
           self.emit("output", result=result)

Creating a Flow
---------------

Now let's create a flow and connect routines:

.. code-block:: python

   from routilux import Flow

   # Create a flow
   flow = Flow(flow_id="my_flow")
   
   # Create routine instances
   processor1 = DataProcessor()
   processor2 = DataProcessor()
   
   # Add routines to the flow
   id1 = flow.add_routine(processor1, "processor1")
   id2 = flow.add_routine(processor2, "processor2")
   
   # Connect processor1's output to processor2's input
   flow.connect(id1, "output", id2, "input")

Executing a Flow
----------------

Execute the flow with entry parameters:

.. code-block:: python

   # Execute the flow
   job_state = flow.execute(id1, entry_params={"data": "test"})
   
   # Check the status
   print(job_state.status)  # "completed"
   
   # Check statistics
   print(processor1.stats())  # {"processing": {"success": 1, "total": 1}}

Using Built-in Routines
-----------------------

Routilux comes with many built-in routines ready to use. Let's use ``TextClipper`` to clip text:

.. code-block:: python

   from routilux import Flow
   from routilux.builtin_routines import TextClipper, TextRenderer

   flow = Flow()
   
   # Create and configure built-in routines
   renderer = TextRenderer()
   renderer.set_config(tag_format="xml")
   
   clipper = TextClipper()
   clipper.set_config(max_length=100)
   
   # Add to flow
   renderer_id = flow.add_routine(renderer, "renderer")
   clipper_id = flow.add_routine(clipper, "clipper")
   
   # Connect: renderer -> clipper
   flow.connect(renderer_id, "output", clipper_id, "input")
   
   # Execute
   data = {"name": "Alice", "age": 30, "city": "New York"}
   renderer.input_slot.receive({"data": data})
   
   # Get clipped result
   print(clipper.get_stat("clipped_text"))

Using Conditional Router
------------------------

``ConditionalRouter`` lets you route data based on conditions:

.. code-block:: python

   from routilux import Flow
   from routilux.builtin_routines import ConditionalRouter

   flow = Flow()
   
   router = ConditionalRouter()
   router.set_config(
       routes=[
           ("high", "data.get('priority', 0) > 10"),
           ("normal", "data.get('priority', 0) <= 10"),
       ],
       default_route="normal"
   )
   
   router_id = flow.add_routine(router, "router")
   
   # Define output events
   router.define_event("high")
   router.define_event("normal")
   
   # Connect to different handlers
   # flow.connect(router_id, "high", high_handler_id, "input")
   # flow.connect(router_id, "normal", normal_handler_id, "input")
   
   # Route data
   router.input_slot.receive({"data": {"priority": 15}})  # Routes to "high"

Merge Strategies
----------------

When multiple events connect to the same slot, you can control how data is merged:

.. code-block:: python

   from routilux import Routine

   class Aggregator(Routine):
       def __init__(self):
           super().__init__()
           # Use "append" strategy to accumulate data
           self.input_slot = self.define_slot(
               "input",
               handler=self.aggregate,
               merge_strategy="append"  # Accumulates data in lists
           )
       
       def aggregate(self, **kwargs):
           # Access accumulated data
           data = self.input_slot._data
           print(f"Aggregated: {data}")

**Available Merge Strategies**:

* **"override"** (default): New data replaces old data
* **"append"**: Values are appended to lists
* **Custom function**: Define your own merge logic

See :doc:`user_guide/connections` for details.

Concurrent Execution
--------------------

For I/O-bound operations, use concurrent execution to run multiple routines in parallel:

.. code-block:: python

   from routilux import Flow

   # Create a concurrent flow
   flow = Flow(
       execution_strategy="concurrent",
       max_workers=5
   )
   
   # Add routines (they'll execute concurrently when possible)
   # ...
   
   try:
       # Execute - routines run in parallel
       job_state = flow.execute(entry_routine_id, entry_params={"data": "test"})
       
       # Wait for all concurrent tasks to complete
       flow.wait_for_completion(timeout=10.0)
   finally:
       # Always clean up resources
       flow.shutdown(wait=True)

**Key Points**:

* Routines that can run in parallel execute concurrently automatically
* Use ``wait_for_completion()`` to ensure all tasks finish
* Always call ``shutdown()`` to clean up thread pool
* Thread-safe operations required for shared state

See :doc:`user_guide/flows` for detailed execution order behavior.

Error Handling
--------------

Configure error handling strategies for robust workflows:

.. code-block:: python

   from routilux import Flow, ErrorHandler, ErrorStrategy

   flow = Flow()
   
   # Set error handler with retry strategy
   error_handler = ErrorHandler(
       strategy=ErrorStrategy.RETRY,
       max_retries=3,
       retry_delay=1.0
   )
   flow.set_error_handler(error_handler)
   
   # Execute - errors will be retried automatically
   job_state = flow.execute(entry_routine_id)

**Available Strategies**:

* **STOP**: Stop execution on error (default)
* **CONTINUE**: Continue execution, log error
* **RETRY**: Retry failed routine up to max_retries
* **SKIP**: Skip failed routine, continue with next

See :doc:`user_guide/error_handling` for details.

State Management
----------------

Track routine state using the ``_stats`` dictionary:

.. code-block:: python

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.input_slot = self.define_slot("input", handler=self.process)
       
       def process(self, data):
           # Track operations
           self._track_operation("processing", success=True)
           
           # Set custom stats
           self.set_stat("last_processed", data)
           self.increment_stat("total_processed")
           
           # Access stats
           total = self.get_stat("total_processed", 0)
           print(f"Total processed: {total}")
       
       def get_summary(self):
           return {
               "total": self.get_stat("total_processed", 0),
               "last": self.get_stat("last_processed"),
               "stats": self.stats()
           }

**Helper Methods**:

* ``set_stat(key, value)``: Set a stat value
* ``get_stat(key, default=None)``: Get a stat value
* ``increment_stat(key, amount=1)``: Increment a stat
* ``_track_operation(name, success=True)``: Track operation statistics
* ``stats()``: Get all statistics

See :doc:`user_guide/state_management` for details.

Serialization
-------------

Serialize and deserialize flows for persistence:

.. code-block:: python

   from routilux import Flow
   import json

   # Create and configure flow
   flow = Flow(flow_id="my_flow")
   # ... add routines and connections ...
   
   # Serialize
   flow_data = flow.serialize()
   
   # Save to file
   with open("flow.json", "w") as f:
       json.dump(flow_data, f, indent=2)
   
   # Load and deserialize
   with open("flow.json", "r") as f:
       flow_data = json.load(f)
   
   new_flow = Flow.deserialize(flow_data)
   
   # Execute deserialized flow
   job_state = new_flow.execute(entry_routine_id)

**Important**: All routines must have no-argument constructors for serialization to work.
Use ``_config`` dictionary for configuration instead of constructor parameters.

See :doc:`user_guide/serialization` for details.

Aggregation Pattern
-------------------

Collect data from multiple sources before processing:

.. code-block:: python

   class ResultAggregator(Routine):
       def __init__(self, expected_count=3):
           super().__init__()
           self.expected_count = expected_count
           self.input_slot = self.define_slot(
               "input",
               handler=self._handle_input,
               merge_strategy="append"  # Accumulate data
           )
           self.output_event = self.define_event("output", ["results"])
       
       def _handle_input(self, **kwargs):
           # Check if we have enough data
           count = self.get_stat("message_count", 0) + 1
           self.set_stat("message_count", count)
           
           if count >= self.expected_count:
               # Process all accumulated data
               results = self.input_slot._data
               self.emit("output", results=results)
               # Reset for next batch
               self.input_slot._data = {}
               self.reset_stats()

This pattern is useful for:
* Collecting results from multiple parallel operations
* Batching data for batch processing
* Aggregating metrics from multiple sources

See :doc:`user_guide/aggregation_pattern` for details.

Complete Example
----------------

Here's a complete example combining multiple features:

.. code-block:: python

   from routilux import Flow, Routine
   from routilux.builtin_routines import TextRenderer, ConditionalRouter
   from routilux import ErrorHandler, ErrorStrategy

   # Define custom routine
   class DataValidator(Routine):
       def __init__(self):
           super().__init__()
           self.input_slot = self.define_slot("input", handler=self.validate)
           self.output_event = self.define_event("output", ["data", "valid"])
       
       def validate(self, data):
           is_valid = isinstance(data, dict) and "value" in data
           self._track_operation("validation", success=is_valid)
           self.emit("output", data=data, valid=is_valid)

   # Create flow
   flow = Flow(flow_id="complete_example")
   
   # Add error handler
   flow.set_error_handler(ErrorHandler(strategy=ErrorStrategy.CONTINUE))
   
   # Create routines
   validator = DataValidator()
   renderer = TextRenderer()
   router = ConditionalRouter()
   
   validator_id = flow.add_routine(validator, "validator")
   renderer_id = flow.add_routine(renderer, "renderer")
   router_id = flow.add_routine(router, "router")
   
   # Configure router
   router.set_config(routes=[
       ("valid", "data.get('valid') == True"),
       ("invalid", "data.get('valid') == False"),
   ])
   router.define_event("valid")
   router.define_event("invalid")
   
   # Connect: validator -> renderer, validator -> router
   flow.connect(validator_id, "output", renderer_id, "input")
   flow.connect(validator_id, "output", router_id, "input")
   
   # Execute
   job_state = flow.execute(validator_id, entry_params={"data": {"value": 42}})
   
   print(f"Status: {job_state.status}")
   print(f"Validator stats: {validator.stats()}")

Next Steps
----------

* :doc:`user_guide/index` - Comprehensive user guide with detailed explanations
* :doc:`user_guide/builtin_routines` - Explore all built-in routines
* :doc:`user_guide/flows` - Deep dive into flow execution and strategies
* :doc:`user_guide/connections` - Learn about merge strategies and parameter mapping
* :doc:`api_reference/index` - Complete API documentation
* :doc:`examples/index` - Real-world examples and use cases

Tips for Success
----------------

* **Start Simple**: Begin with basic routines and flows, then add complexity
* **Use Built-ins**: Leverage built-in routines before creating custom ones
* **Track Operations**: Use ``_track_operation()`` for consistent statistics
* **Handle Errors**: Always configure error handling for production workflows
* **Test Serialization**: Verify your flows can be serialized/deserialized
* **Monitor Stats**: Use ``stats()`` to understand routine behavior
* **Read Documentation**: Check the user guide for advanced features

Happy coding with Routilux! 🚀
