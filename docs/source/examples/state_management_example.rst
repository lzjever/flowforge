State Management Example
=========================

Examples demonstrating JobState and ExecutionTracker usage.

Example Code
------------

.. literalinclude:: ../../../examples/state_management_example.py
   :language: python
   :linenos:

This example demonstrates:

* JobState for execution tracking
* ExecutionTracker for performance monitoring
* State serialization and persistence
* Pending tasks serialization in pause/resume
* Event queue state management

**Key Features**:

* **Pending Tasks Serialization**: Pending tasks are serialized when pausing
* **Event Queue State**: JobState tracks tasks in the event queue
* **Automatic Flow Detection**: State management works seamlessly with automatic flow detection

