Runtime API
===========

The ``Runtime`` class provides centralized workflow execution management.

Overview
--------

The ``Runtime`` manages all workflow executions with a shared thread pool,
provides worker tracking, and handles event routing.

Key Features
------------

* **Thread pool management**: Shared pool across all workers
* **Worker registry**: Thread-safe tracking of active workers
* **Non-blocking execution**: ``exec()`` returns immediately
* **Event routing**: Routes events to connected slots
* **Routine activation checking**: Calls activation policies
* **Job context binding**: For per-task tracking

Basic Usage
-----------

.. code-block:: python

    from routilux import Runtime

    # Create runtime with thread pool
    runtime = Runtime(thread_pool_size=10)

    # Execute flow
    worker_state = runtime.exec("my_flow")

    # Post data and create a job
    worker_state, job = runtime.post(
        "my_flow", "processor", "input",
        {"data": "test"},
        metadata={"user_id": "123"}
    )

    # Wait for completion
    runtime.wait_until_all_workers_idle(timeout=5.0)

    # Clean up
    runtime.shutdown()

Using Context Manager
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from routilux import Runtime

    with Runtime(thread_pool_size=10) as runtime:
        worker_state = runtime.exec("my_flow")
        runtime.post("my_flow", "processor", "input", {"data": "test"})
        runtime.wait_until_all_workers_idle(timeout=5.0)
    # Automatically shuts down when exiting context

.. automodule:: routilux.core.runtime
   :members:
   :undoc-members:
   :show-inheritance:

Key Methods
-----------

.. automethod:: routilux.core.runtime.Runtime.__init__
   :no-index:
.. automethod:: routilux.core.runtime.Runtime.exec
   :no-index:
.. automethod:: routilux.core.runtime.Runtime.post
   :no-index:
.. automethod:: routilux.core.runtime.Runtime.wait_until_all_workers_idle
   :no-index:
.. automethod:: routilux.core.runtime.Runtime.shutdown
   :no-index:
