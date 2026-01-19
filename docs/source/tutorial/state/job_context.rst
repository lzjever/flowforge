JobContext: Per-Request Temporary State
========================================

JobContext is the mechanism for maintaining state within a single job execution.
It's temporary, short-lived state that exists only for the duration of one job.

.. note:: **What You'll Learn**

   - What JobContext is and when to use it
   - JobContext lifecycle and scope
   - Accessing JobContext in routines
   - Storing job-specific data and traces
   - Common JobContext patterns

.. note:: **Prerequisites**

   - :doc:`worker_state` - Understand WorkerState first

Understanding JobContext
------------------------

**JobContext** is a short-lived state container associated with a single job
execution. It's created when ``runtime.post()`` is called and destroyed when
the job completes.

.. code-block:: text

   Job Lifecycle (Short-Lived)
   │
   │  Job 1 created
   │  │
   │  ├─▶ JobContext {
   │  │     job_id: "abc-123",
   │  │     metadata: {user_id: 42},
   │  │     data: {},
   │  │     trace_log: []
   │  │   }
   │  │
   │  ├─▶ Routine A processes (can access JobContext)
   │  ├─▶ Routine B processes (can access JobContext)
   │  ├─▶ Routine C processes (can access JobContext)
   │  │
   │  └─▶ Job 1 completes → JobContext destroyed
   │
   │  Job 2 created → New JobContext (different job_id)
   │  ...
   │

**JobContext Characteristics**:

- **Scope**: Per-job (single execution)
- **Lifetime**: From job start to job completion
- **Visibility**: Accessible to all routines processing this job
- **Use cases**: Request metadata, tracing, temporary calculations

WorkerState vs JobContext
--------------------------

.. list-table::
   :widths: 25 25 25 25
   :header-rows: 1

   * - Aspect
     - WorkerState
     - JobContext
     - Use When...
   * - **Scope**
     - Worker (long-running)
     - Job (short-lived)
     -
   * - **Analogy**
     - Server process
     - HTTP request
     -
   * - **Good for**
     - Caches, counters, connections
     - Request params, user ID, trace
     -
   * - **Example**
     - Total requests processed
     - Current user's ID
     -

.. code-block:: text

   ┌─────────────────────────────────────────────────────────┐
   │                     Worker                              │
   │  (Long-Running Process)                                │
   │                                                         │
   │  ┌───────────────────────────────────────────────────┐ │
   │  │  WorkerState (Persistent across jobs)             │ │
   │  │  • Database connection pool                        │ │
   │  │  • Total jobs processed: 1000                      │ │
   │  │  • Cache: {...}                                    │ │
   │  └───────────────────────────────────────────────────┘ │
   │                                                         │
   │  Job 1 ──▶ ┌─────────────────────────────────┐         │
   │           │ JobContext (Temporary)           │         │
   │           │  • job_id: "abc-123"             │         │
   │           │  • metadata: {user_id: 42}       │         │
   │           │  • trace_log: [...]              │         │
   │           └─────────────────────────────────┘         │
   │                                                         │
   │  Job 2 ──▶ ┌─────────────────────────────────┐         │
   │           │ JobContext (Different!)          │         │
   │           │  • job_id: "def-456"             │         │
   │           │  • metadata: {user_id: 99}       │         │
   │           │  • trace_log: [...]              │         │
   │           └─────────────────────────────────┘         │
   └─────────────────────────────────────────────────────────┘

Accessing JobContext in Routines
----------------------------------

Use the ``get_current_job()`` function to access JobContext:

.. code-block:: python

   from routilux import Routine
   from routilux.activation_policies import immediate_policy
   from routilux.core import get_current_job

   class UserProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output", ["user_id", "result"])

           def process_logic(slot_data, policy_message, worker_state):
               # Get current job context
               job = get_current_job()

               if job:
                   # Access job metadata
                   user_id = job.metadata.get("user_id")
                   print(f"Processing for user {user_id}")

                   # Store job-specific data
                   job.set_data("processed_at", "2024-01-01")
                   job.set_data("items_processed", 5)

                   # Trace execution
                   job.trace("processor", "started", {"input": "data"})

                   # Emit result
                   self.emit("output", user_id=user_id, result="success")

                   job.trace("processor", "completed", {"result": "success"})

           self.set_logic(process_logic)
           self.set_activation_policy(immediate_policy())

.. tip:: **Always Check for None**

   ``get_current_job()`` returns ``None`` if called outside of a job context:

   .. code-block:: python

      job = get_current_job()
      if job:
          # Safe to access job properties
          user_id = job.metadata.get("user_id")
      else:
          # Not in a job context
          print("Not processing a job")

JobContext API Reference
------------------------

**Job Properties**:

.. code-block:: python

   job = get_current_job()

   # Unique job identifier
   job_id = job.job_id

   # Worker processing this job
   worker_id = job.worker_id

   # Flow this job belongs to
   flow_id = job.flow_id

   # Timestamps
   created_at = job.created_at
   completed_at = job.completed_at  # None if still running

   # Job status
   status = job.status  # "pending", "running", "completed", "failed"

   # Error if job failed
   error = job.error

**Metadata** (set at job creation):

.. code-block:: python

   # Set metadata when posting job
   runtime.post("flow", "routine", "slot", {},
                metadata={"user_id": 42, "request_id": "abc-123"})

   # Access in routine
   job = get_current_job()
   user_id = job.metadata.get("user_id")
   request_id = job.metadata.get("request_id")

**Job Data** (temporary job-specific storage):

.. code-block:: python

   # Store data
   job.set_data("key", "value")
   job.set_data("results", [1, 2, 3])

   # Retrieve data
   value = job.get_data("key", "default")
   results = job.get_data("results", [])

**Trace Log** (execution tracing):

.. code-block:: python

   # Add trace entry
   job.trace("routine_id", "action", {"details": "value"})

   # Trace entry structure:
   # {
   #     "timestamp": "2024-01-01T10:00:00",
   #     "routine_id": "routine_id",
   #     "action": "action",
   #     "details": {...}
   # }

Complete Example: Request Tracing
----------------------------------

Here's a complete example showing JobContext for request tracing:

.. code-block:: python
   :linenos:
   :name: state_job_context_tracing

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   from routilux.core import get_current_job

   # Stage 1: Request ingress
   class RequestIngress(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("request")
           self.add_event("validated", ["data"])

           def validate(slot_data, policy_message, worker_state):
               job = get_current_job()
               if job:
                   job.trace("ingress", "validating_request")

               requests = slot_data.get("request", [])
               if requests:
                   req = requests[0]
                   user_id = req.get("user_id", "anonymous")

                   # Store in job context for downstream routines
                   if job:
                       job.set_data("user_id", user_id)
                       job.set_data("request_received_at", req.get("timestamp"))

                   print(f"[Ingress] Validating request for user {user_id}")
                   job.trace("ingress", "validated", {"user_id": user_id})

                   self.emit("validated", data=req)

           self.set_logic(validate)
           self.set_activation_policy(immediate_policy())

   # Stage 2: Business logic
   class BusinessLogic(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("validated")
           self.add_event("processed", ["result"])

           def process(slot_data, policy_message, worker_state):
               job = get_current_job()
               if job:
                   job.trace("logic", "processing")

               # Access data from upstream routine
               user_id = None
               if job:
                   user_id = job.get_data("user_id")

               requests = slot_data.get("validated", [])
               if requests:
                   data = requests[0]

                   # Process...
                   result = f"processed_for_{user_id or 'unknown'}"

                   print(f"[Logic] Processing for user {user_id}")
                   job.trace("logic", "processed", {"result": result})

                   self.emit("processed", result=result)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Stage 3: Response
   class ResponseBuilder(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("processed")

           def build_response(slot_data, policy_message, worker_state):
               job = get_current_job()
               if job:
                   job.trace("response", "building")

               processed = slot_data.get("processed", [])
               if processed:
                   item = processed[0]
                   result = item.get("result")

                   # Get trace log for debugging
                   if job:
                       trace_log = job.trace_log
                       print(f"\n[Response] Building response")
                       print(f"Result: {result}")
                       print(f"Trace log ({len(trace_log)} entries):")
                       for entry in trace_log:
                           print(f"  - {entry['routine_id']}: {entry['action']}")

                       job.trace("response", "completed")
                       job.complete(status="completed")

           self.set_logic(build_response)
           self.set_activation_policy(immediate_policy())

   # Build tracing flow
   flow = Flow("traced_workflow")

   flow.add_routine(RequestIngress(), "ingress")
   flow.add_routine(BusinessLogic(), "logic")
   flow.add_routine(ResponseBuilder(), "response")

   flow.connect("ingress", "validated", "logic", "validated")
   flow.connect("logic", "processed", "response", "processed")

   FlowRegistry.get_instance().register_by_name("traced_workflow", flow)

   with Runtime(thread_pool_size=3) as runtime:
       runtime.exec("traced_workflow")

       # Post multiple requests with metadata
       requests = [
           {"user_id": "alice", "timestamp": "2024-01-01T10:00:00"},
           {"user_id": "bob", "timestamp": "2024-01-01T10:00:01"},
       ]

       for req in requests:
           # Include metadata with the job
           _, job_ctx = runtime.post(
               "traced_workflow",
               "ingress",
               "request",
               req,
               metadata={"user_id": req["user_id"], "request_id": f"req_{req['user_id']}"}
           )
           print(f"Posted job: {job_ctx.job_id}\n")

       runtime.wait_until_all_jobs_finished(timeout=10.0)

**Expected Output**:

.. code-block:: text

   Posted job: abc-123-def

   [Ingress] Validating request for user alice
   [Logic] Processing for user alice

   [Response] Building response
   Result: processed_for_alice
   Trace log (3 entries):
     - ingress: validating_request
     - ingress: validated
     - logic: processing
     - logic: processed
     - response: building
     - response: completed

   Posted job: def-456-ghi

   [Ingress] Validating request for user bob
   [Logic] Processing for user bob
   ...

Common JobContext Patterns
---------------------------

**Pattern 1: Request Chain Data Passing**

.. code-block:: python

   # Routine 1: Extract user info
   def auth_logic(slot_data, policy_message, worker_state):
       job = get_current_job()
       req = slot_data.get("request", [{}])[0]

       # Extract and store
       user_id = authenticate(req["token"])
       if job:
           job.set_data("user_id", user_id)
           job.set_data("permissions", get_permissions(user_id))

       self.emit("authenticated", user_id=user_id)

   # Routine 2: Use extracted info
   def business_logic(slot_data, policy_message, worker_state):
       job = get_current_job()
       # Retrieve from job context
       user_id = job.get_data("user_id")
       permissions = job.get_data("permissions", [])

       # Use for authorization
       if "admin" in permissions:
           # Do admin stuff
           pass

**Pattern 2: Error Tracking**

.. code-block:: python

   def error_handling_logic(slot_data, policy_message, worker_state):
       job = get_current_job()
       try:
           # Do risky operation
           result = risky_operation()
       except Exception as e:
           if job:
               job.set_data("error", str(e))
               job.set_data("error_type", type(e).__name__)
               job.trace("error", "occurred", {"error": str(e)})
               job.complete(status="failed", error=str(e))

**Pattern 3: Progress Tracking**

.. code-block:: python

   def multi_step_process(slot_data, policy_message, worker_state):
       job = get_current_job()

       steps = ["validate", "transform", "enrich", "save"]

       for i, step in enumerate(steps):
           # Do step
           result = execute_step(step)

           # Track progress
           if job:
               job.set_data("current_step", step)
               job.set_data("progress_percent", int((i + 1) / len(steps) * 100))
               job.trace("progress", f"completed_{step}")

**Pattern 4: Correlation ID**

.. code-block:: python

   # At job start, assign correlation ID
   runtime.post("flow", "start", "trigger", {},
                metadata={"correlation_id": "abc-123"})

   # In any routine, access it
   def any_logic(slot_data, policy_message, worker_state):
       job = get_current_job()
       correlation_id = job.metadata.get("correlation_id")

       # Use in logs for tracing
       print(f"[{correlation_id}] Processing...")

Pitfalls Reference
------------------

.. warning:: **Pitfall 1: Using JobContext for Long-Lived Data**

   JobContext is destroyed when job completes:

   .. code-block:: python

      # WRONG - Data will be lost after job completes
      def logic(slot_data, policy_message, worker_state):
          job = get_current_job()
          job.set_data("important_cache", expensive_computation())
          # This is lost when job ends!

      # RIGHT - Use WorkerState for persistent data
      def logic(slot_data, policy_message, worker_state):
          state = worker_state.get_routine_state("cache") or {}
          if "data" not in state:
              state["data"] = expensive_computation()
              worker_state.update_routine_state("cache", state)

.. warning:: **Pitfall 2: Assuming JobContext Exists**

   ``get_current_job()`` returns None outside of job context:

   .. code-block:: python

      # WRONG - Will crash
      def logic(slot_data, policy_message, worker_state):
          job = get_current_job()
          user_id = job.metadata.get("user_id")  # AttributeError if None!

      # RIGHT - Always check
      def logic(slot_data, policy_message, worker_state):
          job = get_current_job()
          if job:
              user_id = job.metadata.get("user_id")
          else:
              user_id = "system"

.. warning:: **Pitfall 3: Growing Trace Log Unbounded**

   Trace logs grow with each trace() call:

   .. code-block:: python

      # WRONG - Unbounded growth
      def logic(slot_data, policy_message, worker_state):
          job = get_current_job()
          for item in large_list:
              job.trace("processor", "processing", {"item": item})
              # Trace can get huge!

      # RIGHT - Sample traces or limit size
      def logic(slot_data, policy_message, worker_state):
          job = get_current_job()
          for i, item in enumerate(large_list):
              # Only trace first 10 and every 100th
              if i < 10 or i % 100 == 0:
                  job.trace("processor", "processing", {"index": i})

Next Steps
----------

- :doc:`state_isolation` - Understanding state boundaries
- :doc:`output_capture` - Capturing stdout per job
- :doc:`../error_handling/error_strategies` - Error handling patterns

.. seealso::

   :doc:`../../api_reference/core/context`
      Complete JobContext API reference

   :doc:`../../user_guide/state_management`
      Comprehensive state management guide
