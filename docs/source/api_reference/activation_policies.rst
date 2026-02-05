Activation Policies API
======================

Activation policies determine when a routine's logic should be executed
based on slot data availability and conditions.

Overview
--------

Activation policies control when routines execute by checking slot data
and deciding whether to activate the routine's logic. Each policy receives
the current slots and worker state, and returns whether to activate,
what data to process, and an optional policy message.

Built-in Policies
-----------------

immediate_policy
~~~~~~~~~~~~~~~~

Execute immediately when any slot receives data.

.. autofunction:: routilux.activation_policies.immediate_policy

all_slots_ready_policy
~~~~~~~~~~~~~~~~~~~~~~

Execute only when all slots have at least one item of data.

.. autofunction:: routilux.activation_policies.all_slots_ready_policy

batch_size_policy
~~~~~~~~~~~~~~~~~

Execute when all slots have at least N items of data.

.. autofunction:: routilux.activation_policies.batch_size_policy

time_interval_policy
~~~~~~~~~~~~~~~~~~~~

Execute at most once every N seconds, regardless of how many events arrive.

.. autofunction:: routilux.activation_policies.time_interval_policy

breakpoint_policy
~~~~~~~~~~~~~~~~~

Pause execution at breakpoint for debugging.

.. autofunction:: routilux.activation_policies.breakpoint_policy

custom_policy
~~~~~~~~~~~~~

Create a custom activation policy with your own logic.

.. autofunction:: routilux.activation_policies.custom_policy

.. automodule:: routilux.activation_policies
   :members:
   :undoc-members:
   :show-inheritance:

Usage Examples
--------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

    from routilux import Routine
    from routilux.activation_policies import immediate_policy, batch_size_policy

    class MyRoutine(Routine):
        def __init__(self):
            super().__init__()
            self.add_slot("input")
            self.add_event("output")
            self.set_activation_policy(immediate_policy())

            def process(input_data, **kwargs):
                result = input_data * 2
                self.emit("output", result=result)

            self.set_logic(process)

Batch Processing
~~~~~~~~~~~~~~~~

.. code-block:: python

    from routilux.activation_policies import batch_size_policy

    # Process in batches of 100
    routine.set_activation_policy(batch_size_policy(100))

    def process_batch(input_data, **kwargs):
        # input_data will be a dict with lists of items
        for item in input_data["input"]:
            # Process each item
            pass

Time-Based Throttling
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from routilux.activation_policies import time_interval_policy

    # Execute at most once every 5 seconds
    routine.set_activation_policy(time_interval_policy(5.0))

Custom Policy
~~~~~~~~~~~~~

.. code-block:: python

    from routilux.activation_policies import custom_policy

    def my_policy(slots, worker_state):
        # Custom logic to decide when to activate
        input_slot = slots.get("input")

        # Check if we have special trigger data
        for item in input_slot.consume_all_new():
            if item.get("trigger") == "now":
                return True, {"input": [item]}, "Triggered"

        return False, {}, "Waiting for trigger"

    routine.set_activation_policy(my_policy)
