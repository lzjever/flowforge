Monitoring API Reference
========================

This section documents the monitoring and debugging APIs.

.. contents::
   :local:
   :depth: 2

Monitoring Registry
-------------------

.. autoclass:: routilux.monitoring.MonitoringRegistry
   :members:
   :undoc-members:

Monitor Collector
-----------------

.. autoclass:: routilux.monitoring.MonitorCollector
   :members:
   :undoc-members:

.. autoclass:: routilux.monitoring.monitor_collector.ExecutionEvent
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: routilux.monitoring.monitor_collector.RoutineMetrics
   :members:
   :undoc-members:
   :show-inheritance:

Breakpoint Manager
------------------

.. autoclass:: routilux.monitoring.breakpoint_manager.BreakpointManager
   :members:
   :undoc-members:

.. autoclass:: routilux.monitoring.breakpoint_manager.Breakpoint
   :members:
   :undoc-members:
   :show-inheritance:

Debug Session Store
-------------------

.. autoclass:: routilux.monitoring.debug_session.DebugSessionStore
   :members:
   :undoc-members:

.. autoclass:: routilux.monitoring.debug_session.DebugSession
   :members:
   :undoc-members:
   :show-inheritance:

Job Event Manager
-----------------

.. autoclass:: routilux.monitoring.event_manager.JobEventManager
   :members:
   :undoc-members:

HTTP API Overview
-----------------

The monitoring system provides a comprehensive HTTP API for:

* **Flow Management**: Create, read, update, and delete flows
* **Job Execution**: Start, monitor, pause, resume, and cancel jobs
* **Metrics & Tracing**: Get execution metrics and detailed traces
* **Breakpoints**: Set, list, update, and delete breakpoints
* **Debug Controls**: Step over/into, get variables and call stack
* **WebSocket Monitoring**: Real-time event streaming

For detailed API documentation, see the :doc:`User Guide <../user_guide/monitoring_debugging>`.

Key Endpoints
~~~~~~~~~~~~~

**Flows**

* ``GET /api/flows`` - List all flows
* ``GET /api/flows/{flow_id}`` - Get a specific flow
* ``POST /api/flows`` - Create a new flow

**Jobs**

* ``GET /api/jobs`` - List all jobs
* ``GET /api/jobs/{job_id}`` - Get job details
* ``POST /api/jobs`` - Start a new job execution
* ``POST /api/jobs/{job_id}/pause`` - Pause a running job
* ``POST /api/jobs/{job_id}/resume`` - Resume a paused job
* ``POST /api/jobs/{job_id}/cancel`` - Cancel a job

**Metrics & Tracing**

* ``GET /api/jobs/{job_id}/metrics`` - Get job execution metrics
* ``GET /api/jobs/{job_id}/trace`` - Get execution trace

**Breakpoints**

* ``GET /api/jobs/{job_id}/breakpoints`` - List breakpoints
* ``POST /api/jobs/{job_id}/breakpoints`` - Set a breakpoint
* ``DELETE /api/jobs/{job_id}/breakpoints/{id}`` - Delete a breakpoint

**Debug Controls**

* ``POST /api/jobs/{job_id}/debug/step_over`` - Step over next routine
* ``POST /api/jobs/{job_id}/debug/step_into`` - Step into routine
* ``GET /api/jobs/{job_id}/debug/variables`` - Get debug variables
* ``GET /api/jobs/{job_id}/debug/call_stack`` - Get call stack

**WebSocket**

* ``WS /api/ws/jobs/{job_id}/monitor`` - Real-time job monitoring
* ``WS /api/ws/jobs/{job_id}/debug`` - Interactive debug session
* ``WS /api/ws/flows/{flow_id}/monitor`` - Flow-wide monitoring

Storage
-------

.. autoclass:: routilux.monitoring.storage.FlowStore
   :members:
   :undoc-members:

.. autoclass:: routilux.monitoring.storage.JobStore
   :members:
   :undoc-members:
