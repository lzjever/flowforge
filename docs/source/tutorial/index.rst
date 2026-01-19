Tutorials
=========

Welcome to the Routilux tutorials! These tutorials are designed to take you
from complete beginner to advanced user, progressively building your knowledge
and skills.

.. tip:: **How to Use These Tutorials**

   **If you're new to Routilux**: Start with :doc:`hello_world` and work through
   the :doc:`basics/understanding_routines` section sequentially.

   **If you have some experience**: Jump to specific topics using the navigation
   below or the sidebar.

   **If you're migrating from v1**: See :doc:`../../migration_guide` for what
   changed.

Tutorial Roadmap
-----------------

.. code-block:: text

   Beginner (Start Here)
   │
   ├─▶ hello_world (5 minutes)
   │
   ├─▶ basics/
   │   ├─▶ understanding_routines (Routines)
   │   ├─▶ understanding_slots_events (Slots & Events)
   │   ├─▶ understanding_flows (Flows)
   │   └─▶ understanding_runtime (Runtime)
   │
   ▼
   Intermediate
   │
   ├─▶ connections/
   │   ├─▶ simple_connection (Point-to-point)
   │   ├─▶ one_to_many (Fan-out)
   │   ├─▶ many_to_one (Fan-in)
   │   └─▶ complex_patterns (Diamond, branching, loops)
   │
   ├─▶ data_flow/
   │   ├─▶ parameter_mapping (Data routing)
   │   ├─▶ data_transformation (Transforming data)
   │   └─▶ slot_queue_management (Queue management)
   │
   ├─▶ activation/
   │   ├─▶ immediate_policy (Immediate activation)
   │   ├─▶ all_slots_ready (Wait for all slots)
   │   ├─▶ batch_size (Batch processing)
   │   ├─▶ time_interval (Time-based execution)
   │   └─▶ custom_policies (Custom policies)
   │
   └─▶ state/
       ├─▶ worker_state (Persistent state)
       ├─▶ job_context (Job-specific state)
       ├─▶ state_isolation (State boundaries)
       └─▶ output_capture (Capturing output)
   │
   ▼
   Advanced
   │
   ├─▶ error_handling/
   │   ├─▶ error_strategies (Error handling)
   │   ├─▶ error_handlers (Custom handlers)
   │   └─▶ resilience_patterns (Resilience)
   │
   ├─▶ concurrency/
   │   ├─▶ thread_pools (Thread management)
   │   ├─▶ parallel_execution (Parallel patterns)
   │   └─▶ synchronization (Thread safety)
   │
   ├─▶ advanced/
   │   ├─▶ serialization (Serialization)
   │   ├─▶ flow_builder (Declarative flows)
   │   ├─▶ monitoring (Zero-overhead monitoring)
   │   ├─▶ debugging (Breakpoints)
   │   └─▶ http_api (FastAPI server)
   │
   └─▶ cookbook/
       ├─▶ data_processing_pipeline (Data ETL)
       ├─▶ event_aggregator (Aggregation)
       ├─▶ conditional_routing (Routing)
       ├─▶ rate_limiter (Rate limiting)
       ├─▶ retry_mechanism (Retries)
       ├─▶ data_enrichment (Enrichment)
       └─▶ batch_processor (Batching)

Beginner Tutorials
-------------------

Get started with Routilux basics:

.. toctree::
   :maxdepth: 1

   hello_world
   basics/understanding_routines
   basics/understanding_slots_events
   basics/understanding_flows
   basics/understanding_runtime

Intermediate Tutorials
-----------------------

Build more complex workflows:

.. toctree::
   :maxdepth: 1

   connections/simple_connection
   connections/one_to_many
   connections/many_to_one
   connections/complex_patterns

   data_flow/parameter_mapping
   data_flow/data_transformation
   data_flow/slot_queue_management

   activation/immediate_policy
   activation/all_slots_ready
   activation/batch_size
   activation/time_interval
   activation/custom_policies

   state/worker_state
   state/job_context
   state/state_isolation

Advanced Tutorials
------------------

Master advanced features:

.. toctree::
   :maxdepth: 1

   error_handling/error_strategies
   error_handling/error_handlers
   error_handling/resilience_patterns

   concurrency/thread_pools
   concurrency/parallel_execution
   concurrency/synchronization

   advanced/serialization
   advanced/flow_builder
   advanced/monitoring
   advanced/debugging
   advanced/http_api

