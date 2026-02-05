Architecture Design
===================

This document describes the architecture of Routilux, including
component relationships, data flow, and design decisions.

Overview
--------

Routilux is an **event-driven workflow orchestration framework** for Python.
It enables developers to compose complex workflows from reusable components
called Routines, connected via Events and Slots.

Key Design Principles:

- **Event-Driven**: Components communicate through events, not direct calls
- **Serializable**: All state can be serialized for pause/resume
- **Concurrent**: Built-in support for parallel execution
- **Explicit**: Data flow and dependencies are visible

Core Abstractions
-----------------

Flow
~~~~

The Flow is the **orchestration container** that manages:

- Routine lifecycle and registration
- Event-to-Slot connections
- Execution mode (sequential/concurrent)
- JobState creation and management

**Responsibilities:**

- Add/remove routines
- Create event-to-slot connections
- Execute workflows
- Wait for completion

**Invariants:**

- A Flow has a unique flow_id
- All routines in a Flow share the same Flow reference
- Events cannot cross Flow boundaries

Routine
~~~~~~~

A Routine is a **reusable workflow component** that:

- Defines input Slots and output Events
- Contains business logic via Slot handlers
- Can be configured with parameters

**Responsibilities:**

- Emit events with data
- Define input slots with handlers
- Store configuration parameters
- Register lifecycle hooks

**Invariants:**

- A Routine belongs to exactly one Flow
- Routine IDs are unique within a Flow
- Events are uniquely named per Routine

Event
~~~~~

An Event represents a **data emission point** in a Routine.

**Responsibilities:**

- Store event name and data
- Maintain reference to parent Routine
- Support data updates

Slot
~~~~

A Slot represents a **data consumption point** in a Routine.

**Responsibilities:**

- Receive data from connected Events
- Merge data based on strategy (override/append)
- Invoke handler function
- Record execution in JobState

**Merge Strategies:**

- **override**: Last write wins (default)
- **append**: Accumulate all values in a list

JobState
~~~~~~~~

JobState is the **execution state container** for a workflow run.

**Responsibilities:**

- Track current status (running/completed/failed/paused)
- Store Routine execution states
- Maintain execution history
- Support pause/resume
- Serializable for persistence

**Retention Policies:**

- ``max_history_size``: Limit history entries (default: 1000)
- ``history_ttl_seconds``: Remove old entries (default: 3600)

Component Diagram
-----------------

.. graphviz::
   :name: component-diagram
   :caption: Routilux Component Relationships

   digraph components {
       rankdir=TB;
       node [shape=box, style=rounded];

       Flow [label="Flow\n(Orchestrator)", shape=doublebox];
       Routine [label="Routine\n(Component)"];
       Event [label="Event\n(Emission)"];
       Slot [label="Slot\n(Reception)"];
       JobState [label="JobState\n(Execution State)"];
       Connection [label="Connection\n(Wiring)"];

       Flow -> Routine [label="1..*"];
       Flow -> JobState [label="creates"];
       Routine -> Event [label="0..*"];
       Routine -> Slot [label="0..*"];
       Event -> Connection [label="source"];
       Slot -> Connection [label="target"];
       Connection -> Flow [label="owned by"];
       JobState -> Routine [label="tracks state"];
   }

Data Flow
---------

.. graphviz::
   :name: data-flow-diagram
   :caption: Event Data Flow Through Connection

   digraph dataflow {
       rankdir=LR;
       node [shape=box];

       subgraph source_routine {
           SourceRoutine [label="Source Routine"];
           SourceEvent [label="Event.emit()"];
           SourceRoutine -> SourceEvent;
       }

       subgraph connection {
           Connection [label="Connection"];
           SourceEvent -> Connection [label="data"];
       }

       subgraph target_routine {
           TargetSlot [label="Slot.receive()"];
           Handler [label="Handler Function"];
           TargetRoutine [label="Target Routine"];
           JobState [label="JobState.record()"];

           Connection -> TargetSlot [label="merged data"];
           TargetSlot -> Handler;
           Handler -> JobState;
           JobState -> TargetRoutine [label="state update"];
       }
   }

Execution Flow
--------------

