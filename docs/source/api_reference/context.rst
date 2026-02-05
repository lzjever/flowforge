Context API
===========

The context module provides JobContext and WorkerState for managing execution state.

Overview
--------

Routilux uses Python's ``contextvars`` module to provide thread-local context
that is automatically propagated across async operations and thread boundaries.

Key Context Variables
---------------------

* ``_current_job``: Current JobContext for the executing job
* ``_current_worker_state``: Current WorkerState for the executing worker

Context Variables (contextvars)
--------------------------------

**Context Variables** allow automatic propagation of state across thread boundaries.
They are set by WorkerExecutor before routine execution and can be accessed via
helper functions.

**Normal Execution (within routines):**

Context variables are automatically set by WorkerExecutor before routine execution.

.. code-block:: python

    from routilux.core.context import get_current_job, get_current_worker_state

    def logic(self, input_data, **kwargs):
        job = get_current_job()  # Automatically available
        worker_state = get_current_worker_state()  # Automatically available

**Testing Scenarios:**

When writing tests that directly call methods like ``emit()`` or ``handle_event_emit()``,
you MUST manually set the context variables:

.. code-block:: python

    from routilux.core.context import set_current_job, set_current_worker_state

    # In your test
    worker_state, job_context = runtime.post(...)

    # Set context variables before calling methods that need them
    set_current_job(job_context)
    set_current_worker_state(worker_state)

    # Now methods can access context
    source.output.emit(runtime=runtime, worker_state=worker_state, data="test")

.. automodule:: routilux.core.context
   :members:
   :undoc-members:
   :show-inheritance:

JobContext
----------

.. autoclass:: routilux.core.context.JobContext
   :members:
   :show-inheritance:

Helper Functions
----------------

.. autofunction:: routilux.core.context.get_current_job
.. autofunction:: routilux.core.context.set_current_job
