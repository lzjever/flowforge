Flow API
========

The Flow module has been refactored into a modular structure for better maintainability.
The main ``Flow`` class and related components are organized as follows:

Main Flow Class
---------------

.. automodule:: routilux.flow
   :members:
   :undoc-members:
   :show-inheritance:

Flow Submodules
---------------

The Flow functionality is organized into the following submodules:

**flow.flow**
    Main Flow class that orchestrates workflow execution.

**flow.task**
    Task-related classes including ``TaskPriority`` enum and ``SlotActivationTask`` dataclass.

**flow.execution**
    Execution logic for sequential and concurrent workflow execution.

**flow.event_loop**
    Event loop and task queue management.

**flow.error_handling**
    Error handling logic for task errors and error handler resolution.

**flow.state_management**
    State management including pause, resume, cancel, and task serialization.

**flow.dependency**
    Dependency graph building and querying.

**flow.serialization**
    Flow serialization and deserialization logic.

For most use cases, you only need to import from the main ``routilux.flow`` module:

.. code-block:: python

   from routilux import Flow
   from routilux.flow import TaskPriority, SlotActivationTask  # If needed

The submodules are internal implementation details and typically don't need to be imported directly.

