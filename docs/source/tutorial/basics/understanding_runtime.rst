Understanding Runtime
====================

The **Runtime** is Routilux's execution engine. It manages thread pools, routes
events between routines, tracks execution state, and provides the bridge between
your flows and actual execution.

.. note:: **What You'll Learn**

   - How Runtime manages execution
   - How to create and configure Runtime instances
   - How to post jobs and wait for completion
   - How Runtime handles threading and concurrency
   - Runtime lifecycle and best practices

.. note:: **Prerequisites**

   - :doc:`understanding_flows` - Understand Flows first

What is Runtime?
----------------

The **Runtime** is the execution environment that:

- **Manages** thread pools for parallel execution
- **Routes** events from routines to connected slots
- **Tracks** WorkerState and JobContext for each execution
- **Executes** jobs posted to flows
- **Handles** routine activation policies

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                        Runtime                               │
   │                                                              │
   │  ┌────────────────────────────────────────────────────────┐ │
   │  │              Thread Pool (executor)                     │ │
   │  │                                                         │ │
   │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   │ │
   │  │  │ Thread 1│  │ Thread 2│  │ Thread 3│  │ Thread N│   │ │
   │  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘   │ │
   │  └───────┼────────────┼────────────┼────────────┼────────┘ │
   │          │            │            │            │           │
   │          ▼            ▼            ▼            ▼           │
   │  ┌────────────────────────────────────────────────────────┐ │
   │  │                   WorkerExecutors                      │ │
   │  │                                                         │ │
   │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │ │
   │  │  │Worker 1  │  │Worker 2  │  │Worker N  │             │ │
   │  │  │┌────────┐│  │┌────────┐│  │┌────────┐│             │ │
   │  │  ││Routine ││  ││Routine ││  ││Routine ││             │ │
   │  │  ││Logic   ││  ││Logic   ││  ││Logic   ││             │ │
   │  │  │└────────┘│  │└────────┘│  │└────────┘│             │ │
   │  │  └──────────┘  └──────────┘  └──────────┘             │ │
   │  └────────────────────────────────────────────────────────┘ │
   │                                                              │
   │  ┌────────────────────────────────────────────────────────┐ │
   │  │              Event Routing System                       │ │
   │  │                                                         │ │
   │  │  Event → Connection → Slot → Activation → Logic        │ │
   │  └────────────────────────────────────────────────────────┘ │
   └─────────────────────────────────────────────────────────────┘

Creating a Runtime
------------------

**Context Manager (Recommended)**:

.. code-block:: python
   :linenos:

   from routilux import Runtime

   # Using context manager (recommended)
   with Runtime(thread_pool_size=4) as runtime:
       # Execute flows here
       worker_state = runtime.exec("my_flow")
       # ... do work ...
       # Automatically shuts down when exiting 'with' block

.. tip:: **Always Use Context Managers**

   Using ``with Runtime()`` ensures:
   - Thread pools are properly shut down
   - Resources are cleaned up
   - No hanging threads

   Equivalent manual cleanup:

   .. code-block:: python

      runtime = Runtime(thread_pool_size=4)
      try:
          # ... do work ...
      finally:
          runtime.shutdown()

**Runtime Parameters**:

.. code-block:: python

   # Basic runtime
   runtime = Runtime()

   # With custom thread pool
   runtime = Runtime(thread_pool_size=8)

   # With all parameters
   runtime = Runtime(
       thread_pool_size=4,       # Number of worker threads
       max_queue_size=1000,      # Max pending jobs
       enable_monitoring=True    # Enable monitoring collection
   )

**Parameter Reference**:

- ``thread_pool_size``: Number of worker threads (default: CPU count)
- ``max_queue_size``: Maximum pending jobs in queue (default: 1000)
- ``enable_monitoring``: Enable metrics collection (default: False)

.. warning:: **Thread Pool Size Guidelines**

   Choose thread pool size based on your workload:

   - **CPU-bound tasks**: Use ``thread_pool_size=os.cpu_count()``
   - **I/O-bound tasks**: Use 2-4x CPU count
   - **Mixed workloads**: Start with CPU count, tune based on performance

   Too many threads cause context switching overhead. Too few cause
   underutilization.

Executing Flows
---------------

**exec() - Start Flow Execution**:

.. code-block:: python

   from routilux import Runtime

   runtime = Runtime(thread_pool_size=2)

   # Start the flow (creates worker)
   worker_state = runtime.exec("my_flow")

   # exec() returns WorkerState for tracking
   print(f"Worker ID: {worker_state.worker_id}")
   print(f"Flow ID: {worker_state.flow_id}")
   print(f"Status: {worker_state.status}")

.. note:: **exec() vs post()**

   - ``exec(flow_id)``: Starts the flow's worker, returns WorkerState
   - ``post(flow_id, routine_id, slot, data)``: Submits a job to a flow

   You typically call ``exec()`` once per flow, then ``post()`` multiple times.

**post() - Submit Jobs**:

.. code-block:: python
   :linenos:

   with Runtime(thread_pool_size=2) as runtime:
       # Start the flow
       worker_state = runtime.exec("my_flow")

       # Post a job to trigger a routine
       job_context = runtime.post(
           "my_flow",       # flow_id
           "routine1",      # routine_id
           "trigger",       # slot_name
           {"key": "value"} # data to send
       )

       # job_context contains tracking information
       print(f"Job ID: {job_context.job_id}")

**post() Return Value**:

.. code-block:: python

   worker_state, job_context = runtime.post(
       "my_flow", "routine", "slot", {}
   )

   # worker_state: WorkerState instance
   #   - worker_id: Unique worker identifier
   #   - flow_id: Flow this worker belongs to
   #   - status: Worker status (starting, running, stopped)
   #   - routine_states: Per-routine state tracking

   # job_context: JobContext instance
   #   - job_id: Unique job identifier
   #   - status: Job status (pending, running, completed, failed)
   #   - data: Job-level data storage
   #   - trace_log: Execution trace for debugging

Waiting for Completion
----------------------

**wait_until_all_jobs_finished()**:

.. code-block:: python

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("my_flow")

       # Post multiple jobs
       for i in range(5):
           runtime.post("my_flow", "processor", "input", {"value": i})

       # Wait for all jobs to complete
       runtime.wait_until_all_jobs_finished(timeout=10.0)

.. tip:: **Always Set Timeouts**

   Always use a timeout when waiting to prevent indefinite blocking:

   .. code-block:: python

      # Good - With timeout
      runtime.wait_until_all_jobs_finished(timeout=30.0)

      # Risky - No timeout (may block forever)
      runtime.wait_until_all_jobs_finished()

**Polling for Job Status**:

.. code-block:: python

   import time

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("my_flow")
       job_ctx, _ = runtime.post("my_flow", "processor", "input", {"value": 42})
       job_id = job_ctx.job_id

       # Poll for completion
       while True:
           job = runtime.get_job(job_id)
           if job and job.status in ("completed", "failed"):
               break
           time.sleep(0.1)

       print(f"Job finished: {job.status}")

Complete Example: Processing Pipeline
--------------------------------------

Here's a complete example showing Runtime usage:

.. code-block:: python
   :linenos:
   :name: understanding_runtime_complete

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   import time

   # Define a simple processor routine
   class Processor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output", ["result", "original"])

           def process(slot_data, policy_message, worker_state):
               data_list = slot_data.get("input", [])
               if data_list:
                   value = data_list[0].get("value", 0)
                   result = value * 2

                   # Track processing in worker state
                   state = worker_state.get_routine_state("processor") or {}
                   count = state.get("processed_count", 0) + 1
                   worker_state.update_routine_state("processor", {
                       "processed_count": count,
                       "last_value": value
                   })

                   print(f"Processed: {value} → {result} (count: {count})")
                   self.emit("output", result=result, original=value)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Build flow
   flow = Flow("processor_flow")
   flow.add_routine(Processor(), "processor")

   # Register flow
   FlowRegistry.get_instance().register_by_name("processor_flow", flow)

   # Execute with Runtime
   print("Starting runtime...")
   with Runtime(thread_pool_size=2) as runtime:
       # Start the flow
       worker_state = runtime.exec("processor_flow")
       print(f"Worker started: {worker_state.worker_id}")

       # Post multiple jobs
       print("Posting jobs...")
       job_ids = []
       for i in range(5):
           _, job_ctx = runtime.post(
               "processor_flow",
               "processor",
               "input",
               {"value": i}
           )
           job_ids.append(job_ctx.job_id)

       # Wait for completion
       print("Waiting for jobs to complete...")
       runtime.wait_until_all_jobs_finished(timeout=10.0)

       # Check results
       print("\nResults:")
       for job_id in job_ids:
           job = runtime.get_job(job_id)
           print(f"  Job {job_id}: {job.status}")

       # Check worker state
       processor_state = worker_state.get_routine_state("processor")
       print(f"\nWorker state: {processor_state}")

**Expected Output**:

.. code-block:: text

   Starting runtime...
   Worker started: worker_abc123
   Posting jobs...
   Waiting for jobs to complete...
   Processed: 0 → 0 (count: 1)
   Processed: 1 → 2 (count: 2)
   Processed: 2 → 4 (count: 3)
   Processed: 3 → 6 (count: 4)
   Processed: 4 → 8 (count: 5)

   Results:
     job_xyz1: completed
     job_xyz2: completed
     job_xyz3: completed
     job_xyz4: completed
     job_xyz5: completed

   Worker state: {'processed_count': 5, 'last_value': 4}

Runtime Internals
-----------------

**Thread Pool Architecture**:

Runtime uses a ``concurrent.futures.ThreadPoolExecutor`` for parallel execution:

.. code-block:: text

   Runtime Thread Pool
   │
   ├─ Thread 1 ─▶ WorkerExecutor ─▶ Routine Logic
   ├─ Thread 2 ─▶ WorkerExecutor ─▶ Routine Logic
   ├─ Thread 3 ─▶ WorkerExecutor ─▶ Routine Logic
   └─ Thread N ─▶ WorkerExecutor ─▶ Routine Logic

Each thread maintains its own context via Python's ``contextvars`` module,
allowing safe access to JobContext and WorkerState.

**Event Routing**:

When a routine emits an event:

1. Runtime receives the event with data
2. Looks up connections for that event
3. For each connection, posts data to destination slot
4. Slot queues the data
5. Activation policy checks if routine should execute
6. If activation passes, routine logic executes on thread pool

.. code-block:: text

   emit("output", data=123)
        │
        ▼
   Runtime routes event
        │
        ├──▶ Slot A (Connection 1) ─▶ Queue ─▶ Routine A
        │
        └──▶ Slot B (Connection 2) ─▶ Queue ─▶ Routine B

**Job Execution Flow**:

.. code-block:: text

   1. runtime.post() called
        │
        ▼
   2. JobContext created (job_id, status=pending)
        │
        ▼
   3. Data sent to target slot
        │
        ▼
   4. Slot queues data
        │
        ▼
   5. Activation policy evaluates
        │
        ├──▶ Should activate = False ─▶ Stop (data stays in queue)
        │
        └──▶ Should activate = True
             │
             ▼
          6. JobContext.status = "running"
             │
             ▼
          7. Submit task to thread pool
             │
             ▼
          8. WorkerExecutor runs logic()
             │
             ▼
          9. Logic emits events
             │
             ▼
         10. JobContext.status = "completed" or "failed"

Runtime API Reference
---------------------

**exec()** - Start a flow:

.. code-block:: python

   worker_state = runtime.exec(flow_id: str) -> WorkerState

**post()** - Submit a job:

.. code-block:: python

   worker_state, job_context = runtime.post(
       flow_id: str,
       routine_id: str,
       slot: str,
       data: dict
   ) -> tuple[WorkerState, JobContext]

**get_job()** - Get job status:

.. code-block:: python

   job_context = runtime.get_job(job_id: str) -> JobContext | None

**wait_until_all_jobs_finished()** - Wait for completion:

.. code-block:: python

   runtime.wait_until_all_jobs_finished(timeout: float | None = None)

**shutdown()** - Shutdown runtime:

.. code-block:: python

   runtime.shutdown(wait: bool = True)

Common Patterns
---------------

**Pattern 1: Single-Shot Execution**

.. code-block:: python

   with Runtime() as runtime:
       runtime.exec("my_flow")
       runtime.post("my_flow", "start", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Pattern 2: Continuous Processing**

.. code-block:: python

   with Runtime() as runtime:
       runtime.exec("my_flow")

       while True:
           data = get_data_from_source()
           runtime.post("my_flow", "processor", "input", {"data": data})
           time.sleep(0.1)

**Pattern 3: Batching**

.. code-block:: python

   with Runtime() as runtime:
       runtime.exec("my_flow")

       batch = []
       for item in data_source:
           batch.append(item)
           if len(batch) >= 100:
               runtime.post("my_flow", "processor", "input", {
                   "batch": batch
               })
               batch = []

       # Process remaining
       if batch:
           runtime.post("my_flow", "processor", "input", {
               "batch": batch
           })

       runtime.wait_until_all_jobs_finished(timeout=30.0)

Pitfalls Reference
------------------

.. list-table:: Common Runtime Pitfalls
   :widths: 50 50
   :header-rows: 1

   * - Pitfall
     - Solution
   * - Forgetting context manager
     - Always use ``with Runtime()`` or call ``shutdown()``
   * - No timeout on wait
     - Always set timeout in ``wait_until_all_jobs_finished()``
   * - Posting before exec
     - Call ``exec()`` before ``post()``
   * - Thread pool too small
     - Set appropriate ``thread_pool_size``
   * - Not checking job status
     - Use ``get_job()`` to verify completion
   * - Blocking in thread pool
     - Don't use blocking I/O in logic functions

.. warning:: **Pitfall: Posting Before exec**

   Posting jobs before starting the flow causes errors:

   .. code-block:: python

      # WRONG - Order matters!
      runtime.post("flow", "routine", "slot", {})  # Error!
      runtime.exec("flow")

      # RIGHT - exec first, then post
      runtime.exec("flow")
      runtime.post("flow", "routine", "slot", {})

Next Steps
----------

Now that you understand Runtime, learn about:

- :doc:`../connections/simple_connection` - Connecting routines
- :doc:`../activation/immediate_policy` - Activation policies
- :doc:`../state/worker_state` - WorkerState for tracking
- :doc:`../concurrency/thread_pools` - Advanced concurrency

.. seealso::

   :doc:`../../api_reference/core/runtime`
      Complete Runtime API reference

   :doc:`../../user_guide/runtime`
      Comprehensive Runtime usage guide
