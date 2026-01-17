Features
========

This document provides a comprehensive overview of Routilux features.

Core Architecture
-----------------

Runtime-Based Execution
~~~~~~~~~~~~~~~~~~~~~~~

* ✅ **Centralized Runtime**: Single execution manager with shared thread pool
* ✅ **Non-Blocking Execution**: ``runtime.exec()`` returns immediately
* ✅ **Job Registry**: Thread-safe tracking of all active jobs
* ✅ **Event Routing**: Automatic delivery of events to connected slots
* ✅ **Flow Registry**: Centralized flow registration and lookup

Event-Driven Architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~

* ✅ **Slots (Input)**: Queue-based input mechanisms for receiving data
* ✅ **Events (Output)**: Non-blocking output mechanisms for emitting data
* ✅ **Many-to-Many Connections**: Flexible event-to-slot wiring
* ✅ **Activation Policies**: Declarative control over routine execution
* ✅ **Unified Task Queue**: Fair scheduling for all executions

State Management
~~~~~~~~~~~~~~~~

* ✅ **JobState**: Execution state tracking per job
* ✅ **State Isolation**: Each execution has independent state
* ✅ **Serialization Support**: Save/resume workflow execution
* ✅ **Shared Data**: ``shared_data`` and ``shared_log`` for cross-routine communication
* ✅ **Execution History**: Complete record of all routine executions

Core Components
---------------

Routine
~~~~~~~

* ✅ **0-N Slots**: Define any number of input slots
* ✅ **0-N Events**: Define any number of output events
* ✅ **Activation Policies**: Control when routines execute
* ✅ **Logic Functions**: Separate logic from activation control
* ✅ **Configuration Dictionary**: ``_config`` for static parameters
* ✅ **Serialization Support**: Full save/load capability

.. warning:: **Critical Constraints**

   * Routines MUST have parameterless constructors
   * Routines MUST NOT modify instance variables during execution
   * All execution state MUST be stored in JobState

Slot (Input Slot)
~~~~~~~~~~~~~~~~~

* ✅ **Queue-Based Storage**: Thread-safe data queuing
* ✅ **Configurable Capacity**: Custom queue size and watermark
* ✅ **Many-to-One Support**: Multiple events can connect to one slot
* ✅ **Automatic Cleanup**: Data cleared based on watermark threshold
* ✅ **Thread-Safe Operations**: All operations are thread-safe

Event (Output Event)
~~~~~~~~~~~~~~~~~~~~

* ✅ **One-to-Many Support**: Single event connects to multiple slots
* ✅ **Non-Blocking Emit**: Returns immediately after enqueuing
* ✅ **Parameter Mapping**: Automatic data transformation via connections
* ✅ **Auto-Detection**: Flow automatically detected from execution context

Connection
~~~~~~~~~~

* ✅ **Event-to-Slot Links**: Connects event output to slot input
* ✅ **Parameter Mapping**: Transform data between event and slot
* ✅ **Many-to-Many Patterns**: Support complex connection topologies
* ✅ **Validation**: Automatic validation of connection integrity

Flow (Workflow Manager)
~~~~~~~~~~~~~~~~~~~~~~~

* ✅ **Routine Management**: Add, remove, and query routines
* ✅ **Connection Management**: Create and manage event-to-slot connections
* ✅ **Execution Template**: Flow definition is separate from execution
* ✅ **Validation**: Built-in flow structure validation
* ✅ **Serialization**: Save/load flow definitions

Runtime (Execution Manager)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* ✅ **Thread Pool Management**: Shared worker threads for all jobs
* ✅ **Job Lifecycle**: Start, monitor, pause, resume, cancel jobs
* ✅ **Job Registry**: Thread-safe tracking of active jobs
* ✅ **Wait Management**: Wait for completion with timeouts
* ✅ **Context Manager Support**: Automatic resource cleanup

JobState (Execution State)
~~~~~~~~~~~~~~~~~~~~~~~~~~

* ✅ **Status Tracking**: pending, running, completed, failed, cancelled
* ✅ **Routine States**: Per-routine execution state dictionaries
* ✅ **Execution History**: Complete record with timestamps
* ✅ **Shared Data**: ``shared_data`` for cross-routine communication
* ✅ **Shared Log**: ``shared_log`` for append-only logging
* ✅ **Serialization**: Save/load for workflow resumption

Activation Policies
-------------------

Built-in Policies
~~~~~~~~~~~~~~~~~

* ✅ **immediate_policy**: Execute immediately when any slot receives data
* ✅ **all_slots_ready_policy**: Execute when all slots have at least one item
* ✅ **batch_size_policy**: Execute when all slots have at least N items
* ✅ **time_interval_policy**: Execute at most once per time interval
* ✅ **custom_policy**: Define your own activation logic

.. warning:: **Required Configuration**

   Routines MUST have an activation policy set. Without it, the routine
   will never execute.

Error Handling
--------------

Error Strategies
~~~~~~~~~~~~~~~~

* ✅ **STOP**: Stop execution immediately on error
* ✅ **CONTINUE**: Continue execution despite errors, log them
* ✅ **RETRY**: Retry failed routine with configurable attempts and delay
* ✅ **SKIP**: Skip failed routine and continue with next

Error Handler Features
~~~~~~~~~~~~~~~~~~~~~~

* ✅ **Flow-Level Configuration**: Set error handler per flow
* ✅ **Retry Configuration**: Max retries, delay, backoff multiplier
* ✅ **Retryable Exception Types**: Specify which exceptions to retry
* ✅ **Error Logging**: Automatic error capture and recording

Concurrent Execution
--------------------

Threading Model
~~~~~~~~~~~~~~~

