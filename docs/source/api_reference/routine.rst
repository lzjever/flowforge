Routine API
============

The ``Routine`` class is the base class for all processing units in Routilux.
It defines the input ``slots`` and output ``events`` for data flow.

Overview
--------

Routines are the fundamental building blocks of workflows. Each routine:

* Defines **slots** (input queues for receiving data)
* Defines **events** (output channels for transmitting data)
* Contains **logic** functions for processing data
* Stores configuration in ``_config`` dictionary
* Uses **WorkerState** for persistent execution state
* Uses **JobContext** for temporary job-level state

Important Constraints
---------------------

Routines MUST NOT accept constructor parameters (except ``self``). This is required
for proper serialization and deserialization. All configuration should be stored
in the ``_config`` dictionary instead:

.. code-block:: python

    # WRONG - Don't do this!
    class MyRoutine(Routine):
        def __init__(self, timeout: int):
            super().__init__()
            self.timeout = timeout  # This breaks serialization!

    # CORRECT - Do this instead!
    class MyRoutine(Routine):
        def __init__(self):
            super().__init__()
            self.set_config(timeout=30)  # Store in _config dict

State Management
----------------

Routilux provides two types of state:

**Worker-level State (``WorkerState``)**

Persistent state that lives across multiple executions. Use this for:

* Caches and accumulators
* Running counters and totals
* Long-lived resources (connections, sessions)

.. code-block:: python

    def logic(self, input_data, **kwargs):
        worker_state = get_current_worker_state()
        # Update persistent counter
        count = worker_state.get_routine_state("count") or 0
        worker_state.update_routine_state("count", count + 1)

**Job-level State (``JobContext``)**

Temporary state that lives only for a single job. Use this for:

* Request metadata and tracing
* Per-job results and outputs
* Temporary calculations

.. code-block:: python

    def logic(self, input_data, **kwargs):
        job = get_current_job()
        if job:
            job.set_data("processed", True)
            job.add_tag("api_request")

.. autoclass:: routilux.core.routine.Routine
   :members:
   :show-inheritance:
   :exclude-members: serialize, deserialize

Helper Methods
--------------

The ``Routine`` class provides several helper methods:

.. automethod:: routilux.core.routine.Routine.add_slot
.. automethod:: routilux.core.routine.Routine.add_event
.. automethod:: routilux.core.routine.Routine.emit
.. automethod:: routilux.core.routine.Routine.set_config
.. automethod:: routilux.core.routine.Routine.set_activation_policy
.. automethod:: routilux.core.routine.Routine.set_logic
.. automethod:: routilux.core.routine.Routine.get_execution_context
.. automethod:: routilux.core.routine.Routine.get_state
.. automethod:: routilux.core.routine.Routine.set_state
.. automethod:: routilux.core.routine.Routine.update_state

ExecutionContext
----------------

.. autoclass:: routilux.core.routine.ExecutionContext
   :members:
   :show-inheritance:

Context Variable Helpers
-------------------------

.. autofunction:: routilux.core.routine.get_current_worker_state
.. autofunction:: routilux.core.routine.set_current_worker_state
