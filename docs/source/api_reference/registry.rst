Registry API
============

Global registries for flows and workers.

Overview
--------

Routilux provides singleton registries for managing flows and workers globally:

* ``FlowRegistry``: Global registry for Flow objects
* ``WorkerRegistry``: Global registry for active workers

These registries support a plugin-like architecture with singleton pattern.

FlowRegistry
------------

The ``FlowRegistry`` manages all Flow objects globally. Flows are automatically
registered when created.

.. autoclass:: routilux.core.registry.FlowRegistry
   :members:
   :show-inheritance:

WorkerRegistry
--------------

The ``WorkerRegistry`` tracks all active workers globally.

.. autoclass:: routilux.core.registry.WorkerRegistry
   :members:
   :show-inheritance:

Helper Functions
----------------

.. autofunction:: routilux.core.registry.get_flow_registry
.. autofunction:: routilux.core.registry.get_worker_registry
