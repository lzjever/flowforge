Troubleshooting Guide
=====================

This guide helps you diagnose and resolve common issues when working with
Routilux workflows.

.. note:: **Before You Start**

   - Check :doc:`../pitfalls/index` for common mistakes
   - Review :doc:`../migration_guide` if upgrading from v1
   - Ensure you're using the v2 architecture

Quick Diagnosis
---------------

**Problem: Routine not executing**

1. Check activation policy is set
2. Check data is being posted to the correct slot
3. Check flow is registered with FlowRegistry

**Problem: "Flow not found" error**

1. Check flow is registered: ``FlowRegistry.register_by_name()``
2. Check flow_id matches registration name

**Problem: State not persisting**

1. Check if using WorkerState (persistent) vs JobContext (temporary)
2. Check state key matches between get/set operations

**Problem: Thread pool exhausted**

1. Increase thread_pool_size in Runtime
2. Check for blocking operations in logic functions

---

Common Issues and Solutions
----------------------------

Issue: Routine Never Executes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- Routine added to flow but logic never runs
- No output from routine
- No errors logged

**Diagnosis**:

.. code-block:: python

   # Check 1: Is activation policy set?
   routine = flow.routines["my_routine"]
   policy_info = routine.get_activation_policy_info()
   print(f"Policy type: {policy_info['type']}")

   # Check 2: Is data arriving at slot?
   slot = routine.get_slot("my_slot")
   print(f"Unconsumed count: {slot.get_unconsumed_count()}")

**Solutions**:

1. **Missing activation policy**:

   .. code-block:: python

      # Add activation policy
      from routilux.activation_policies import immediate_policy

      routine.set_activation_policy(immediate_policy())

2. **Wrong slot name**:

   .. code-block:: python

      # Ensure slot names match
      runtime.post("flow", "routine", "correct_slot_name", {})

3. **Not posting data**:

   .. code-block:: python

      # Verify job posting
      worker_state, job_ctx = runtime.post(
          "flow", "routine", "slot", {"data": "value"}
      )

---

Issue: "Flow not found" Error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- ``ValueError: Flow not found: 'my_flow'``
- ``RuntimeError: Cannot execute unregistered flow``

**Diagnosis**:

.. code-block:: python

   # Check if flow is registered
   from routilux.monitoring.flow_registry import FlowRegistry

   registry = FlowRegistry.get_instance()
   print(f"Registered flows: {list(registry._flows.keys())}")

**Solutions**:

1. **Register flow before execution**:

   .. code-block:: python

      from routilux.monitoring.flow_registry import FlowRegistry

      # Register by name
      FlowRegistry.get_instance().register_by_name("my_flow", flow)

      # Then execute
      runtime.exec("my_flow")

2. **Check flow_id matches**:

   .. code-block:: python

      # flow_id must match registration name
      FlowRegistry.register_by_name("my_flow", flow)
      runtime.exec("my_flow")  # Same name!

---

Issue: Slot Queue Full Error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- ``SlotQueueFullError``
- Data being rejected
- Routines not receiving data

**Diagnosis**:

.. code-block:: python

   # Check slot queue size
   slot = routine.get_slot("my_slot")
   print(f"Unconsumed: {slot.get_unconsumed_count()}")
   print(f"Consumed: {slot.get_consumed_count()}")

**Solutions**:

1. **Increase queue size**:

   .. code-block:: python

      # Add slot with larger queue
      self.add_slot("data", max_queue_length=10000)

2. **Process faster**:

   - Increase thread pool size
   - Optimize logic function
   - Use batch processing

3. **Handle backpressure**:

   .. code-block:: python

      from routilux.core.slot import SlotQueueFullError

      try:
          runtime.post("flow", "routine", "slot", data)
      except SlotQueueFullError:
          # Retry with backoff
          import time
          time.sleep(0.1)
          runtime.post("flow", "routine", "slot", data)

---

Issue: State Not Persisting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- WorkerState changes lost between jobs
- Cache not working across executions
- Counters reset unexpectedly

**Diagnosis**:

.. code-block:: python

   # Check state type
   def debug_logic(slot_data, policy_message, worker_state):
       print(f"Worker ID: {worker_state.worker_id}")
       print(f"Routine states: {worker_state.routine_states}")

**Solutions**:

1. **Using JobContext for persistent data**:

   .. code-block:: python

      # WRONG - JobContext is temporary
      job = get_current_job()
      job.set_data("cache", expensive_data)

      # RIGHT - Use WorkerState for persistence
      state = worker_state.get_routine_state("cache") or {}
      state["data"] = expensive_data
      worker_state.update_routine_state("cache", state)

2. **State key mismatch**:

   .. code-block:: python

      # Ensure keys match
      worker_state.update_routine_state("my_id", {"key": "value"})
      state = worker_state.get_routine_state("my_id")

---

Issue: Race Conditions
~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- Lost updates under concurrent load
- Inconsistent data
- Counts lower than expected

**Diagnosis**:

.. code-block:: python

   # Check for concurrent access
   import threading

   def logic(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("counter") or {}
       count = state.get("count", 0)
       # Check if multiple threads access simultaneously
       print(f"Thread: {threading.current_thread().name}, Count: {count}")

**Solutions**:

1. **Use JobContext for precise counts**:

   .. code-block:: python

      from routilux.core import get_current_job

      def logic(slot_data, policy_message, worker_state):
          job = get_current_job()
          count = job.get_data("count", 0) + 1
          job.set_data("count", count)

2. **Accept approximate counts**:

   .. code-block:: python

      # Document that counts are approximate
      def logic(slot_data, policy_message, worker_state):
          state = worker_state.get_routine_state("counter") or {}
          count = state.get("count", 0) + 1
          worker_state.update_routine_state("counter", {"count": count})
          # Note: May miss some increments under high concurrency

3. **Use locks for critical sections**:

   .. code-block:: python

      from threading import Lock

      state_lock = Lock()

      def logic(slot_data, policy_message, worker_state):
          with state_lock:
              state = worker_state.get_routine_state("counter") or {}
              count = state.get("count", 0) + 1
              worker_state.update_routine_state("counter", {"count": count})

---

Issue: Memory Usage Growing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- Memory usage increases continuously
- ``MemoryError`` after extended runtime
- Slow performance

**Diagnosis**:

.. code-block:: python

   # Check state sizes
   import sys

   def debug_logic(slot_data, policy_message, worker_state):
       for routine_id, state in worker_state.routine_states.items():
           size = sys.getsizeof(state)
           print(f"{routine_id}: {size} bytes")

**Solutions**:

1. **Bounded collections**:

   .. code-block:: python

      MAX_CACHE_SIZE = 1000

      def logic(slot_data, policy_message, worker_state):
          state = worker_state.get_routine_state("cache") or {}
          cache = state.get("data", [])

          # Add new item
          cache.append(new_item)

          # Trim to max size
          if len(cache) > MAX_CACHE_SIZE:
              cache = cache[-MAX_CACHE_SIZE:]

          worker_state.update_routine_state("cache", {"data": cache})

2. **Periodic cleanup**:

   .. code-block:: python

      import time

      def cleanup_logic(slot_data, policy_message, worker_state):
          state = worker_state.get_routine_state("cache") or {}
          cache = state.get("data", {})

          # Remove entries older than 1 hour
          now = time.time()
          cache = {k: v for k, v in cache.items()
                   if now - v.get("timestamp", 0) < 3600}

          worker_state.update_routine_state("cache", {"data": cache})

---

Issue: Slow Performance
~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- Poor throughput
- High latency
- CPU usage high

**Diagnosis**:

.. code-block:: python

   # Profile execution time
   import time

   def timed_logic(slot_data, policy_message, worker_state):
       start = time.time()
       # ... processing ...
       duration = time.time() - start
       print(f"Logic took {duration:.3f} seconds")

**Solutions**:

1. **Use batch processing**:

   .. code-block:: python

      from routilux.activation_policies import batch_size_policy

      # Instead of immediate (one item per execution)
      routine.set_activation_policy(immediate_policy())

      # Use batch (100 items per execution)
      routine.set_activation_policy(batch_size_policy(100))

2. **Avoid blocking operations**:

   .. code-block:: python

      # WRONG - Blocking in thread pool
      import requests
      response = requests.get(url)  # Blocks thread!

      # RIGHT - Use async
      import aiohttp
      async with aiohttp.ClientSession() as session:
          async with session.get(url) as response:
              data = await response.text()

3. **Increase thread pool**:

   .. code-block:: python

      # For I/O bound workloads
      runtime = Runtime(thread_pool_size=50)

---

Issue: Serialization Errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Symptoms**:
- ``TypeError: Object of type X is not JSON serializable``
- ``PicklingError``
- State not persisting

**Diagnosis**:

.. code-block:: python

   # Check what's in state
   def debug_logic(slot_data, policy_message, worker_state):
       for routine_id, state in worker_state.routine_states.items():
           for key, value in state.items():
               try:
                   import json
                   json.dumps(value)
               except TypeError:
                   print(f"Non-serializable: {routine_id}.{key} = {type(value)}")

**Solutions**:

1. **Store configuration, not objects**:

   .. code-block:: python

      # WRONG - Storing connection
      self.connection = sqlite3.connect(":memory:")

      # RIGHT - Storing connection string
      self.set_config(connection_string="sqlite:///tmp/db")

2. **Use JSON-serializable types only**:

   .. code-block:: python

      # Serializable: str, int, float, bool, list, dict, None
      worker_state.update_routine_state("data", {
          "string": "value",
          "number": 42,
          "list": [1, 2, 3],
          "dict": {"nested": "value"},
          "none": None
      })

---

Debugging Tips
-------------

**Enable Tracing**:

.. code-block:: python

   from routilux.core import get_current_job

   def traced_logic(slot_data, policy_message, worker_state):
       job = get_current_job()
       if job:
           job.trace("routine_id", "logic_started", {
               "input": slot_data,
               "timestamp": time.time()
           })

       # ... logic ...

       if job:
           job.trace("routine_id", "logic_completed", {
               "output": result
           })

**Print Slot Data**:

.. code-block:: python

   def debug_logic(slot_data, policy_message, worker_state):
       print(f"Slot data: {slot_data}")
       print(f"Policy message: {policy_message}")
       print(f"Worker state: {worker_state.routine_states}")

**Use BreakpointManager**:

.. code-block:: python

   from routilux.monitoring.breakpoint_manager import BreakpointManager

   manager = BreakpointManager()

   # Set breakpoint on routine
   manager.set_breakpoint(flow_id="my_flow", routine_id="my_routine")

   # Execution will pause at breakpoint

---

Getting Help
------------

If you can't resolve your issue:

1. **Check documentation**:
   - :doc:`../pitfalls/index`
   - :doc:`../tutorial/index`
   - :doc:`../user_guide/index`

2. **Search GitHub Issues**:
   https://github.com/lzjever/routilux/issues

3. **Create minimal reproducible example**:
   - Simplify your flow to minimum code
   - Remove external dependencies
   - Include error messages and stack traces

4. **Report issue**:
   - Use GitHub issue template
   - Include Python version
   - Include Routilux version
   - Include minimal reproducible example

---

Prevention Checklist
--------------------

Before deploying, verify:

- [ ] All routines have activation policies
- [ ] Flows registered with FlowRegistry
- [ ] Using WorkerState for persistent data
- [ ] Using JobContext for temporary data
- [ ] Slot queues sized appropriately
- [ ] No blocking operations in logic
- [ ] Thread pool sized for workload
- [ ] Error handlers configured
- [ ] Tested under concurrent load
- [ ] Memory usage is bounded

.. seealso::

   :doc:`../pitfalls/index`
      Common pitfalls and how to avoid them

   :doc:`../api_reference/index`
      Complete API reference