* ✅ **Shared Thread Pool**: All jobs share same worker threads
* ✅ **Configurable Pool Size**: Adjust based on workload
* ✅ **Thread-Safe Operations**: All state updates are thread-safe
* ✅ **Fair Scheduling**: Tasks processed fairly across jobs

Execution Features
~~~~~~~~~~~~~~~~~~

* ✅ **Non-Blocking emit()**: Event emission returns immediately
* ✅ **Automatic Flow Detection**: No need to pass flow explicitly
* ✅ **Independent Event Loops**: Each job has its own event loop
* ✅ **Wait Management**: Wait for specific jobs or all jobs

Serialization and Persistence
-----------------------------

Flow Serialization
~~~~~~~~~~~~~~~~~~

* ✅ **Save Flow Structure**: Serialize routines and connections
* ✅ **Load Flow Structure**: Reconstruct flow from saved data
* ✅ **DSL Support**: Import/export flows as YAML or JSON

JobState Serialization
~~~~~~~~~~~~~~~~~~~~~~

* ✅ **Save Execution State**: Persist job state to disk
* ✅ **Load Execution State**: Resume from saved state
* ✅ **Job Recovery**: Resume interrupted workflows

.. note:: **Serialization Format**

   Uses ``serilux`` library for JSON-based serialization. All core
   classes are serializable when following the parameterless constructor
   constraint.

Monitoring and Debugging
-------------------------

Monitoring Features
~~~~~~~~~~~~~~~~~~~

* ✅ **Zero Overhead When Disabled**: No performance impact when off
* ✅ **Execution Metrics**: Track duration, event counts, errors
* ✅ **Event Streaming**: Real-time event push via WebSocket
* ✅ **Performance Metrics**: Per-routine and per-job metrics
* ✅ **Execution History**: Complete audit trail

Debugging Features
~~~~~~~~~~~~~~~~~~

* ✅ **Breakpoints**: Conditional breakpoints for pausing execution
* ✅ **Debug Sessions**: Interactive debugging with step/continue
* ✅ **Variable Inspection**: Inspect slot data and job state
* ✅ **Expression Evaluation**: Safe expression evaluation in context

HTTP API and WebSocket
----------------------

REST API
~~~~~~~~

* ✅ **Flow Management**: CRUD operations for flows
* ✅ **Job Management**: Start, pause, resume, cancel jobs
* ✅ **Breakpoint Management**: Set/clear breakpoints
* ✅ **Debug Operations**: Step, continue, evaluate expressions
* ✅ **Monitoring Endpoints**: Get metrics and status
* ✅ **Health Checks**: API health and status endpoint

WebSocket Endpoints
~~~~~~~~~~~~~~~~~~~

* ✅ **Job Monitor**: Real-time events for specific job
* ✅ **Job Debug**: Debug-specific event streaming
* ✅ **Flow Monitor**: Aggregated events for flow's jobs
* ✅ **Generic WebSocket**: Dynamic subscription to multiple jobs

.. warning:: **Production Security**

   When using the API in production:
   * **Always enable API key authentication**: ``ROUTILUX_API_KEY_ENABLED=true``
   * **Use strong API keys**: Generate cryptographically random keys
   * **Enable rate limiting**: ``ROUTILUX_RATE_LIMIT_ENABLED=true``
   * **Restrict CORS**: Set ``ROUTILUX_CORS_ORIGINS`` to specific origins
   * **Use HTTPS**: Always use HTTPS in production

See :doc:`http_api` for complete security documentation.

Optional Features
-----------------

API Server (Optional)
~~~~~~~~~~~~~~~~~~~~~

* ✅ **FastAPI-Based**: Modern async web framework
* ✅ **Interactive Documentation**: Auto-generated Swagger UI and ReDoc
* ✅ **Rate Limiting**: Configurable per-IP rate limiting
* ✅ **CORS Support**: Configurable CORS origins
* ✅ **GZip Compression**: Automatic response compression

DSL Support (Optional)
~~~~~~~~~~~~~~~~~~~~~~

* ✅ **YAML Format**: Define flows in YAML
* ✅ **JSON Format**: Define flows in JSON
* ✅ **Import/Export**: Convert flows to/from DSL
* ✅ **Validation**: Validate DSL structure before execution

Built-in Routines
~~~~~~~~~~~~~~~~~

* ✅ **Control Flow**: Branch, merge, loop routines
* ✅ **Data Processing**: Map, filter, reduce routines
* ✅ **Text Processing**: String manipulation routines
* ✅ **Utilities**: Logging, timing utilities

Advanced Features
-----------------

Flow Builder
~~~~~~~~~~~~

* ✅ **Dynamic Flow Construction**: Build flows programmatically
* ✅ **Validation**: Validate flow structure before execution
* ✅ **Factory Support**: Create routines from factory or class path
* ✅ **Connection Management**: Add/remove connections dynamically

Output Handling
~~~~~~~~~~~~~~~

* ✅ **Multiple Handlers**: Queue, callback, null handlers
* ✅ **Output Logging**: Automatic output capture
* ✅ **Custom Handlers**: Implement custom output handlers

Thread Safety
~~~~~~~~~~~~~

* ✅ **Lock-Protected State**: All shared state protected by locks
* ✅ **ContextVars**: Thread-local storage for execution context
* ✅ **Atomic Operations**: Thread-safe state updates
* ✅ **No Race Conditions**: Designed for concurrent execution

Extensibility
~~~~~~~~~~~~~

* ✅ **Custom Routines**: Easy to create custom routine classes
* ✅ **Custom Policies**: Create custom activation policies
* ✅ **Custom Handlers**: Implement custom output handlers
* ✅ **Plugin System**: Factory pattern for routine registration
