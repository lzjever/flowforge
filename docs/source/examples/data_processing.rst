Data Processing Example
========================

A multi-stage data processing pipeline example.

Example Code
------------

.. literalinclude:: ../../../examples/data_processing.py
   :language: python
   :linenos:

This example demonstrates:

* Multi-stage data processing pipeline
* Automatic flow detection in ``emit()`` calls
* Error handling in validation
* Statistics tracking across stages
* Event queue-based execution

**Key Features**:

* **Event Queue Pattern**: Tasks are enqueued and processed asynchronously
* **Automatic Flow Detection**: No need to pass flow parameter in ``emit()`` calls
* **Non-blocking Execution**: Each stage processes independently via the event queue

