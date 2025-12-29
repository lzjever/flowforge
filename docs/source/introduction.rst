Introduction
============

Routilux is a powerful, event-driven workflow orchestration framework designed for building
flexible and maintainable data processing pipelines. With its intuitive slot-and-event mechanism,
Routilux makes it easy to connect routines, manage state, and orchestrate complex workflows
while maintaining clean separation of concerns.

Why Routilux?
--------------

Building workflow-based applications can be challenging. You need to:

* **Connect components** in flexible ways (one-to-many, many-to-one, many-to-many)
* **Manage state** across multiple processing steps
* **Handle errors** gracefully with retry, skip, or continue strategies
* **Track execution** for debugging and monitoring
* **Scale** with concurrent execution for I/O-bound operations
* **Persist** workflows for recovery and resumption

Routilux addresses all these needs with a clean, Pythonic API that feels natural to use.

What Makes Routilux Special?
------------------------------

**🎯 Event-Driven Architecture**

Routilux uses a clear slot-and-event mechanism where routines communicate through well-defined
interfaces. This makes your workflows easy to understand, test, and maintain.

.. code-block:: python

   class DataProcessor(Routine):
       def __init__(self):
           super().__init__()
           # Define input slot
           self.input_slot = self.define_slot("input", handler=self.process)
           # Define output event
           self.output_event = self.define_event("output", ["result"])
       
       def process(self, data):
           result = f"Processed: {data}"
           self.emit("output", result=result)

**🔗 Flexible Connections**

Connect routines in any pattern you need - one-to-many, many-to-one, or complex branching patterns.
Routilux handles the complexity while you focus on your business logic.

.. code-block:: python

   # One event to multiple slots
   flow.connect(source_id, "output", processor1_id, "input")
   flow.connect(source_id, "output", processor2_id, "input")
   
   # Multiple events to one slot (with merge strategy)
   flow.connect(source1_id, "output", aggregator_id, "input")
   flow.connect(source2_id, "output", aggregator_id, "input")

**📊 Built-in Routines**

Routilux comes with a rich set of built-in routines ready to use:

* **Text Processing**: ``TextClipper``, ``TextRenderer``, ``ResultExtractor``
* **Data Processing**: ``DataTransformer``, ``DataValidator``, ``DataFlattener``
* **Control Flow**: ``ConditionalRouter`` for dynamic routing
* **Utilities**: ``TimeProvider`` for time-based operations

.. code-block:: python

   from routilux.builtin_routines import TextClipper, ConditionalRouter
   
   clipper = TextClipper()
   clipper.set_config(max_length=1000)
   
   router = ConditionalRouter()
   router.set_config(routes=[
       ("high_priority", "data.get('priority') == 'high'"),
       ("normal", "data.get('priority') == 'normal'"),
   ])

**⚡ Event Queue Architecture**

Routilux uses an event queue pattern for workflow execution:
- Non-blocking ``emit()``: Returns immediately after enqueuing tasks
- Unified execution model: Sequential and concurrent modes use the same queue mechanism
- Fair scheduling: Tasks are processed fairly, preventing long chains from blocking shorter ones
- Automatic flow detection: ``emit()`` automatically detects flow from routine context

.. code-block:: python

   flow = Flow(execution_strategy="concurrent", max_workers=5)
   # Tasks execute in parallel via event queue

**🛡️ Robust Error Handling**

Multiple error handling strategies (STOP, CONTINUE, RETRY, SKIP) let you build resilient
workflows that handle failures gracefully.

.. code-block:: python

   from routilux import ErrorHandler, ErrorStrategy
   
   error_handler = ErrorHandler(
       strategy=ErrorStrategy.RETRY,
       max_retries=3
   )
   flow.set_error_handler(error_handler)

**💾 Full Serialization Support**

Serialize and deserialize entire flows for persistence, recovery, and distributed execution.

.. code-block:: python

   # Serialize
   flow_data = flow.serialize()
   
   # Deserialize
   new_flow = Flow.deserialize(flow_data)

**📈 Comprehensive Tracking**

Built-in execution tracking provides insights into workflow performance, execution history,
and routine statistics.

Key Features
------------

* **Slots and Events Mechanism**: Clear distinction between input slots and output events
* **Many-to-Many Connections**: Flexible connection relationships between routines
* **Merge Strategies**: Control how data from multiple sources is combined (override, append, custom)
* **State Management**: Unified ``stats()`` method for tracking routine state
* **Flow Manager**: Workflow orchestration, persistence, and recovery
* **JobState Management**: Execution state recording and recovery functionality
* **Error Handling**: Multiple error handling strategies (STOP, CONTINUE, RETRY, SKIP)
* **Execution Tracking**: Comprehensive execution tracking and performance monitoring
* **Event Queue Architecture**: Non-blocking emit(), unified execution model, fair scheduling
* **Concurrent Execution**: Thread pool-based parallel execution for I/O-bound operations (via event queue)
* **Serialization Support**: Full serialization/deserialization support for persistence
* **Built-in Routines**: Rich set of ready-to-use routines for common tasks

Architecture
------------

Routilux is built around a few core concepts:

**Routine**
   The fundamental building block. A routine can have:
   
   * **Slots** (0-N): Input mechanisms that receive data
   * **Events** (0-N): Output mechanisms that emit data
   * **Stats**: A dictionary for tracking execution state

**Flow**
   Orchestrates multiple routines and their connections. Manages execution
   using an event queue pattern, state, and error handling. Provides unified
   execution model for both sequential and concurrent modes.

**Connection**
   Links events to slots with optional parameter mapping. Supports flexible
   connection patterns.

**JobState**
   Tracks execution state and history. Enables pause, resume, and recovery.

**ErrorHandler**
   Configurable error handling with multiple strategies.

**ExecutionTracker**
   Monitors execution performance and event flow.

Design Principles
------------------

* **Separation of Concerns**: Clear separation between control (Flow) and data (JobState)
* **Flexibility**: Support for various workflow patterns (linear, branching, converging)
* **Persistence**: Full support for serialization and state recovery
* **Error Resilience**: Multiple error handling strategies for robust applications
* **Observability**: Comprehensive tracking and monitoring capabilities
* **Simplicity**: Clean, Pythonic API that's easy to learn and use
* **Extensibility**: Easy to create custom routines and extend functionality

Real-World Use Cases
--------------------

Routilux is ideal for:

* **Data Processing Pipelines**: ETL workflows, data transformation, validation
* **API Orchestration**: Coordinating multiple API calls, handling responses
* **LLM Agent Workflows**: Complex agent interactions, tool calling, result processing
* **Event Processing**: Real-time event streams, filtering, routing
* **Batch Processing**: Large-scale data processing with error recovery
* **Workflow Automation**: Business process automation, task orchestration

Getting Started
---------------

Ready to get started? Check out the :doc:`quickstart` guide for a hands-on introduction,
or dive into the :doc:`user_guide/index` for detailed documentation.

.. code-block:: python

   from routilux import Flow, Routine
   
   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.input_slot = self.define_slot("input", handler=self.process)
           self.output_event = self.define_event("output")
       
       def process(self, data=None, **kwargs):
           # Flow is automatically detected from routine context
           self.emit("output", result=f"Processed: {data}")
   
   flow = Flow()
   routine_id = flow.add_routine(MyRoutine(), "my_routine")
   flow.execute(routine_id, entry_params={"data": "Hello, Routilux!"})

Next Steps
----------

* :doc:`quickstart` - Get started in 5 minutes
* :doc:`user_guide/index` - Comprehensive user guide
* :doc:`api_reference/index` - Complete API documentation
* :doc:`examples/index` - Real-world examples
