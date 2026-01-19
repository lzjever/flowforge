State Isolation and Boundaries
===============================

Understanding state isolation boundaries is crucial for building correct
workflows. This tutorial explains how WorkerState, JobContext, and routine
state are isolated and how to properly manage data flow between them.

.. note:: **What You'll Learn**

   - State isolation boundaries and scopes
   - How data flows between isolated state containers
   - Proper patterns for sharing data across boundaries
   - Common isolation mistakes and how to avoid them

.. note:: **Prerequisites**

   - :doc:`worker_state` - Understand WorkerState
   - :doc:`job_context` - Understand JobContext

State Isolation Boundaries
--------------------------

Routilux has multiple levels of state isolation:

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │                    Process (Python)                        │
   │                                                             │
   │  ┌────────────────────────────────────────────────────┐    │
   │  │              Runtime                                │    │
   │  │                                                     │    │
   │  │  ┌──────────────────────────────────────────────┐  │    │
   │  │  │          Worker 1                            │  │    │
   │  │  │  ┌────────────────────────────────────────┐  │  │    │
   │  │  │  │         WorkerState                    │  │  │    │
   │  │  │  │  • routine_states: {...}               │  │  │    │
   │  │  │  │  • flow_id: "flow_a"                   │  │  │    │
   │  │  │  │  • status: "running"                   │  │  │    │
   │  │  │  └────────────────────────────────────────┘  │  │    │
   │  │  │                                              │  │    │
   │  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │    │
   │  │  │  │Job 1     │  │Job 2     │  │Job 3     │  │  │    │
   │  │  │  │(isolated)│  │(isolated)│  │(isolated)│  │  │    │
   │  │  │  └──────────┘  └──────────┘  └──────────┘  │  │    │
   │  │  │                                              │  │    │
   │  │  └──────────────────────────────────────────────┘  │    │
   │  │                                                     │    │
   │  │  ┌──────────────────────────────────────────────┐  │    │
   │  │  │          Worker 2 (Different WorkerState!)   │  │    │
   │  │  └──────────────────────────────────────────────┘  │    │
   │  │                                                     │    │
   │  └────────────────────────────────────────────────────┘  │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘

**Isolation Levels**:

1. **Process Level**: Python process (highest isolation boundary)
2. **Runtime Level**: Thread pools and event routing
3. **Worker Level**: WorkerState (isolated per worker)
4. **Job Level**: JobContext (isolated per job)
5. **Routine Level**: routine_states (isolated per routine)

What Is Isolated?
------------------

**✅ ISOLATED (Not Shared)**:

- ``JobContext`` instances - Each job has its own
- ``routine_states`` - Each routine's state is separate
- Different ``WorkerState`` instances - Workers don't share state

**❌ NOT ISOLATED (Shared)**:

- ``WorkerState`` - Shared by all jobs in the same worker
- Same flow's routines - Access same WorkerState
- Thread pool - Shared by all jobs

State Sharing Matrix
--------------------

