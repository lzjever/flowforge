Connection API
==============

The ``Connection`` class links events to slots for data flow.

Overview
--------

A ``Connection`` represents a link between an event (output) and a slot (input).
When an event emits data, the data flows through all connections to the
connected slots.

Basic Usage
-----------

Connections are typically created via ``Flow.connect()``:

.. code-block:: python

    flow = Flow("my_flow")
    flow.add_routine(processor, "processor")
    flow.add_routine(validator, "validator")

    # Connect processor's output to validator's input
    flow.connect("processor", "output", "validator", "input")

.. automodule:: routilux.core.connection
   :members:
   :undoc-members:
   :show-inheritance:
