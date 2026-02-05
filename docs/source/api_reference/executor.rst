WorkerExecutor API
=================

The WorkerExecutor manages routine execution in worker threads.

Overview
--------

The ``WorkerExecutor`` is responsible for:

* Executing routine logic functions
* Managing thread safety and context
* Handling activation policies
* Propagating events to connected slots

This is an internal component typically used by the Runtime, not directly
by users.

.. automodule:: routilux.core.executor
   :members:
   :undoc-members:
   :show-inheritance:

WorkerExecutor
--------------

.. autoclass:: routilux.core.executor.WorkerExecutor
   :members:
   :show-inheritance:
