Error Handling Example
=======================

Examples demonstrating different error handling strategies.

Example Code
------------

.. literalinclude:: ../../../examples/error_handling_example.py
   :language: python
   :linenos:

This example demonstrates:

* RETRY strategy with retry configuration
* CONTINUE strategy for error logging
* SKIP strategy for fault tolerance
* Error handling in event queue architecture
* Automatic flow detection in error scenarios

**Key Features**:

* **Task-level Error Handling**: Errors are handled at the task level in the event queue
* **Automatic Flow Detection**: ``emit()`` calls automatically detect flow context
* **Non-blocking Error Recovery**: Error handling doesn't block the event loop