.. list-table::
   :widths: 20 20 20 20 20
   :header-rows: 1

   * - Can Access?
     - Routine A State
     - Routine B State
     - JobContext
     - WorkerState
   * - **Routine A Logic**
     - ✅ Yes
     - ⚠️ Indirect
     - ✅ Yes
     - ✅ Yes
   * - **Routine B Logic**
     - ⚠️ Indirect
     - ✅ Yes
     - ✅ Yes
     - ✅ Yes
   * - **Job 1**
     - N/A
     - N/A
     - ✅ Yes (Job 1's)
     - ✅ Yes
   * - **Job 2**
     - N/A
     - N/A
     - ❌ No (different job!)
     - ✅ Yes (same worker)

Complete Example: State Isolation Demonstration
------------------------------------------------

.. code-block:: python
   :linenos:
   :name: state_isolation_demo

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   from routilux.core import get_current_job
   import time

   class StateDemoRoutine(Routine):
       def __init__(self, name):
           super().__init__()
           self.add_slot("input")
           self.add_event("output", ["routine", "worker_state_count", "job_data"])
           self.set_config(routine_name=name)

           def process(slot_data, policy_message, worker_state):
               routine_name = self.get_config("routine_name")
               job = get_current_job()

               # 1. Routine-specific state (isolated per routine)
               state = worker_state.get_routine_state(routine_name) or {}
               count = state.get("count", 0) + 1
               worker_state.update_routine_state(routine_name, {"count": count})

               # 2. Job data (isolated per job)
               job_data = "unknown"
               if job:
                   job_data = job.get_data("job_identifier", "not_set")
                   # Set job-specific data
                   job.set_data(f"processed_by_{routine_name}", True)

               # 3. Worker state (shared across all jobs in this worker)
               total_jobs = worker_state.routine_states.get("_meta", {}).get("total_jobs", 0)
               if job and not job.get_data("counted"):
                   total_jobs += 1
                   meta = worker_state.routine_states.get("_meta", {})
                   meta["total_jobs"] = total_jobs
                   worker_state.update_routine_state("_meta", meta)
                   job.set_data("counted", True)

               print(f"[{routine_name}] "
                     f"routine_count={count}, "
                     f"job_data={job_data}, "
                     f"worker_total_jobs={total_jobs}")

               self.emit("output",
                        routine=routine_name,
                        worker_state_count=count,
                        job_data=job_data)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Build isolation demo flow
   flow = Flow("isolation_demo")

   flow.add_routine(StateDemoRoutine("routine_a"), "routine_a")
   flow.add_routine(StateDemoRoutine("routine_b"), "routine_b")
   flow.add_routine(StateDemoRoutine("routine_c"), "routine_c")

   FlowRegistry.get_instance().register_by_name("isolation_demo", flow)

   with Runtime(thread_pool_size=3) as runtime:
       worker_state = runtime.exec("isolation_demo")

       print("=== Job 1: Chain A→B ===")
       # Job 1: Chain through routines
       _, job1 = runtime.post("isolation_demo", "routine_a", "input", {},
                             metadata={"job_identifier": "job_1"})
       time.sleep(0.1)

       print("\n=== Job 2: Chain B→C ===")
       _, job2 = runtime.post("isolation_demo", "routine_b", "input", {},
                             metadata={"job_identifier": "job_2"})
       time.sleep(0.1)

       print("\n=== Job 3: Routine C ===")
       _, job3 = runtime.post("isolation_demo", "routine_c", "input", {},
                             metadata={"job_identifier": "job_3"})

       runtime.wait_until_all_jobs_finished(timeout=5.0)

       # Check final state
       print("\n=== Final WorkerState ===")
       for routine_id, state in worker_state.routine_states.items():
           print(f"  {routine_id}: {state}")

**Expected Output**:

.. code-block:: text

   === Job 1: Chain A→B ===
   [routine_a] routine_count=1, job_data=job_1, worker_total_jobs=1
   [routine_b] routine_count=1, job_data=job_1, worker_total_jobs=1

   === Job 2: Chain B→C ===
   [routine_b] routine_count=2, job_data=job_2, worker_total_jobs=2
   [routine_c] routine_count=1, job_data=job_2, worker_total_jobs=2

   === Job 3: Routine C ===
   [routine_c] routine_count=2, job_data=job_3, worker_total_jobs=3

   === Final WorkerState ===
     routine_a: {'count': 1}
     routine_b: {'count': 2}
     routine_c: {'count': 2}
     _meta: {'total_jobs': 3}

**Key Observations**:

1. **routine_a**: count=1 (only ran in Job 1)
2. **routine_b**: count=2 (ran in Job 1 and Job 2)
3. **routine_c**: count=2 (ran in Job 2 and Job 3)
4. **job_data**: Each job sees its own identifier
5. **worker_total_jobs**: Shared across all jobs (WorkerState)

Cross-Routine Communication Patterns
------------------------------------

**Pattern 1: Via JobContext (Recommended for job-scoped data)**

.. code-block:: python

   # Routine A: Store data in JobContext
   def logic_a(slot_data, policy_message, worker_state):
       job = get_current_job()
       job.set_data("user_profile", fetch_user_profile())

   # Routine B: Read from JobContext
   def logic_b(slot_data, policy_message, worker_state):
       job = get_current_job()
       profile = job.get_data("user_profile")
       # Use profile...

**Pattern 2: Via WorkerState (For shared cache/resources)**

.. code-block:: python

   # Routine A: Initialize shared resource
   def logic_a(slot_data, policy_message, worker_state):
       if "db_pool" not in worker_state.routine_states:
           worker_state.update_routine_state("_shared", {
               "db_pool": create_db_pool()
           })

   # Routine B: Use shared resource
   def logic_b(slot_data, policy_message, worker_state):
       shared = worker_state.get_routine_state("_shared") or {}
       pool = shared.get("db_pool")
       conn = pool.get_connection()

**Pattern 3: Via Events/Slots (For data flow)**

.. code-block:: python

   # Routine A: Emit data
   def logic_a(slot_data, policy_message, worker_state):
       self.emit("processed", result=42, metadata={"key": "value"})

   # Routine B: Receive via slot
   def logic_b(slot_data, policy_message, worker_state):
       data = slot_data.get("processed", [{}])[0]
       result = data.get("result")

Isolation Pitfalls
------------------

.. warning:: **Pitfall 1: Assuming Jobs Share JobContext**

   Jobs do NOT share JobContext:

   .. code-block:: python

      # Job 1 sets data
      job1.set_data("my_value", 123)

      # Job 2 CANNOT access Job 1's JobContext!
      # Each job has its own isolated JobContext

   **Solution**: Use WorkerState for cross-job data:

   .. code-block:: python

      # Use WorkerState for shared data
      worker_state.update_routine_state("_shared", {"my_value": 123})

.. warning:: **Pitfall 2: Assuming Routines Share routine_states**

   Each routine has its own isolated state:

   .. code-block:: python

      # Routine A's state
      worker_state.update_routine_state("routine_a", {"count": 100})

      # Routine B CANNOT access Routine A's state directly!
      # state = worker_state.get_routine_state("routine_a")  # Only if explicitly allowed

   **Solution**: Use shared state key:

   .. code-block:: python

      # Shared state (accessible by all routines)
      worker_state.update_routine_state("_shared", {"count": 100})

.. warning:: **Pitfall 3: Leaking JobContext Data Between Jobs**

   JobContext is destroyed when job completes:

   .. code-block:: python

      # Job 1
      job1.set_data("cache", expensive_computation())

      # Job 2 - job1's JobContext is gone!
      # Must recompute

   **Solution**: Use WorkerState for caching:

   .. code-block:: python

      # Cache in WorkerState (persists across jobs)
      state = worker_state.get_routine_state("_cache") or {}
      if "result" not in state:
          state["result"] = expensive_computation()
          worker_state.update_routine_state("_cache", state)

.. warning:: **Pitfall 4: Race Conditions on Shared State**

   Concurrent jobs accessing WorkerState can cause race conditions:

   .. code-block:: python

      # WRONG - Race condition!
      def logic(slot_data, policy_message, worker_state):
          state = worker_state.get_routine_state("_shared") or {}
          count = state.get("count", 0)  # Read
          # ... processing ...
          state["count"] = count + 1  # Write
          worker_state.update_routine_state("_shared", state)
          # Problem: Two jobs might read same count!

   **Solution**: Use atomic operations or avoid shared state:

   .. code-block:: python

      # RIGHT - Use JobContext for job-specific counters
      def logic(slot_data, policy_message, worker_state):
          job = get_current_job()
          count = job.get_data("count", 0) + 1
          job.set_data("count", count)

      # OR - Use WorkerState for aggregate statistics only
      # Accept that counts might be slightly off under high concurrency

State Decision Tree
-------------------

Use this decision tree to choose the right state type:

.. code-block:: text

   Need to store data?
        │
        ├─ Is it job-specific (request ID, user ID, trace)?
        │     └─▶ Use JobContext
        │
        ├─ Should it persist across jobs (cache, connection pool)?
        │     └─▶ Use WorkerState
        │
        ├─ Is it routine-specific configuration?
        │     └─▶ Use routine_states in WorkerState
        │
        └─ Should other jobs access it?
              ├─ Yes ─▶ WorkerState (shared key like "_shared")
              └─ No ─▶ JobContext or routine_states

Best Practices
--------------

1. **Default to JobContext**: Use JobContext for most job-specific data
2. **Use WorkerState for caching**: Cache expensive computations in WorkerState
3. **Namespace shared state**: Use "_shared", "_cache", "_meta" prefixes
4. **Document shared state**: Comment which routines access which state
5. **Avoid over-sharing**: Minimize shared state to reduce coupling

Next Steps
----------

- :doc:`output_capture` - Capturing stdout per job
- :doc:`../concurrency/thread_pools` - Thread pool and concurrency
- :doc:`../../pitfalls/state_management` - State management pitfalls

.. seealso::

   :doc:`../../user_guide/state_management`
      Comprehensive state management guide
