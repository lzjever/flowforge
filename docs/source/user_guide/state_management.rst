State Management
================

Routilux v2 provides a comprehensive two-tier state management system designed
for clarity and proper separation of concerns:

- **WorkerState** - Persistent, worker-level state (long-running, shared across jobs)
- **JobContext** - Temporary, job-level state (single request execution)

.. note:: **Key Concept**

   Think of it like a web server:

   - **WorkerState** = The server process (long-running, caches, connection pools)
   - **JobContext** = An HTTP request (temporary, request-specific data)

.. _worker_state:

WorkerState
-----------

WorkerState is a long-running state container associated with a worker (execution
instance). It persists across multiple job executions and is ideal for:

- **Caching** expensive computations
- **Connection pooling** (database, network)
- **Counters** and statistics tracking
- **Configuration** that changes over time
- **Learned/adapted** behavior

**Creating WorkerState**:

WorkerState is automatically created when you call ``runtime.exec()``:

.. code-block:: python

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def process(slot_data, policy_message, worker_state):
               # Access WorkerState (passed to logic function)
               state = worker_state.get_routine_state("my_routine") or {}
               count = state.get("count", 0) + 1
               worker_state.update_routine_state("my_routine", {"count": count})

               self.emit("output", result=count)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   flow = Flow("my_flow")
   flow.add_routine(MyRoutine(), "routine")
   FlowRegistry.get_instance().register_by_name("my_flow", flow)

   with Runtime() as runtime:
       # Creates WorkerState for this flow execution
       worker_state = runtime.exec("my_flow")

**WorkerState Properties**:

.. code-block:: python

   # WorkerState attributes
   worker_id = worker_state.worker_id        # Unique worker identifier
   flow_id = worker_state.flow_id            # Flow this worker belongs to
   status = worker_state.status              # "starting", "running", "stopped"
   routine_states = worker_state.routine_states  # Dict of routine-specific states

**Routine-Specific State**:

Each routine can maintain its own state within WorkerState:

.. code-block:: python

   # Get routine state
   state = worker_state.get_routine_state("my_routine_id")
   # Returns: {"key": "value"} or None if not set

   # Update routine state
   worker_state.update_routine_state("my_routine_id", {
       "count": 100,
       "last_processed": "item_123",
       "cache": {...}
   })

**WorkerState Lifecycle**:

.. code-block:: text

   Runtime created
       │
       ▼
   runtime.exec(flow_id) ──▶ WorkerState created
       │
       ├─▶ Job 1 ──▶ WorkerState shared across jobs
       ├─▶ Job 2 ──▶ WorkerState shared across jobs
       ├─▶ Job 3 ──▶ WorkerState shared across jobs
       │
       ▼
   runtime.shutdown() ──▶ WorkerState destroyed

.. _job_context:

JobContext
----------

JobContext is a temporary state container for a single job execution. It's created
when ``runtime.post()`` is called and destroyed when the job completes.

**JobContext is ideal for**:

- **Request metadata** (user_id, request_id, correlation_id)
- **Job-specific data** (input parameters, intermediate results)
- **Execution tracing** (debug information, audit trails)
- **Temporary calculations** (job-scoped data)

**Accessing JobContext**:

.. code-block:: python

   from routilux.core import get_current_job

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def process(slot_data, policy_message, worker_state):
               # Get current job context
               job = get_current_job()
               if job:
                   # Access metadata
                   user_id = job.metadata.get("user_id")
                   request_id = job.metadata.get("request_id")

                   # Store job-specific data
                   job.set_data("processed", True)
                   job.set_data("result_count", 42)

                   # Trace execution
                   job.trace("processor", "started", {"timestamp": ...})

               self.emit("output", result="done")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

**JobContext Properties**:

.. code-block:: python

   # JobContext attributes
   job_id = job.job_id                  # Unique job identifier
   worker_id = job.worker_id            # Worker processing this job
   flow_id = job.flow_id                # Flow this job belongs to
   created_at = job.created_at          # Creation timestamp
   completed_at = job.completed_at      # Completion timestamp (None if running)
   status = job.status                  # "pending", "running", "completed", "failed"
   error = job.error                    # Error message if failed

**Metadata vs Data**:

.. code-block:: python

   # Set metadata when posting job
   worker_state, job_context = runtime.post(
       "my_flow", "routine", "slot", {},
       metadata={"user_id": 123, "request_id": "abc-123"}
   )

   # In routine
   job = get_current_job()
   user_id = job.metadata.get("user_id")        # From metadata
   processed = job.get_data("processed")        # From job data

**Tracing Execution**:

.. code-block:: python

   # Add trace entries
   job.trace("routine_id", "action", {"details": "value"})

   # Trace entry structure:
   # {
   #     "timestamp": "2024-01-01T10:00:00",
   #     "routine_id": "routine_id",
   #     "action": "action",
   #     "details": {...}
   # }

   # Get trace log
   trace_log = job.trace_log

