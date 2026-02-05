FlowBuilder API
===============

Fluent API for building flows declaratively.

Overview
--------

The ``FlowBuilder`` provides a fluent interface for constructing flows
with method chaining.

Basic Usage
-----------

.. code-block:: python

    from routilux import FlowBuilder, Routine, immediate_policy

    class Processor(Routine):
        def __init__(self):
            super().__init__()
            self.add_slot("input")
            self.add_event("output")
            self.set_activation_policy(immediate_policy())

    flow = (FlowBuilder("my_flow")
        .add_routine(Processor(), "processor")
        .add_routine(Validator(), "validator")
        .connect("processor", "output", "validator", "input")
        .build())

.. automodule:: routilux.flow.builder
   :members:
   :undoc-members:
   :show-inheritance:

FlowBuilder
-----------

.. autoclass:: routilux.flow.builder.FlowBuilder
   :members:
   :show-inheritance:
