Basic Example
=============

A simple example demonstrating basic routine and flow usage.

Example Code
------------

.. literalinclude:: ../../../examples/hello_world.py
   :language: python
   :linenos:

This example demonstrates:

* Creating routines with slots and events
* Using activation policies to control execution
* Building flows with FlowBuilder
* Executing a flow with Runtime
* Posting data to trigger execution

**Key Features**:

* **Event-Driven Execution**: Routines communicate via events and slots
* **Flow Builder**: Declarative flow construction using fluent API
* **Runtime**: Centralized execution management with thread pool
* **Activation Policies**: Control when routines execute

Running the Example
-------------------

To run this example:

.. code-block:: bash

    cd examples
    python hello_world.py
