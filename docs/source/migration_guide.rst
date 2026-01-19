Migration Guide: v1 to v2 Architecture
========================================

This guide helps you migrate your Routilux workflows from the v1 architecture
to the v2 architecture (`refactor/architecture-v2` branch).

.. note:: **What Changed in v2**

   The v2 architecture introduces significant changes to state management,
   execution model, and API structure while maintaining the core event-driven
   workflow concepts.

Key Changes Summary
-------------------

.. list-table::
   :widths: 40 30 30
   :header-rows: 1

   * - Concept
     - v1 (Old)
     - v2 (New)
   * - **State Management**
     - JobState
     - WorkerState + JobContext
   * - **Job Execution**
     - JobManager
     - Runtime
   * - **State Scope**
     - Single state object
     - Worker-level (persistent) + Job-level (temporary)
   * - **State Access**
     - job_state.get_routine_state()
     - worker_state.get_routine_state()
   * - **Job-Level Data**
     - job_state.job_data
     - JobContext.data (via get_current_job())
   * - **Execution Posting**
     - flow.post_job()
     - runtime.post()
   * - **Flow Registration**
     - Not required
     - FlowRegistry.register_by_name() required

---

Breaking Change 1: JobState → WorkerState + JobContext
------------------------------------------------------

**v1 Code**:

.. code-block:: python
   :emphasize-lines: 11, 14, 15

   # v1 - Using JobState
   from routilux import Routine, Flow
   from routilux.execution import JobManager

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def process(job_state, slot_data):
               # Get routine state
               state = job_state.get_routine_state("my_routine") or {}
               count = state.get("count", 0) + 1
               job_state.set_routine_state("my_routine", {"count": count})

               # Get job data
               job_data = job_state.job_data
               user_id = job_data.get("user_id")

               self.emit("output", result=count)

           self.set_logic(process)

**v2 Code**:

.. code-block:: python
   :emphasize-lines: 11, 13, 14, 15

   # v2 - Using WorkerState + JobContext
   from routilux import Routine
   from routilux.activation_policies import immediate_policy
   from routilux.core import get_current_job

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def process(slot_data, policy_message, worker_state):
               # Get routine state from WorkerState
               state = worker_state.get_routine_state("my_routine") or {}
               count = state.get("count", 0) + 1
               worker_state.update_routine_state("my_routine", {"count": count})

               # Get job data from JobContext
               job = get_current_job()
               if job:
                   user_id = job.metadata.get("user_id")

               self.emit("output", result=count)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

**Key Differences**:

1. **Logic signature**: ``process(job_state, slot_data)`` → ``process(slot_data, policy_message, worker_state)``
2. **State update**: ``job_state.set_routine_state()`` → ``worker_state.update_routine_state()``
3. **Job data**: ``job_state.job_data`` → ``job.data`` (via ``get_current_job()``)
4. **Activation policy**: Required in v2 (was implicit in v1)

---

Breaking Change 2: JobManager → Runtime
----------------------------------------

**v1 Code**:

.. code-block:: python
   :emphasize-lines: 1, 13

   # v1 - Using JobManager
   from routilux import Flow
   from routilux.execution import JobManager

   flow = Flow("my_flow")
   flow.add_routine(MyRoutine(), "routine1")

   # Create job manager
   manager = JobManager()

   # Submit jobs
   job_id = flow.post_job("routine1", "input", {"data": "value"})
   manager.wait_until_complete()

**v2 Code**:

.. code-block:: python
   :emphasize-lines: 1, 14, 15, 18

   # v2 - Using Runtime
   from routilux import Flow, Runtime
   from routilux.monitoring.flow_registry import FlowRegistry

   flow = Flow("my_flow")
   flow.add_routine(MyRoutine(), "routine1")

   # Register flow (REQUIRED in v2)
   FlowRegistry.get_instance().register_by_name("my_flow", flow)

   # Create runtime
   with Runtime(thread_pool_size=2) as runtime:
       # Start the flow
       runtime.exec("my_flow")

       # Submit jobs
       worker_state, job_context = runtime.post(
           "my_flow", "routine1", "input", {"data": "value"}
       )

       # Wait for completion
       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Key Differences**:

1. **Execution manager**: ``JobManager`` → ``Runtime``
2. **Flow registration**: Not required → Required (``FlowRegistry.register_by_name()``)
3. **Job posting**: ``flow.post_job()`` → ``runtime.post()``
4. **Context manager**: Optional → Recommended (``with Runtime()``)
5. **Return values**: ``job_id`` → ``worker_state, job_context`` tuple

---

Breaking Change 3: Logic Function Signature
-------------------------------------------

**v1 Logic Signature**:

.. code-block:: python

   # v1
   def my_logic(job_state, slot_data):
       # job_state: JobState object
       # slot_data: dict[str, list[dict]]

       state = job_state.get_routine_state("routine_id") or {}
       data = slot_data.get("input", [{}])[0]

**v2 Logic Signature**:

.. code-block:: python

   # v2
   def my_logic(slot_data, policy_message, worker_state):
       # slot_data: dict[str, list[dict]] - Data from slots
       # policy_message: Any - Message from activation policy
       # worker_state: WorkerState object

       state = worker_state.get_routine_state("routine_id") or {}
       data = slot_data.get("input", [{}])[0]

**Key Differences**:

1. **Parameter order**: ``job_state, slot_data`` → ``slot_data, policy_message, worker_state``
2. **New parameter**: ``policy_message`` - contains activation policy information
3. **Renamed parameter**: ``job_state`` → ``worker_state`` (different semantics)

---

Breaking Change 4: Job-Level Data
---------------------------------

**v1 Code**:

.. code-block:: python
   :emphasize-lines: 7

   # v1 - Using job_state.job_data
   def process(job_state, slot_data):
       # Store job-specific data
       job_state.job_data["user_id"] = 123
       job_state.job_data["request_id"] = "abc-123"

       # Retrieve job-specific data
       user_id = job_state.job_data.get("user_id")

**v2 Code**:

.. code-block:: python
   :emphasize-lines: 8

   # v2 - Using JobContext
   from routilux.core import get_current_job

   def process(slot_data, policy_message, worker_state):
       job = get_current_job()
       if job:
           # Store job-specific data
           job.set_data("user_id", 123)
           job.set_data("request_id", "abc-123")

           # Retrieve job-specific data
           user_id = job.get_data("user_id")

**Key Differences**:

1. **Data location**: ``job_state.job_data`` → ``job.data`` (via ``JobContext``)
2. **Access method**: Direct attribute access → ``get_data()`` / ``set_data()`` methods
3. **Must check for None**: ``get_current_job()`` returns ``None`` outside job context

---

Breaking Change 5: Routine State Management
-------------------------------------------

**v1 Code**:

.. code-block:: python
   :emphasize-lines: 6, 7

   # v1
   def process(job_state, slot_data):
       # Get state
       state = job_state.get_routine_state("routine_id") or {}

       # Set state
       job_state.set_routine_state("routine_id", {"count": 100})

       # Alternative: Use shared state
       job_state.shared_data["global_counter"] += 1

**v2 Code**:

.. code-block:: python
   :emphasize-lines: 6, 7, 11

   # v2
   def process(slot_data, policy_message, worker_state):
       # Get state
       state = worker_state.get_routine_state("routine_id") or {}

       # Set state (update replaces entire state)
       worker_state.update_routine_state("routine_id", {"count": 100})

       # Alternative: Use JobContext for job-specific data
       job = get_current_job()
       if job:
           job.set_data("global_counter", job.get_data("global_counter", 0) + 1)

**Key Differences**:

1. **State object**: ``job_state`` → ``worker_state``
2. **Set method**: ``set_routine_state()`` → ``update_routine_state()``
3. **Shared data**: ``job_state.shared_data`` → ``JobContext.data`` (via ``get_current_job()``)
4. **Method name**: Changed from "set" to "update" to indicate replacement semantics

---

Breaking Change 6: Flow Registration (REQUIRED)
----------------------------------------------

**v1 Code**:

.. code-block:: python

   # v1 - Flow registration not required
   flow = Flow("my_flow")
   flow.add_routine(MyRoutine(), "routine1")

   # Could execute directly without registration
   manager = JobManager()
   manager.execute_flow(flow)

**v2 Code**:

.. code-block:: python
   :emphasize-lines: 7, 12

   # v2 - Flow registration is REQUIRED
   from routilux.monitoring.flow_registry import FlowRegistry

   flow = Flow("my_flow")
   flow.add_routine(MyRoutine(), "routine1")

   # MUST register before execution
   FlowRegistry.get_instance().register_by_name("my_flow", flow)

   # Now can execute
   with Runtime() as runtime:
       runtime.exec("my_flow")

