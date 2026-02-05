Server API
==========

FastAPI-based HTTP API for remote flow management (optional).

Overview
--------

The server module provides a FastAPI application with REST API endpoints for:

* Flow management (CRUD operations)
* Job execution and monitoring
* Worker management
* Breakpoint debugging
* WebSocket real-time events

**Note**: The server module is optional. You can use Routilux without the HTTP API
by directly using the Runtime and Flow classes.

Getting Started
---------------

.. code-block:: python

    from routilux.server import create_app

    app = create_app()

    # Run with uvicorn
    # uvicorn routilux.server.main:app --reload

API Endpoints
-------------

Flow Management
~~~~~~~~~~~~~~~

* ``GET /api/v1/flows`` - List all flows
* ``POST /api/v1/flows`` - Create a new flow
* ``GET /api/v1/flows/{flow_id}`` - Get flow details
* ``DELETE /api/v1/flows/{flow_id}`` - Delete a flow

Job Execution
~~~~~~~~~~~~~

* ``POST /api/v1/flows/{flow_id}/execute`` - Execute a flow
* ``GET /api/v1/jobs`` - List all jobs
* ``GET /api/v1/jobs/{job_id}`` - Get job details
* ``POST /api/v1/jobs/{job_id}/cancel`` - Cancel a job

Worker Management
~~~~~~~~~~~~~~~~~

* ``GET /api/v1/workers`` - List all workers
* ``GET /api/v1/workers/{worker_id}`` - Get worker details
* ``POST /api/v1/workers/{worker_id}/pause`` - Pause worker
* ``POST /api/v1/workers/{worker_id}/resume`` - Resume worker

Breakpoints
~~~~~~~~~~~

* ``GET /api/v1/breakpoints`` - List all breakpoints
* ``POST /api/v1/breakpoints`` - Create a breakpoint
* ``DELETE /api/v1/breakpoints/{breakpoint_id}`` - Delete a breakpoint
* ``POST /api/v1/breakpoints/{breakpoint_id}/resume`` - Resume from breakpoint

WebSocket
~~~~~~~~~

* ``WS /api/v1/ws/events`` - Real-time event streaming

.. automodule:: routilux.server.main
   :members:
   :undoc-members:
   :show-inheritance:

Modules
-------

* ``routilux.server.routes`` - API route handlers
* ``routilux.server.models`` - Pydantic models for API
* ``routilux.server.middleware`` - FastAPI middleware