.. _state_comparison:

WorkerState vs JobContext Comparison
------------------------------------

Understanding when to use each is critical:

.. list-table::
   :widths: 20 20 30 30
   :header-rows: 1

   * - Aspect
     - WorkerState
     - JobContext
     - Example
   * - **Lifetime**
     - Worker lifecycle (hours/days)
     - Job lifecycle (seconds/minutes)
     -
   * - **Scope**
     - Shared across all jobs
     - Isolated per job
     -
   * - **Use For**
     - Caches, counters, connections
     - Request params, tracing
     -
   * - **Analogy**
     - Server process
     - HTTP request
     -
   * - **Database Cache**
     - ✅ Connections
     - ❌ Query results
     -
   * - **User Session**
     - ✅ Session data
     - ❌ Request ID
     -
   * - **Statistics**
     - ✅ Total processed
     - ❌ Current job data
     -

**Decision Tree**:

.. code-block:: text

   Need to store data?
        │
        ├─ Is it specific to THIS job/request?
        │     └─▶ Use JobContext
        │
        ├─ Should it persist across jobs?
        │     └─▶ Use WorkerState
        │
        └─ Should other jobs access it?
              ├─ Yes ─▶ WorkerState (shared key like "_shared")
              └─ No ─▶ JobContext

Complete Example: State Management in Action
---------------------------------------------

.. code-block:: python

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy, batch_size_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   from routilux.core import get_current_job
   import time

   class DataProcessor(Routine):
       """Demonstrates both WorkerState and JobContext usage."""

       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def process(slot_data, policy_message, worker_state):
               # === WorkerState: Persistent cache ===
               cache_state = worker_state.get_routine_state("processor") or {}
               cache = cache_state.get("cache", {})

               input_list = slot_data.get("input", [])
               if input_list:
                   item = input_list[0]
                   key = item.get("key")

                   # Check cache
                   if key in cache:
                       print(f"[WorkerState] Cache HIT: {key}")
                       result = cache[key]
                   else:
                       print(f"[WorkerState] Cache MISS: {key}")
                       # Simulate expensive processing
                       time.sleep(0.1)
                       result = f"processed_{key}"
                       cache[key] = result
                       worker_state.update_routine_state("processor", {
                           "cache": cache,
                           "cache_hits": cache_state.get("cache_hits", 0),
                           "cache_misses": cache_state.get("cache_misses", 0) + 1
                       })

                   # === JobContext: Job-specific tracking ===
                   job = get_current_job()
                   if job:
                       # Track this job's processing
                       job.set_data("processed_key", key)
                       job.set_data("result", result)

                       # Trace execution
                       job.trace("processor", "completed", {
                           "key": key,
                           "cache_hit": key in cache,
                           "timestamp": time.time()
                       })

                   self.emit("output", result=result)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Build flow
   flow = Flow("state_demo")
   flow.add_routine(DataProcessor(), "processor")
   FlowRegistry.get_instance().register_by_name("state_demo", flow)

   # Execute
   with Runtime() as runtime:
       worker_state = runtime.exec("state_demo")

       # Job 1: First access (cache miss)
       _, job1 = runtime.post("state_demo", "processor", "input", {"key": "test"})
       time.sleep(0.2)

       # Job 2: Same key (cache hit)
       _, job2 = runtime.post("state_demo", "processor", "input", {"key": "test"})
       time.sleep(0.2)

       # Job 3: Different key (cache miss)
       _, job3 = runtime.post("state_demo", "processor", "input", {"key": "other"})
       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   [WorkerState] Cache MISS: test
   [WorkerState] Cache HIT: test
   [WorkerState] Cache MISS: other

.. _state_patterns:

Common State Management Patterns
--------------------------------

**Pattern 1: Connection Pool**

.. code-block:: python

   def init_db_pool(slot_data, policy_message, worker_state):
       # Initialize database connection pool in WorkerState
       state = worker_state.get_routine_state("db_accessor") or {}
       if "pool" not in state:
           state["pool"] = create_connection_pool()
           worker_state.update_routine_state("db_accessor", state)

**Pattern 2: Request Counter**

.. code-block:: python

   def count_request(slot_data, policy_message, worker_state):
       # WorkerState: Total across all requests
       state = worker_state.get_routine_state("counter") or {}
       total = state.get("total_requests", 0) + 1
       worker_state.update_routine_state("counter", {"total_requests": total})

       # JobContext: Per-request sequence number
       job = get_current_job()
       if job:
           seq = job.get_data("sequence", 0) + 1
           job.set_data("sequence", seq)

**Pattern 3: Cached Computation**

.. code-block:: python

   def expensive_computation(input_data):
       # Use WorkerState for caching results
       cache_key = hash(input_data)

       state = worker_state.get_routine_state("cache") or {}
       cache = state.get("data", {})

       if cache_key not in cache:
           # Not cached, compute
           result = compute_expensive(input_data)
           cache[cache_key] = result
           worker_state.update_routine_state("cache", {"data": cache})

       return cache[cache_key]

**Pattern 4: Request Chain Data**

.. code-block:: python

   # Routine 1: Extract and store in JobContext
   def auth_logic(slot_data, policy_message, worker_state):
       job = get_current_job()
       if job:
           token = slot_data.get("auth", [{}])[0].get("token")
           user_id = validate_token(token)
           job.set_data("user_id", user_id)
           job.set_data("permissions", get_permissions(user_id))

   # Routine 2: Read from JobContext
   def business_logic(slot_data, policy_message, worker_state):
       job = get_current_job()
       if job:
           user_id = job.get_data("user_id")
           permissions = job.get_data("permissions", [])
           if "admin" in permissions:
               # Do admin stuff
               pass

.. _state_best_practices:

Best Practices
-------------

**DO ✅**:

- Use WorkerState for: caches, connection pools, counters, configuration
- Use JobContext for: request metadata, tracing, temporary data
- Use descriptive state keys: ``"user_cache"`` instead of ``"cache"``
- Namespace shared state: ``"_shared_cache"``, ``"_global_config"``
- Check for None when using ``get_current_job()``
- Document state schemas in docstrings

**DON'T ❌**:

- Don't use JobState (removed in v2)
- Don't use JobContext for persistent data (it's temporary)
- Don't use WorkerState for job-specific data (use JobContext)
- Don't store non-serializable objects (connections, file handles, etc.)
- Don't let state grow unbounded (implement limits)
- Don't assume ``get_current_job()`` always returns a value

**State Key Naming Conventions**:

.. list-table::
   :widths: 40 60
   :header-rows: 1

   * - Pattern
     - When to Use
   * - ``routine_id`` (routine-specific)
     - State private to one routine
   * - ``_shared_*`` (shared across routines)
     - State accessed by multiple routines
   * - ``_cache`` (caching)
     - Cached computation results
   * - ``_config`` (configuration)
     - Dynamic configuration
   * - ``_meta`` (metadata)
     - Worker metadata (counts, stats)

**Thread Safety Considerations**:

WorkerState is designed for concurrent access, but be careful with complex
operations:

.. code-block:: python

   # Safe: Simple get/update
   state = worker_state.get_routine_state("counter") or {}
   count = state.get("count", 0) + 1
   worker_state.update_routine_state("counter", {"count": count})

   # Potentially unsafe: Complex read-modify-write
   state = worker_state.get_routine_state("counter") or {}
   count = state.get("count", 0)
   # ... long processing ...
   state["count"] = count + 1  # Another job might have updated!
   worker_state.update_routine_state("counter", state)

   # Solution: Use JobContext for precise per-job tracking
   job = get_current_job()
   if job:
       count = job.get_data("count", 0) + 1
       job.set_data("count", count)

.. _state_monitoring:

Monitoring State
---------------

**Inspecting WorkerState**:

.. code-block:: python

   # Get all routine states
   all_states = worker_state.routine_states

   # Check specific routine state
   processor_state = worker_state.get_routine_state("processor")
   print(f"Processor state: {processor_state}")

   # Worker metadata
   print(f"Worker ID: {worker_state.worker_id}")
   print(f"Flow ID: {worker_state.flow_id}")
   print(f"Status: {worker_state.status}")

**Inspecting JobContext**:

.. code-block:: python

   # Get job details
   job = runtime.get_job(job_id)
   if job:
       print(f"Job ID: {job.job_id}")
       print(f"Status: {job.status}")
       print(f"Metadata: {job.metadata}")
       print(f"Data: {job.data}")
       print(f"Trace log: {job.trace_log}")

**Debugging State Issues**:

.. code-block:: python

   def debug_logic(slot_data, policy_message, worker_state):
       # Print WorkerState info
       print(f"WorkerState: {worker_state.routine_states}")

       # Print JobContext info
       job = get_current_job()
       if job:
           print(f"JobContext: job_id={job.job_id}, data={job.data}")
       else:
           print("JobContext: None (not in job context)")

Next Steps
----------

- :doc:`../tutorial/state/worker_state` - Detailed WorkerState tutorial
- :doc:`../tutorial/state/job_context` - Detailed JobContext tutorial
- :doc:`../tutorial/state/state_isolation` - State isolation boundaries
- :doc:`../pitfalls/state_management` - State management pitfalls

.. seealso::

   :doc:`../api_reference/core/worker`
      WorkerState API reference

   :doc:`../api_reference/core/context`
      JobContext API reference