**Key Differences**:

1. **Registration**: Optional → Required
2. **Registry class**: N/A → ``FlowRegistry`` singleton
3. **Execution method**: ``manager.execute_flow()`` → ``runtime.exec(flow_id)``

---

Breaking Change 7: Activation Policies (Now Required)
----------------------------------------------------

**v1 Code**:

.. code-block:: python

   # v1 - No explicit activation policy required
   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def process(job_state, slot_data):
               self.emit("output", result="done")

           self.set_logic(process)
           # No activation policy - executed immediately by default

**v2 Code**:

.. code-block:: python
   :emphasize-lines: 1, 12, 16

   # v2 - Activation policy REQUIRED
   from routilux.activation_policies import immediate_policy

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def process(slot_data, policy_message, worker_state):
               self.emit("output", result="done")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())  # REQUIRED!

**Key Differences**:

1. **Import**: Need to import from ``routilux.activation_policies``
2. **Required**: Must call ``set_activation_policy()``
3. **Default behavior**: No default - routine won't execute without policy

---

Step-by-Step Migration Example
------------------------------

Let's migrate a complete v1 workflow to v2.

**v1 Code (Old)**:

.. code-block:: python

   # v1 - Old architecture
   from routilux import Routine, Flow
   from routilux.execution import JobManager

   class DataProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("data")
           self.add_event("result")

           def process(job_state, slot_data):
               # Get state
               state = job_state.get_routine_state("processor") or {}
               count = state.get("count", 0) + 1
               job_state.set_routine_state("processor", {"count": count})

               # Process data
               data_list = slot_data.get("data", [])
               if data_list:
                   item = data_list[0]
                   result = item.get("value", 0) * 2
                   self.emit("result", result=result)

           self.set_logic(process)

   # Create flow
   flow = Flow("data_pipeline")
   flow.add_routine(DataProcessor(), "processor")

   # Execute
   manager = JobManager()
   job_id = flow.post_job("processor", "data", {"value": 21})
   manager.wait_until_complete()

**v2 Code (New)**:

.. code-block:: python

   # v2 - New architecture
   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   class DataProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("data")
           self.add_event("result")

           def process(slot_data, policy_message, worker_state):
               # Get state
               state = worker_state.get_routine_state("processor") or {}
               count = state.get("count", 0) + 1
               worker_state.update_routine_state("processor", {"count": count})

               # Process data
               data_list = slot_data.get("data", [])
               if data_list:
                   item = data_list[0]
                   result = item.get("value", 0) * 2
                   self.emit("result", result=result)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Create flow
   flow = Flow("data_pipeline")
   flow.add_routine(DataProcessor(), "processor")

   # Register flow (REQUIRED)
   FlowRegistry.get_instance().register_by_name("data_pipeline", flow)

   # Execute
   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("data_pipeline")
       worker_state, job_context = runtime.post(
           "data_pipeline", "processor", "data", {"value": 21}
       )
       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Migration Steps**:

1. ✅ Change imports (add ``Runtime``, ``FlowRegistry``, ``immediate_policy``)
2. ✅ Update logic signature (``job_state, slot_data`` → ``slot_data, policy_message, worker_state``)
3. ✅ Update state access (``job_state.get_routine_state()`` → ``worker_state.get_routine_state()``)
4. ✅ Update state modification (``job_state.set_routine_state()`` → ``worker_state.update_routine_state()``)
5. ✅ Add activation policy (``self.set_activation_policy(immediate_policy())``)
6. ✅ Register flow (``FlowRegistry.register_by_name()``)
7. ✅ Use Runtime instead of JobManager
8. ✅ Update job posting (``runtime.post()`` instead of ``flow.post_job()``)

---

Quick Reference Migration Checklist
-----------------------------------

Use this checklist to ensure you've migrated all v1 code:

.. list-table::
   :widths: 60 20 20
   :header-rows: 1

   * - Item
     - v1
     - v2
   * - Import JobManager
     - ✅
     - ❌ Use Runtime
   * - Import FlowRegistry
     - ❌
     - ✅ Required
   * - Import activation policies
     - ❌
     - ✅ Required
   * - Logic: job_state parameter
     - ✅
     - ❌ Use worker_state
   * - Logic: slot_data parameter
     - ✅
     - ✅ (moved to first position)
   * - Logic: policy_message parameter
     - ❌
     - ✅ (new parameter)
   * - Access: job_state.get_routine_state()
     - ✅
     - ❌ Use worker_state.get_routine_state()
   * - Access: job_state.set_routine_state()
     - ✅
     - ❌ Use worker_state.update_routine_state()
   * - Access: job_state.job_data
     - ✅
     - ❌ Use JobContext via get_current_job()
   * - Access: job_state.shared_data
     - ✅
     - ❌ Use JobContext.data
   * - Execute: JobManager()
     - ✅
     - ❌ Use Runtime()
   * - Execute: flow.post_job()
     - ✅
     - ❌ Use runtime.post()
   * - Execute: manager.execute_flow()
     - ✅
     - ❌ Use runtime.exec()
   * - Register: FlowRegistry.register_by_name()
     - ❌
     - ✅ Required
   * - Routine: set_activation_policy()
     - ❌
     - ✅ Required

---

Common Migration Issues and Solutions
-------------------------------------

**Issue 1: "Flow not found" Error**

.. code-block:: python

   # Error: ValueError: Flow not found: my_flow

   # Cause: Flow not registered with FlowRegistry
   # Solution:
   from routilux.monitoring.flow_registry import FlowRegistry
   FlowRegistry.get_instance().register_by_name("my_flow", flow)

**Issue 2: Routine Never Executes**

.. code-block:: python

   # Symptom: Routine added but logic never runs

   # Cause: No activation policy set
   # Solution:
   from routilux.activation_policies import immediate_policy
   routine.set_activation_policy(immediate_policy())

**Issue 3: "get_current_job() returns None"**

.. code-block:: python

   # Symptom: get_current_job() returns None

   # Cause: Called outside of job context
   # Solution: Always check for None
   from routilux.core import get_current_job

   job = get_current_job()
   if job:
       user_id = job.metadata.get("user_id")
   else:
       user_id = "system"

**Issue 4: State Not Persisting**

.. code-block:: python

   # Symptom: WorkerState changes lost between executions

   # Cause: Using JobContext instead of WorkerState for persistent data
   # Solution: Use WorkerState for persistent, JobContext for temporary

   # Wrong (for persistent data):
   job.set_data("cache", expensive_computation())

   # Right (for persistent data):
   state = worker_state.get_routine_state("cache") or {}
   state["data"] = expensive_computation()
   worker_state.update_routine_state("cache", state)

---

Testing Your Migration
---------------------

After migrating, verify:

1. **Flow registration**: Flows registered with ``FlowRegistry``
2. **Activation policies**: All routines have policies set
3. **State access**: ``worker_state`` instead of ``job_state``
4. **Job data**: Using ``JobContext`` via ``get_current_job()``
5. **Execution**: Using ``Runtime`` instead of ``JobManager``

**Verification Script**:

.. code-block:: python

   # test_migration.py
   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   from routilux.core import get_current_job

   # Test routine
   class TestRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def test_logic(slot_data, policy_message, worker_state):
               # Test WorkerState
               state = worker_state.get_routine_state("test") or {}
               state["tested"] = True
               worker_state.update_routine_state("test", state)

               # Test JobContext
               job = get_current_job()
               if job:
                   job.set_data("success", True)

               self.emit("output", result="ok")

           self.set_logic(test_logic)
           self.set_activation_policy(immediate_policy())

   # Create and register flow
   flow = Flow("test_flow")
   flow.add_routine(TestRoutine(), "test")
   FlowRegistry.get_instance().register_by_name("test_flow", flow)

   # Execute
   with Runtime() as runtime:
       runtime.exec("test_flow")
       runtime.post("test_flow", "test", "input", {})
       runtime.wait_until_all_jobs_finished(timeout=5.0)

   print("Migration test passed!")

Next Steps
----------

After completing migration:

1. Review :doc:`../tutorial/basics/understanding_routines` for v2 patterns
2. Read :doc:`../pitfalls/index` to avoid common v2 mistakes
3. Check :doc:`../user_guide/state_management` for state management best practices
4. Run tests: ``make test`` and ``make test-userstory``

.. seealso::

   :doc:`../tutorial/index`
      Progressive tutorials for v2 architecture

   :doc:`../api_reference/index`
      Complete v2 API reference
