Monitoring & Debugging API
==========================

Optional monitoring, debugging, and real-time event streaming capabilities.

.. note::
   All monitoring features are **disabled by default** and have **zero overhead**
   when not enabled. Enable monitoring via ``MonitoringRegistry.enable()`` or by
   setting the ``ROUTILUX_ENABLE_MONITORING=true`` environment variable.

Overview
--------

The monitoring module provides:

* **Breakpoint Management**: Set breakpoints on routines with conditions
* **Debug Sessions**: Interactive debugging workflows
* **Real-time Events**: Event streaming via WebSocket
* **Execution Metrics**: Performance metrics and execution traces
* **Zero Overhead**: No performance impact when disabled

Enabling Monitoring
-------------------

.. code-block:: python

    from routilux.monitoring import MonitoringRegistry

    # Enable monitoring programmatically
    MonitoringRegistry.enable()

    # Or use environment variable:
    # export ROUTILUX_ENABLE_MONITORING=true

Core Components
---------------

MonitoringRegistry
~~~~~~~~~~~~~~~~~~

.. autoclass:: routilux.monitoring.registry.MonitoringRegistry
   :members:
   :show-inheritance:

MonitorCollector
~~~~~~~~~~~~~~~~

.. autoclass:: routilux.monitoring.monitor_collector.MonitorCollector
   :members:
   :show-inheritance:

ExecutionMetrics
^^^^^^^^^^^^^^^^

.. autoclass:: routilux.monitoring.monitor_collector.ExecutionMetrics
   :members:
   :show-inheritance:

RoutineMetrics
^^^^^^^^^^^^^^

.. autoclass:: routilux.monitoring.monitor_collector.RoutineMetrics
   :members:
   :show-inheritance:

ExecutionEvent
^^^^^^^^^^^^^^

.. autoclass:: routilux.monitoring.monitor_collector.ExecutionEvent
   :members:
   :show-inheritance:

Breakpoints
-----------

BreakpointManager
~~~~~~~~~~~~~~~~~

.. autoclass:: routilux.monitoring.breakpoint_manager.BreakpointManager
   :members:
   :show-inheritance:

Breakpoint
~~~~~~~~~~

.. autoclass:: routilux.monitoring.breakpoint_manager.Breakpoint
   :members:
   :show-inheritance:

Debug Sessions
--------------

DebugSession
~~~~~~~~~~~~

.. autoclass:: routilux.monitoring.debug_session.DebugSession
   :members:
   :show-inheritance:

DebugSessionStore
~~~~~~~~~~~~~~~~~

.. autoclass:: routilux.monitoring.debug_session.DebugSessionStore
   :members:
   :show-inheritance:

CallFrame
~~~~~~~~~

.. autoclass:: routilux.monitoring.debug_session.CallFrame
   :members:
   :show-inheritance:

Event Manager
-------------

JobEventManager
~~~~~~~~~~~~~~~

.. autoclass:: routilux.monitoring.event_manager.JobEventManager
   :members:
   :show-inheritance:

Helper Functions
----------------

.. autofunction:: routilux.monitoring.event_manager.get_event_manager

Execution Hooks
---------------

MonitoringExecutionHooks
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: routilux.monitoring.execution_hooks.MonitoringExecutionHooks
   :members:
   :show-inheritance:

Helper Functions
----------------

.. autofunction:: routilux.monitoring.execution_hooks.enable_monitoring_hooks
.. autofunction:: routilux.monitoring.execution_hooks.disable_monitoring_hooks
.. autofunction:: routilux.monitoring.execution_hooks.get_monitoring_hooks
