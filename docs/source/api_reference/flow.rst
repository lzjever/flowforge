Flow API
========

The ``Flow`` class orchestrates multiple routines and manages their connections.

Overview
--------

A ``Flow`` is a container that manages:

* **Routine Management**: Add, organize, and track routines
* **Connection Management**: Link routines via events and slots
* **Execution Control**: Execute workflows via Runtime
* **Error Handling**: Apply error handling strategies

Basic Usage
-----------

.. code-block:: python

    from routilux import Flow, Routine

    # Create a flow
    flow = Flow("my_workflow")

    # Add routines
    routine1 = DataProcessor()
    routine2 = DataValidator()
    flow.add_routine(routine1, "processor")
    flow.add_routine(routine2, "validator")

    # Connect events to slots
    flow.connect("processor", "output", "validator", "input")

    # Register flow
    from routilux import FlowRegistry
    FlowRegistry.get_instance().register_by_name("my_workflow", flow)

.. automodule:: routilux.core.flow
   :members:
   :undoc-members:
   :show-inheritance:

Key Methods
-----------

.. automethod:: routilux.core.flow.Flow.__init__
   :no-index:
.. automethod:: routilux.core.flow.Flow.add_routine
   :no-index:
.. automethod:: routilux.core.flow.Flow.connect
   :no-index:
.. automethod:: routilux.core.flow.Flow.set_error_handler
   :no-index:
.. automethod:: routilux.core.flow.Flow.get_error_handler
   :no-index:
.. automethod:: routilux.core.flow.Flow.validate
   :no-index:

Additional Methods
------------------

.. automethod:: routilux.core.flow.Flow.find_routines_by_type
.. automethod:: routilux.core.flow.Flow.get_connections_for_event

WorkerNotRunningError
---------------------

.. autoclass:: routilux.core.flow.WorkerNotRunningError
   :members:
   :show-inheritance:
