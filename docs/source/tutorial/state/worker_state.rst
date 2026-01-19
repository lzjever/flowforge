WorkerState: Persistent Worker-Level State
==========================================

WorkerState is the mechanism for maintaining state across routine executions
within a worker. It's persistent, long-running state that survives multiple
job executions.

.. note:: **What You'll Learn**

   - What WorkerState is and when to use it
   - WorkerState lifecycle and scope
   - Storing and retrieving routine-specific state
   - Thread-safety considerations
   - Common WorkerState patterns

.. note:: **Prerequisites**

   - :doc:`../basics/understanding_routines` - Understand Routines first

Understanding WorkerState
-------------------------

**WorkerState** is a long-running state container associated with a worker
(execution instance). It persists across multiple job executions and is
ideal for:

- **Caching** data that's expensive to compute
- **Counters** and statistics
- **Connection pooling** (database, network)
- **Configuration** that changes over time
- **Learning/Adaptation** from previous executions

.. code-block:: text

   Worker Lifecycle (Long-Running)
   │
   │  ┌────────────────────────────────────────────────────┐
   │  │ WorkerState (Persistent)                           │
   │  │                                                    │
   │  │  routine_states: {                                │
   │  │    "routine1": {count: 100, last_item: "abc"},    │
   │  │    "routine2": {cache: {...}, connections: {...}}  │
   │  │  }                                                │
   │  └────────────────────────────────────────────────────┘
   │
   │  Job 1 ─▶ [Read State] ─▶ Process ─▶ [Update State]
   │  Job 2 ─▶ [Read State] ─▶ Process ─▶ [Update State]
   │  Job 3 ─▶ [Read State] ─▶ Process ─▶ [Update State]
   │  ...
   │
   ▼

**WorkerState Characteristics**:

- **Scope**: Per-worker (not per-job)
- **Lifetime**: As long as the worker is running
- **Visibility**: Accessible to all routines in the worker
- **Thread-safe**: Protected by locks for concurrent access

WorkerState vs JobContext
--------------------------

It's critical to understand the difference:

.. list-table::
   :widths: 25 25 25 25
   :header-rows: 1

   * - Aspect
     - WorkerState
     - JobContext
     - Example
   * - **Scope**
     - Worker-level
     - Job-level
     -
   * - **Lifetime**
     - Long-running (hours/days)
     - Short-lived (seconds/minutes)
     -
   * - **Use for**
     - Cached data, counters
     - Request-specific data
     -
   * - **Analogy**
     - Server process
     - HTTP request
     -

.. code-block:: text

   WorkerState (Server Process)          JobContext (HTTP Request)
   ┌──────────────────────────────┐     ┌──────────────────────────┐
   │ • Database connections        │     │ • Request ID              │
   │ • User session cache          │     │ • User ID for this request│
   │ • Total requests processed    │     │ • Request parameters      │
   │ • Learned model parameters    │     │ • Temporary calculations  │
   └──────────────────────────────┘     └──────────────────────────┘
            │                                       │
            └──────────────┬────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │   Routine   │
                    │   Logic     │
                    └─────────────┘

Accessing WorkerState in Routines
----------------------------------

WorkerState is automatically passed to your logic function:

.. code-block:: python

   from routilux import Routine
   from routilux.activation_policies import immediate_policy

   class CounterRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output", ["count"])

           def count_logic(slot_data, policy_message, worker_state):
               # worker_state is automatically provided!

               # Read current count
               state = worker_state.get_routine_state("counter") or {}
               count = state.get("count", 0)

               # Increment
               count += 1

               # Update state
               worker_state.update_routine_state("counter", {"count": count})

               # Emit result
               self.emit("output", count=count)
               print(f"Count: {count}")

           self.set_logic(count_logic)
           self.set_activation_policy(immediate_policy())

.. tip:: **Routine-Specific State**

   Use ``worker_state.get_routine_state(routine_id)`` to get state specific
   to your routine. This prevents state pollution between routines.

WorkerState API Reference
-------------------------

**Reading State**:

.. code-block:: python

   # Get all routine states
   all_states = worker_state.routine_states

   # Get specific routine state
   state = worker_state.get_routine_state("my_routine_id")
   # Returns: {"key": "value"} or None

   # Get nested value with default
   state = worker_state.get_routine_state("my_routine_id") or {}
   value = state.get("key", "default")

**Writing State**:

.. code-block:: python

   # Update entire routine state
   worker_state.update_routine_state("my_routine_id", {
       "count": 100,
       "last_processed": "item_123",
       "cache": {...}
   })

   # Partial update (merges with existing)
   existing = worker_state.get_routine_state("my_id") or {}
   existing["new_key"] = "new_value"
   worker_state.update_routine_state("my_id", existing)

**Utility Methods**:

.. code-block:: python

   # Get worker ID
   worker_id = worker_state.worker_id

   # Get flow ID
   flow_id = worker_state.flow_id

   # Get status
   status = worker_state.status  # "starting", "running", "stopped"

Complete Example: Caching Pattern
----------------------------------

Here's a practical example using WorkerState for caching:

.. code-block:: python
   :linenos:
   :name: state_worker_cache

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   import time
   import hashlib

   class ExpensiveDataProcessor(Routine):
       """Processes data with caching to avoid expensive recomputation."""

       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output", ["result", "cached"])
           self.add_slot("clear_cache")  # Optional cache clearing

           def process(slot_data, policy_message, worker_state):
               # Get routine state
               state = worker_state.get_routine_state("processor") or {}
               cache = state.get("cache", {})
               stats = state.get("stats", {"hits": 0, "misses": 0})

               # Check if input is for processing or cache clearing
               input_list = slot_data.get("input", [])
               clear_list = slot_data.get("clear_cache", [])

               if clear_list:
                   # Clear cache
                   print("Cache cleared!")
                   worker_state.update_routine_state("processor", {
                       "cache": {},
                       "stats": {"hits": 0, "misses": 0}
                   })
                   return

               if not input_list:
                   return

               item = input_list[0]
               data = item.get("data", "")

               # Generate cache key
               cache_key = hashlib.md5(data.encode()).hexdigest()

               # Check cache
               if cache_key in cache:
                   # Cache hit!
                   result = cache[cache_key]
                   stats["hits"] += 1
                   print(f"CACHE HIT! Reusing cached result (hits: {stats['hits']})")
                   self.emit("output", result=result, cached=True)
               else:
                   # Cache miss - do expensive processing
                   print("Cache miss - processing...")
                   time.sleep(1.0)  # Simulate expensive operation
                   result = f"processed_{data.upper()}"

                   # Store in cache
                   cache[cache_key] = result
                   stats["misses"] += 1

                   # Update state
                   worker_state.update_routine_state("processor", {
                       "cache": cache,
                       "stats": stats
                   })

                   print(f"Processed and cached (misses: {stats['misses']})")
                   self.emit("output", result=result, cached=False)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Build flow
   flow = Flow("cached_processor")

   flow.add_routine(ExpensiveDataProcessor(), "processor")

   FlowRegistry.get_instance().register_by_name("cached_processor", flow)

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("cached_processor")

       # Same data multiple times
       test_data = ["hello", "world", "hello", "test", "hello", "world"]

       for data in test_data:
           print(f"\nSending: {data}")
           runtime.post("cached_processor", "processor", "input", {"data": data})
           time.sleep(0.1)

       runtime.wait_until_all_jobs_finished(timeout=10.0)

**Expected Output**:

.. code-block:: text

   Sending: hello
   Cache miss - processing...
   Processed and cached (misses: 1)

   Sending: world
   Cache miss - processing...
   Processed and cached (misses: 2)

   Sending: hello
   CACHE HIT! Reusing cached result (hits: 1)

   Sending: test
   Cache miss - processing...
   Processed and cached (misses: 3)

   Sending: hello
   CACHE HIT! Reusing cached result (hits: 2)

   Sending: world
   CACHE HIT! Reusing cached result (hits: 2)

Counter Pattern
---------------

WorkerState is perfect for counting:

.. code-block:: python
   :linenos:

   class RequestCounter(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("request")
           self.add_event("response", ["request_id", "count"])

           def count_logic(slot_data, policy_message, worker_state):
               # Get or initialize counter
               state = worker_state.get_routine_state("counter") or {}
               total = state.get("total_requests", 0)
               by_type = state.get("by_type", {})

               # Process request
               requests = slot_data.get("request", [])
               if requests:
                   req = requests[0]
                   req_id = req.get("request_id", "unknown")
                   req_type = req.get("type", "unknown")

                   # Update counters
                   total += 1
                   by_type[req_type] = by_type.get(req_type, 0) + 1

                   # Save state
                   worker_state.update_routine_state("counter", {
                       "total_requests": total,
                       "by_type": by_type
                   })

                   print(f"Request {req_id} ({req_type}) - Total: {total}")
                   self.emit("response", request_id=req_id, count=total)

           self.set_logic(count_logic)
           self.set_activation_policy(immediate_policy())

Connection Pool Pattern
------------------------

WorkerState can store expensive resources like database connections:

.. code-block:: python
   :linenos:

   class DatabaseQueryRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("query")
           self.add_event("result", ["data"])

           def query_logic(slot_data, policy_message, worker_state):
               # Get or create connection pool
               state = worker_state.get_routine_state("db_accessor") or {}
               pool = state.get("connection_pool")

               if pool is None:
                   # Initialize connection pool (expensive!)
                   print("Initializing database connection pool...")
                   pool = self._create_connection_pool()
                   worker_state.update_routine_state("db_accessor", {
                       "connection_pool": pool
                   })

               # Use connection from pool
               queries = slot_data.get("query", [])
               if queries:
                   query = queries[0]
                   conn = pool.get_connection()
                   try:
                       result = conn.execute(query["sql"])
                       self.emit("result", data=result)
                   finally:
                       pool.return_connection(conn)

           def _create_connection_pool(self):
               # In real code, this would create actual connections
               return {
                   "connections": [],
                   "get_connection": lambda: {"id": "conn_1"},
                   "return_connection": lambda c: None
               }

           self.set_logic(query_logic)
           self.set_activation_policy(immediate_policy())

Thread-Safety Considerations
-----------------------------

WorkerState is thread-safe for concurrent access:

.. code-block:: python

   # Safe - Multiple routines can access concurrently
   def logic1(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("shared") or {}
       count = state.get("count", 0) + 1
       worker_state.update_routine_state("shared", {"count": count})

   def logic2(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("shared") or {}
       count = state.get("count", 0) + 1
       worker_state.update_routine_state("shared", {"count": count})

.. warning:: **Pitfall: Complex State Updates**

   For complex state updates, be careful of race conditions:

   .. code-block:: python

      # WRONG - Read-modify-write race condition
      def logic(slot_data, policy_message, worker_state):
          state = worker_state.get_routine_state("counter") or {}
          count = state.get("count", 0)  # Read
          # ... some processing ...
          worker_state.update_routine_state("counter", {"count": count + 1})  # Write
          # Problem: Another routine might update between read and write!

   **Solution**: Use atomic operations or redesign:

   .. code-block:: python

      # RIGHT - Use WorkerState's built-in atomic operations
      def logic(slot_data, policy_message, worker_state):
          # Or better, redesign to avoid shared mutable state
          state = worker_state.get_routine_state("counter") or {}
          count = state.get("count", 0) + 1
          worker_state.update_routine_state("counter", {"count": count})

Common WorkerState Patterns
---------------------------

**Pattern 1: Statistics Tracking**

.. code-block:: python

   def track_stats(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("stats") or {
           "processed": 0,
           "errors": 0,
           "last_processed": None
       }

       # Update stats
       state["processed"] += 1
       state["last_processed"] = time.time()

       worker_state.update_routine_state("stats", state)

**Pattern 2: Configuration Hot-Reload**

.. code-block:: python

   def load_config(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("config") or {}
       last_check = state.get("last_check", 0)
       config = state.get("current", {})

       # Reload config every 60 seconds
       if time.time() - last_check > 60:
           config = fetch_config_from_server()
           state["current"] = config
           state["last_check"] = time.time()
           worker_state.update_routine_state("config", state)

       return config

**Pattern 3: Learned Behavior**

.. code-block:: python

   def adaptive_threshold(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("adaptive") or {
           "threshold": 0.5,
           "adjustments": 0
       }

       # Adapt threshold based on results
       if too_many_false_positives():
           state["threshold"] += 0.05
           state["adjustments"] += 1
       elif too_many_false_negatives():
           state["threshold"] -= 0.05
           state["adjustments"] += 1

       worker_state.update_routine_state("adaptive", state)
       return state["threshold"]

Pitfalls Reference
------------------

.. list-table:: WorkerState Pitfalls
   :widths: 50 50
   :header-rows: 1

   * - Pitfall
     - Solution
   * - Using WorkerState for job-specific data
     - Use JobContext instead
   * - Not initializing state
     - Always use ``or {}`` default
   * - Race conditions on complex updates
     - Keep updates simple or use locks
   * - Memory leaks from unbounded growth
     - Implement cache limits/cleanup
   * - Storing non-serializable objects
     - Only store JSON-serializable data

Next Steps
----------

- :doc:`job_context` - Job-level temporary state
- :doc:`state_isolation` - Understanding state boundaries
- :doc:`../basics/understanding_runtime` - Runtime and worker lifecycle

.. seealso::

   :doc:`../../api_reference/core/worker`
      WorkerState API reference

   :doc:`../../pitfalls/state_management`
      Common state management pitfalls
