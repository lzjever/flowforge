Execution Hooks API
==================

The execution hooks interface allows custom code to be executed at key points
in the workflow lifecycle.

Overview
--------

The core module defines the ``ExecutionHooksInterface`` for execution lifecycle events.
The monitoring module provides the actual implementation. If no monitoring is enabled,
``NullExecutionHooks`` is used (no-op with zero overhead).

Hook Methods
------------

* ``on_worker_start``: Called when a worker starts execution
* ``on_worker_stop``: Called when a worker stops execution
* ``on_job_start``: Called when a job starts processing
* ``on_job_end``: Called when a job finishes processing
* ``on_routine_start``: Called when a routine starts execution
* ``on_routine_end``: Called when a routine finishes execution
* ``on_event_emit``: Called when an event is emitted
* ``on_slot_before_enqueue``: Called before data is enqueued to a slot

.. automodule:: routilux.core.hooks
   :members:
   :undoc-members:
   :show-inheritance:

ExecutionHooksInterface
-----------------------

.. autoclass:: routilux.core.hooks.ExecutionHooksInterface
   :members:
   :show-inheritance:

NullExecutionHooks
------------------

.. autoclass:: routilux.core.hooks.NullExecutionHooks
   :members:
   :show-inheritance:

Helper Functions
----------------

.. autofunction:: routilux.core.hooks.get_execution_hooks
.. autofunction:: routilux.core.hooks.set_execution_hooks
.. autofunction:: routilux.core.hooks.reset_execution_hooks
