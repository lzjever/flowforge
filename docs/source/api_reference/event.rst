Event API
=========

The ``Event`` class represents output channels for transmitting data.

Overview
--------

An ``Event`` is an output channel that:

* Emits data to connected slots
* Supports one-to-many connections (one event → multiple slots)
* Thread-safe operations
* Integrates with monitoring and breakpoints

Basic Usage
-----------

Events are typically created via ``Routine.add_event()``:

.. code-block:: python

    class MyRoutine(Routine):
        def __init__(self):
            super().__init__()
            # Add an event with documented output parameters
            self.add_event("output", output_params=["result", "status"])

        def logic(self, input_data, **kwargs):
            # Emit data to connected slots
            self.emit("output", result="processed", status="success")

.. automodule:: routilux.core.event
   :members:
   :undoc-members:
   :show-inheritance:

Key Methods
-----------

.. automethod:: routilux.core.event.Event.__init__
   :no-index:
.. automethod:: routilux.core.event.Event.emit
   :no-index:
.. automethod:: routilux.core.event.Event.connect
   :no-index:
.. automethod:: routilux.core.event.Event.disconnect
   :no-index:
