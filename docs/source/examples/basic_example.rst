Basic Example
=============

A simple example demonstrating basic routine and flow usage.

Example Code
------------

.. literalinclude:: ../../../examples/basic_example.py
   :language: python
   :linenos:

This example demonstrates:

* Creating routines with slots and events
* Automatic flow detection in ``emit()`` calls (no need to pass flow parameter)
* Connecting routines in a flow
* Executing a flow
* Checking execution status

**Key Features**:

* **Automatic Flow Detection**: The ``emit()`` method automatically detects the flow from routine context
* **Non-blocking emit()**: Event emission returns immediately after enqueuing tasks
* **Event Queue Architecture**: All execution uses a unified event queue mechanism