.. graphviz::
   :name: execution-sequence
   :caption: Workflow Execution Sequence

   digraph sequence {
       rankdir=LR;
       node [shape=box];

       User [label="User", shape=ellipse];
       Flow [label="Flow.execute()"];
       JobState [label="JobState"];
       Routine [label="Routine"];
       Slot [label="Slot.receive()"];
       Handler [label="Handler"];
       Event [label="Event.emit()"];
       Connection [label="Connection"];

       User -> Flow [label="call execute()"];
       Flow -> JobState [label="create"];
       Flow -> Routine [label="find entry routine"];
       Routine -> Slot [label="get input slots"];
       Slot -> Handler [label="call with data"];
       Handler -> JobState [label="record execution"];
       Handler -> Event [label="may emit"];
       Event -> Connection [label="propagate"];
       Connection -> Slot [label="deliver to target"];
       Flow -> Flow [label="continue until complete"];
   }

Design Decisions
----------------

Why Event-Driven?
~~~~~~~~~~~~~~~~~

**Decision:** Use events and slots instead of direct function calls.

**Rationale:**

1. **Decoupling**: Routines don't need direct references to each other
2. **Visibility**: Data flow is explicit through connections
3. **Flexibility**: Easy to reconfigure connections
4. **Serialization**: Event-based state is easier to persist

**Trade-offs:**

- Pro: Easier to test and reason about
- Pro: Natural for async/concurrent execution
- Con: More verbose than direct calls
- Con: Slight performance overhead

Why Slots Instead of Direct Handlers?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision:** Introduce Slot abstraction between Event and Handler.

**Rationale:**

1. **Merge Strategies**: Slots control how data is combined
2. **Multiple Sources**: Many events can connect to one slot
3. **Validation**: Slot can validate before calling handler
4. **Recording**: Slot automatically records to JobState

**Trade-offs:**

- Pro: Flexible data combination
- Pro: Consistent execution tracking
- Con: Additional abstraction layer
- Con: More concepts to learn

Why Serializable JobState?
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision:** All workflow state must be serializable.

**Rationale:**

1. **Pause/Resume**: Users can pause long workflows and resume later
2. **Crash Recovery**: State can be restored after failure
3. **Distributed**: Potential for cross-machine execution
4. **Debugging**: Full execution history available

**Trade-offs:**

- Pro: Resilient to failures
- Pro: Supports long-running workflows
- Con: Cannot use lambdas/closures in handlers
- Con: Serialization overhead

Concurrency Model
-----------------

Routilux supports two execution modes:

**Sequential Mode** (default):

- Routines execute one at a time
- Deterministic execution order
- Easier debugging
- Lower throughput

**Concurrent Mode**:

- Multiple routines execute in parallel
- Thread pool based (configurable workers)
- Higher throughput
- Requires thread-safe handlers

Choosing Between Modes:

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Scenario
     - Use Sequential
     - Use Concurrent
   * - I/O-bound tasks
     - No
     - Yes (big speedup)
   * - CPU-bound tasks
     - Yes (GIL limitation)
     - Maybe with multiprocessing
   * - Debugging
     - Yes
     - No (harder to trace)
   * - Simple dependencies
     - Either
     - Either
   * - Complex dependencies
     - Yes (avoid deadlocks)
     - No (risk of deadlocks)

Error Handling
--------------

Routilux provides a structured exception hierarchy:

```
RoutiluxError (base)
├── ExecutionError      # Runtime failures
├── SerializationError  # Serialize/deserialize failures
├── ConfigurationError  # Invalid setup
├── StateError          # State inconsistencies
└── SlotHandlerError    # User handler failures
```

Users can:

- Catch ``RoutiluxError`` for all framework errors
- Catch specific types for selective handling
- Inspect ``JobState.execution_history`` for errors

Performance Considerations
---------------------------

**Event Emission**: O(1) - creates Event object, looks up connections

**Slot Receive**: O(n) where n = number of connections to slot

**JobState Serialization**: O(h) where h = history size (use retention policies!)

**Concurrent Speedup**: Up to N workers for I/O-bound tasks

Bottlenecks to avoid:

1. **Unbounded history growth**: Use ``max_history_size`` and ``history_ttl_seconds``
2. **Large data in events**: Keep event data small, use references
3. **Slow handlers**: Profile handlers, optimize hot paths

Future Enhancements
-------------------

Potential improvements (not currently planned):

1. **Distributed execution**: Cross-machine workflow execution
2. **Event versioning**: Schema evolution for event data
3. **Visual debugger**: GUI for workflow visualization
4. **Metrics integration**: OpenTelemetry/Prometheus support

References
----------

- `Code Review <code_review.rst>`_
- `Design Overview <overview.rst>`_
- `Optimization Strategies <optimization.rst>`_