Cookbook (Pattern Library)
---------------------------

Copy-paste patterns for common use cases:

.. toctree::
   :maxdepth: 1

   cookbook/data_processing_pipeline
   cookbook/event_aggregator
   cookbook/conditional_routing
   cookbook/rate_limiter
   cookbook/retry_mechanism
   cookbook/data_enrichment
   cookbook/batch_processor

Legacy Tutorials
----------------

The following tutorials from the previous version are still available but may
reference deprecated APIs:

.. toctree::
   :maxdepth: 1

   getting_started
   connecting_routines
   data_flow
   state_management
   error_handling
   concurrent_execution
   advanced_patterns
   serialization

.. note:: **Deprecated Content Warning**

   The legacy tutorials above may reference deprecated APIs (like ``JobState``).
   For new code, follow the beginner tutorials above which use the current v2
   architecture.

Learning Path by Goal
---------------------

**I want to process data in parallel**:

1. :doc:`basics/understanding_routines`
2. :doc:`connections/one_to_many`
3. :doc:`concurrency/parallel_execution`

**I want to build a data pipeline**:

1. :doc:`basics/understanding_flows`
2. :doc:`connections/simple_connection`
3. :doc:`cookbook/data_processing_pipeline`

**I want to handle errors gracefully**:

1. :doc:`basics/understanding_runtime`
2. :doc:`error_handling/error_strategies`
3. :doc:`error_handling/resilience_patterns`

**I want to optimize performance**:

1. :doc:`activation/batch_size`
2. :doc:`concurrency/thread_pools`
3. :doc:`advanced/monitoring`

**I want to debug my workflow**:

1. :doc:`state/job_context`
2. :doc:`advanced/debugging`
3. :doc:`../../user_guide/troubleshooting`

Common Questions
----------------

**How long does it take to learn Routilux?**

- **Hello World**: 5 minutes
- **Basics**: 1-2 hours
- **Intermediate**: 4-6 hours
- **Advanced**: 10+ hours

**What should I learn first?**

Start with :doc:`hello_world`, then work through the basics section. The basics
are foundational - everything else builds on them.

**Do I need to read everything?**

No! Routilux is designed to be simple. For a quick start:

1. :doc:`hello_world`
2. :doc:`basics/understanding_routines`
3. :doc:`basics/understanding_slots_events`
4. :doc:`basics/understanding_flows`
5. :doc:`basics/understanding_runtime`

Then jump to specific topics as needed.

**Where can I find examples?**

- :doc:`../../examples/index` - Complete runnable examples
- :doc:`cookbook/index` - Copy-paste patterns
- :doc:`../../user_guide/index` - Comprehensive guides

**I'm stuck. Where can I get help?**

- :doc:`../../user_guide/troubleshooting` - Common issues
- :doc:`../../pitfalls/index` - Common mistakes
- GitHub Issues: https://github.com/lzjever/routilux/issues

.. note:: **Tutorial Conventions**

   Throughout the tutorials, you'll see:

   - **✅ DO** - Recommended practices
   - **❌ DON'T** - Common mistakes to avoid
   - **🔴 CRITICAL** - Must-know information
   - **🟡 IMPORTANT** - Important considerations
   - **🟢 TIP** - Helpful suggestions

   Each tutorial includes:
   - Complete, runnable code examples
   - Expected output
   - Common pitfalls
   - Next steps

Prerequisites
-------------

Before starting the tutorials, ensure you have:

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Requirement
     - How to Check
   * - Python 3.8+
     - ``python --version``
   * - pip or uv
     - ``pip --version`` or ``uv --version``
   * - routilux installed
     - ``python -c "import routilux; print(routilux.__version__)"``

**Installation**:

.. code-block:: bash

   # Using pip
   pip install routilux

   # Using uv (recommended)
   uv pip install routilux

**Quick Verify**:

.. code-block:: python

   # test_install.py
   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy

   print("Routilux installed successfully!")

Next Steps
----------

Start with :doc:`hello_world` for your first Routilux workflow!

.. seealso::

   :doc:`../../user_guide/index`
      Comprehensive user guides

   :doc:`../../api_reference/index`
      Complete API reference

   :doc:`../../examples/index`
      Runnable examples
