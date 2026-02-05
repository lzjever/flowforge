Output Capture API
==================

Utilities for capturing and routing stdout output to job-specific buffers.

Overview
--------

Routilux provides utilities for capturing ``print()`` statements and routing
them to job-specific output buffers. This is useful for debugging and logging.

Basic Usage
-----------

.. code-block:: python

    from routilux import install_routed_stdout, get_job_output, Runtime

    # Install at program startup
    install_routed_stdout()

    # Use runtime normally
    runtime = Runtime()
    worker_state, job = runtime.post("my_flow", "routine", "slot", {"data": "test"})

    # Get output from specific job
    output = get_job_output(job.job_id)
    print(output)  # Contains all print() output from that job

.. automodule:: routilux.core.output
   :members:
   :undoc-members:
   :show-inheritance:

RoutedStdout
-----------

.. autoclass:: routilux.core.output.RoutedStdout
   :members:
   :show-inheritance:

Helper Functions
----------------

.. autofunction:: routilux.core.output.install_routed_stdout
.. autofunction:: routilux.core.output.uninstall_routed_stdout
.. autofunction:: routilux.core.output.get_job_output
.. autofunction:: routilux.core.output.clear_job_output
