Hello World Example
==================

A minimal working example showing the basic Routilux concepts.

.. literalinclude:: ../../examples/hello_world.py
   :language: python
   :lines: 7-29

Description
-----------

This example demonstrates:

1. Creating a simple ``Routine`` with a slot and event
2. Creating a ``Flow`` and adding the routine
3. Registering the flow with ``FlowRegistry``
4. Executing with ``Runtime``
5. Posting a job and waiting for completion

Code
----

.. literalinclude:: ../../examples/hello_world.py
   :language: python

Expected Output
-------------

.. code-block:: text

   Hello, World!

Running the Example
-----------------

.. code-block:: bash

   cd examples
   python hello_world.py

Notes
-----

- The routine must have an activation policy set (``immediate_policy()`` here)
- The flow must be registered with ``FlowRegistry`` before execution
- Use ``with Runtime()`` context manager for proper cleanup
- ``runtime.wait_until_all_jobs_finished()`` blocks until completion
