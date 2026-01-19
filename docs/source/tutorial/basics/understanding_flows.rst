Understanding Flows
==================

A **Flow** is a container that manages multiple routines and their connections.
It's the orchestration layer that brings your workflow together, defining how
data moves between routines and when execution happens.

.. note:: **What You'll Learn**

   - How to create and configure flows
   - How to add routines to flows
   - How to connect routines together
   - How to register flows with FlowRegistry
   - Flow lifecycle and execution patterns

.. note:: **Prerequisites**

   - :doc:`understanding_routines` - Understand Routines first
   - :doc:`understanding_slots_events` - Understand slots and events

What is a Flow?
---------------

A **Flow** is a workflow orchestrator that:

- **Contains** multiple routines
- **Connects** routines via event-slot connections
- **Manages** execution lifecycle
- **Tracks** routine states and execution history
- **Handles** errors and debugging

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                        Flow                                  │
   │                                                              │
   │  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
   │  │Routine A │───▶│Routine B │───▶│Routine C │              │
   │  │          │    │          │    │          │              │
   │  │ Slot: in │    │ Slot: in │    │ Slot: in │              │
   │  │Event:out│    │Event:out │    │Event:out │              │
   │  └──────────┘    └──────────┘    └──────────┘              │
   │       │               │               │                    │
   │       └───────────────┴───────────────┴───────▶ Runtime     │
   │                        Connections                         │
   └─────────────────────────────────────────────────────────────┘

Creating a Flow
---------------

Basic flow creation:

.. code-block:: python
   :linenos:

   from routilux import Flow

   # Create a flow with a unique ID
   flow = Flow("my_workflow")

   # Create with custom timeout
   flow = Flow(
       flow_id="my_workflow",
       execution_timeout=60.0  # 60 seconds
   )

**Flow Parameters**:

- ``flow_id``: Unique identifier (auto-generated if not provided)
- ``execution_timeout``: Default timeout for execution in seconds (default: 300)

.. note:: **Flow ID Requirements**

   Flow IDs must be unique when registering with FlowRegistry. Use descriptive
   names that reflect the workflow's purpose:

   .. code-block:: python

      # Good - Descriptive
      Flow("user_registration_pipeline")
      Flow("data_processing_batch")
      Flow("email_notification_service")

      # Avoid - Too generic
      Flow("flow1")
      Flow("my_flow")
      Flow("workflow")

Adding Routines
---------------

Add routines to a flow with unique IDs:

.. code-block:: python

   from routilux import Routine, Flow
   from routilux.activation_policies import immediate_policy

   class DataSource(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("data", ["value"])

           def generate(slot_data, policy_message, worker_state):
               self.emit("data", value=42)

           self.set_logic(generate)
           self.set_activation_policy(immediate_policy())

   class DataProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("result", ["processed"])

           def process(slot_data, policy_message, worker_state):
               data_list = slot_data.get("input", [])
               if data_list:
                   value = data_list[0].get("value", 0)
                   self.emit("result", processed=value * 2)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Create flow
   flow = Flow("data_pipeline")

   # Add routines with unique IDs
   flow.add_routine(DataSource(), "source")
   flow.add_routine(DataProcessor(), "processor")

.. tip:: **Routine ID Naming**

   Use lowercase, descriptive names for routine IDs:

   - ``source`` / ``sink`` for entry/exit points
   - ``processor`` / ``transformer`` for data processing
   - ``validator`` / ``checker`` for validation
   - ``aggregator`` / ``collector`` for combining data

.. warning:: **Pitfall: Duplicate Routine IDs**

   Adding a routine with an existing ID raises ``ValueError``:

   .. code-block:: python

      flow.add_routine(DataSource(), "source")
      flow.add_routine(DataProcessor(), "source")  # ValueError!

   **Solution**: Use unique IDs for each routine.

Connecting Routines
-------------------

Connections define how data flows between routines:

.. code-block:: python
   :linenos:

   # Connect: source's "data" event → processor's "input" slot
   flow.connect(
       "source",     # Source routine ID
       "data",       # Source event name
       "processor",  # Destination routine ID
       "input"       # Destination slot name
   )

**Connection Syntax**:

.. code-block:: python

   flow.connect(
       source_routine_id,   # Which routine sends the data
       source_event,        # Which event to connect
       dest_routine_id,     # Which routine receives the data
       dest_slot            # Which slot receives the data
   )

.. note:: **Connection Validation**

   Flow validates connections when they're created:

   - Source routine must exist in the flow
   - Source event must exist on the source routine
   - Destination routine must exist in the flow
   - Destination slot must exist on the destination routine

   If any validation fails, ``ValueError`` is raised immediately.

**Multiple Connections**:

A routine can have multiple input and output connections:

.. code-block:: python

   flow = Flow("multi_connection")

   # Add routines
   flow.add_routine(Splitter(), "splitter")
   flow.add_routine(ProcessA(), "process_a")
   flow.add_routine(ProcessB(), "process_b")
   flow.add_routine(Merger(), "merger")

   # Fan-out: splitter → multiple processors
   flow.connect("splitter", "output_a", "process_a", "input")
   flow.connect("splitter", "output_b", "process_b", "input")

   # Fan-in: multiple processors → merger
   flow.connect("process_a", "result", "merger", "input_a")
   flow.connect("process_b", "result", "merger", "input_b")

.. code-block:: text

   Diagram:
                    ┌──────────┐
                    │ Splitter │
                    └─────┬────┘
                  ┌───────┴───────┐
                  ▼               ▼
            ┌──────────┐    ┌──────────┐
            │Process A │    │Process B │
            └─────┬────┘    └─────┬────┘
                  │               │
                  └───────┬───────┘
                          ▼
                    ┌──────────┐
                    │  Merger  │
                    └──────────┘

Flow Registration
-----------------

Before executing a flow, it must be registered with **FlowRegistry**:

.. code-block:: python

   from routilux.monitoring.flow_registry import FlowRegistry

   # Get the registry singleton
   registry = FlowRegistry.get_instance()

   # Register by name (for runtime.exec() lookup)
   registry.register_by_name("my_workflow", flow)

   # Or register directly (auto-generates ID)
   registry.register(flow)

.. danger:: **CRITICAL: Always Register Flows**

   Forgetting to register flows causes ``ValueError`` when calling
   ``runtime.exec()``:

   .. code-block:: python

      flow = Flow("my_workflow")
      # Missing: FlowRegistry.get_instance().register_by_name("my_workflow", flow)

      runtime = Runtime()
      runtime.exec("my_workflow")  # ValueError: Flow not found!

.. tip:: **Registration Best Practice**

   Always register immediately after creating the flow:

   .. code-block:: python

      def create_and_register_flow():
          flow = Flow("my_workflow")
          # ... add routines and connections ...
          FlowRegistry.get_instance().register_by_name("my_workflow", flow)
          return flow

Complete Example: ETL Pipeline
-------------------------------

Here's a complete example showing flow creation with multiple stages:

.. code-block:: python
   :linenos:
   :name: understanding_flows_etl

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   # Extract: Read data from source
   class Extractor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("raw_data", ["records"])

           def extract(slot_data, policy_message, worker_state):
               # Simulate data extraction
               records = [
                   {"id": 1, "name": "Alice", "score": 85},
                   {"id": 2, "name": "Bob", "score": 92},
                   {"id": 3, "name": "Charlie", "score": 78},
               ]
               print(f"Extracted {len(records)} records")
               self.emit("raw_data", records=records)

           self.set_logic(extract)
           self.set_activation_policy(immediate_policy())

   # Transform: Clean and enrich data
   class Transformer(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("raw")
           self.add_event("clean_data", ["records"])

           def transform(slot_data, policy_message, worker_state):
               data_list = slot_data.get("raw", [])
               if data_list:
                   raw_records = data_list[0].get("records", [])
                   # Transform: add grade, normalize names
                   clean_records = []
                   for record in raw_records:
                       score = record.get("score", 0)
                       grade = "A" if score >= 90 else "B" if score >= 80 else "C"
                       clean_records.append({
                           "id": record.get("id"),
                           "name": record.get("name", "").strip().title(),
                           "score": score,
                           "grade": grade
                       })
                   print(f"Transformed {len(clean_records)} records")
                   self.emit("clean_data", records=clean_records)

           self.set_logic(transform)
           self.set_activation_policy(immediate_policy())

   # Load: Write data to destination
   class Loader(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("clean")

           def load(slot_data, policy_message, worker_state):
               data_list = slot_data.get("clean", [])
               if data_list:
                   records = data_list[0].get("records", [])
                   # Simulate writing to database
                   print(f"Loaded {len(records)} records:")
                   for record in records:
                       print(f"  - {record['name']}: {record['grade']} ({record['score']})")

           self.set_logic(load)
           self.set_activation_policy(immediate_policy())

   # Build ETL pipeline
   etl_flow = Flow("etl_pipeline")

   etl_flow.add_routine(Extractor(), "extract")
   etl_flow.add_routine(Transformer(), "transform")
   etl_flow.add_routine(Loader(), "load")

   # Connect stages: Extract → Transform → Load
   etl_flow.connect("extract", "raw_data", "transform", "raw")
   etl_flow.connect("transform", "clean_data", "load", "clean")

   # Register flow
   FlowRegistry.get_instance().register_by_name("etl_pipeline", etl_flow)

   # Execute
   with Runtime(thread_pool_size=3) as runtime:
       runtime.post("etl_pipeline", "extract", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Extracted 3 records
   Transformed 3 records
   Loaded 3 records:
     - Alice: B (85)
     - Bob: A (92)
     - Charlie: C (78)

Flow Configuration
------------------

Flows support several configuration options:

**Execution Timeout**:

.. code-block:: python

   # Set timeout for flow execution
   flow = Flow("my_flow", execution_timeout=30.0)  # 30 seconds

   # Update timeout after creation
   flow.execution_timeout = 60.0

**Error Handler**:

.. code-block:: python

   from routilux.core.error import ErrorHandler, ErrorStrategy

   class MyErrorHandler(ErrorHandler):
       def handle_error(self, error, routine_id, slot_data):
           print(f"Error in {routine_id}: {error}")
           return ErrorStrategy.CONTINUE

   flow.error_handler = MyErrorHandler()

.. note:: **Error Handling**

   See :doc:`../error_handling/error_strategies` for detailed error handling
   patterns.

Flow Inspection
---------------

Flows provide methods for inspection:

.. code-block:: python

   # Get all routines
   routines = flow.routines  # dict[routine_id, Routine]

   # Get all connections
   connections = flow.connections  # list[Connection]

   # Get connections for a specific routine
   source = flow.routines["source"]
   output_conns = flow.get_connections_for_event(source.get_event("output"))

   # Get routine ID from routine object
   routine_id = flow._get_routine_id(my_routine)

Flow Lifecycle
--------------

A flow goes through these stages:

.. code-block:: text

   1. Created    → Flow("my_flow")
   2. Built      → Add routines, make connections
   3. Registered → FlowRegistry.register_by_name()
   4. Executed   → Runtime.exec("my_flow")
   5. Running    → Worker processing jobs
   6. Completed  → All jobs finished

**State Tracking**:

Flows don't track execution state themselves—that's handled by **WorkerState**.
Each execution of a flow creates a new WorkerState instance.

.. note:: **Flow vs WorkerState**

   - **Flow**: The workflow definition (routines, connections)
   - **WorkerState**: An execution instance (status, history)

   One Flow can have multiple concurrent WorkerState instances running.

Common Patterns
---------------

**Pattern 1: Linear Pipeline**

.. code-block:: python

   flow = Flow("pipeline")
   flow.add_routine(Stage1(), "stage1")
   flow.add_routine(Stage2(), "stage2")
   flow.add_routine(Stage3(), "stage3")

   flow.connect("stage1", "output", "stage2", "input")
   flow.connect("stage2", "output", "stage3", "input")

**Pattern 2: Fan-Out/Fan-In**

.. code-block:: python

   flow = Flow("scatter_gather")
   flow.add_routine(Producer(), "producer")
   flow.add_routine(Worker1(), "worker1")
   flow.add_routine(Worker2(), "worker2")
   flow.add_routine(Aggregator(), "aggregator")

   # Fan-out
   flow.connect("producer", "data", "worker1", "input")
   flow.connect("producer", "data", "worker2", "input")

   # Fan-in
   flow.connect("worker1", "result", "aggregator", "results")
   flow.connect("worker2", "result", "aggregator", "results")

**Pattern 3: Conditional Routing**

.. code-block:: python

   flow = Flow("router")
   flow.add_routine(Source(), "source")
   flow.add_routine(Router(), "router")
   flow.add_routine(HighPriorityHandler(), "high")
   flow.add_routine(LowPriorityHandler(), "low")

   flow.connect("source", "data", "router", "input")
   flow.connect("router", "high_priority", "high", "input")
   flow.connect("router", "low_priority", "low", "input")

Pitfalls Reference
------------------

.. list-table:: Common Flow Pitfalls
   :widths: 50 50
   :header-rows: 1

   * - Pitfall
     - Solution
   * - Forgetting to register flow
     - Always call ``FlowRegistry.register_by_name()``
   * - Duplicate routine IDs
     - Use unique IDs for each routine
   * - Wrong connection order
     - ``connect(source_id, event, dest_id, slot)``
   * - Non-existent event/slot
     - Verify event/slot names before connecting
   * - Setting timeout after execution
     - Set timeout before calling ``runtime.exec()``
   * - Mixing up flow_id and routine_id
     - ``flow_id`` identifies flow, ``routine_id`` identifies routine within flow

Next Steps
----------

Now that you understand Flows, learn about:

- :doc:`understanding_runtime` - Executing flows with Runtime
- :doc:`../connections/complex_patterns` - Advanced connection patterns
- :doc:`../error_handling/error_strategies` - Handling errors in flows
- :doc:`../advanced/flow_builder` - Declarative flow construction

.. seealso::

   :doc:`../../api_reference/core/flow`
      Complete Flow API reference

   :doc:`../../user_guide/flows`
      Comprehensive flow usage guide
