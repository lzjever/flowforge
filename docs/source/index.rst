.. Routilux documentation master file

Routilux Documentation
=====================

Welcome to Routilux's documentation!

Routilux is an event-driven workflow orchestration framework for Python. It provides
flexible connection management, state tracking, and real-time monitoring capabilities
for building reliable data processing pipelines.

.. grid:: 2
   :gutter: 2
   :margin: 2

   .. grid-item-card::
      :link: tutorial/hello_world
      :link-type: doc

      **Hello World**

      Get started in 5 minutes with your first Routilux workflow.

   .. grid-item-card::
      :link: tutorial/index
      :link-type: doc

      **Tutorials**

      Progressive tutorials from beginner to advanced.

   .. grid-item-card::
      :link: pitfalls/index
      :link-type: doc

      **Common Pitfalls**

      Avoid common mistakes and learn best practices.

   .. grid-item-card::
      :link: user_guide/index
      :link-type: doc

      **User Guide**

      Comprehensive guides for all Routilux features.

   .. grid-item-card::
      :link: api_reference/index
      :link-type: doc

      **API Reference**

      Complete API documentation for all modules.

   .. grid-item-card::
      :link: examples/index
      :link-type: doc

      **Examples**

      Real-world code examples and patterns.

   .. grid-item-card::
      :link: migration_guide
      :link-type: doc

      **Migration Guide**

      Migrating from v1 to v2 architecture.

   .. grid-item-card::
      :link: testing
      :link-type: doc

      **Testing**

      Testing guidelines and best practices.

Quick Start
-----------

Install Routilux:

.. code-block:: bash

   pip install routilux

Your first workflow:

.. code-block:: python

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy

   class HelloWorld(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("greeting")

           def say_hello(slot_data, policy_message, worker_state):
               print("Hello, World!")
               self.emit("greeting", message="Hello, World!")

           self.set_logic(say_hello)
           self.set_activation_policy(immediate_policy())

   flow = Flow("hello_flow")
   flow.add_routine(HelloWorld(), "greeter")

   from routilux.monitoring.flow_registry import FlowRegistry
   FlowRegistry.get_instance().register_by_name("hello_flow", flow)

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("hello_flow")
       runtime.post("hello_flow", "greeter", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=5.0)

.. note:: **New to Routilux?**

   Start with the :doc:`tutorial/hello_world` tutorial for a gentle introduction.

Documentation Structure
-----------------------

.. toctree::
   :maxdepth: 2
   :caption: Documentation
   :hidden:

   introduction
   installation
   quickstart
   http_api
   migration_guide

   Tutorials <tutorial/index>
   Pitfalls <pitfalls/index>

   User Guide <user_guide/index>
   API Reference <api_reference/index>
   Examples <examples/index>

   features
   testing
   changelog

Learning Path
-------------

**Beginner** (New to Routilux)

1. :doc:`tutorial/hello_world` - Your first workflow (5 minutes)
2. :doc:`tutorial/basics/understanding_routines` - Core concepts
3. :doc:`tutorial/basics/understanding_slots_events` - Data flow
4. :doc:`tutorial/basics/understanding_flows` - Building flows
5. :doc:`tutorial/basics/understanding_runtime` - Execution

**Intermediate** (Building real workflows)

1. :doc:`tutorial/connections/simple_connection` - Connecting routines
2. :doc:`tutorial/connections/one_to_many` - Fan-out patterns
3. :doc:`tutorial/state/worker_state` - State management
4. :doc:`tutorial/activation/batch_size` - Batch processing
5. :doc:`tutorial/error_handling/error_strategies` - Error handling

**Advanced** (Production-ready workflows)

1. :doc:`tutorial/connections/complex_patterns` - Complex topologies
2. :doc:`tutorial/advanced/monitoring` - Zero-overhead monitoring
3. :doc:`tutorial/advanced/debugging` - Breakpoint debugging
4. :doc:`tutorial/cookbook/index` - Pattern library
5. :doc:`pitfalls/index` - Common pitfalls

Key Concepts
------------

**Routines**

Routines are the building blocks of workflows. Each routine:

- Defines input ``slots`` (data receivers)
- Defines output ``events`` (data emitters)
- Contains ``logic`` functions for processing
- Must NOT accept constructor parameters (serialization requirement)

**Flows**

Flows orchestrate multiple routines:

- Contain routines with unique IDs
- Define connections between events and slots
- Manage execution lifecycle
- Can be serialized and distributed

**Runtime**

The Runtime executes flows:

- Manages thread pools
- Routes events between routines
- Tracks WorkerState and JobContext
- Provides execution context

**State Management**

Two types of state:

- ``WorkerState``: Persistent, worker-level state (caches, counters)
- ``JobContext``: Temporary, job-level state (request metadata, tracing)

Common Use Cases
----------------

**Data Processing Pipeline**

Process data through multiple stages with error handling and retry logic.

**Event Aggregation**

Collect and aggregate events from multiple sources.

**Conditional Routing**

Route data to different processors based on conditions.

**Batch Processing**

Process data in batches for efficiency.

**Parallel Execution**

Execute independent operations concurrently.

Contributing
------------

Found a bug? Have a feature request? Please contribute!

- GitHub: https://github.com/lzjever/routilux
- Issues: https://github.com/lzjever/routilux/issues
- Pull Requests: https://github.com/lzjever/routilux/pulls

Indices and tables
=================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
