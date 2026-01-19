State Management Pitfalls
=========================

State management is one of the most confusing aspects of Routilux. This section
covers common mistakes with WorkerState, JobContext, and routine state.

.. note:: **Overview**

   | Pitfall | Severity | Frequency |
   |---------|----------|-----------|
   | Using JobState (deprecated) | 🔴 Critical | High |
   | WorkerState vs JobContext Confusion | 🟡 High | Very High |
   | Non-Serializable State | 🔴 Critical | Medium |
   | Memory Leaks in State | 🟡 High | Medium |
   | Race Conditions | 🔴 Critical | High |
   | State Pollution | 🟢 Medium | Low |

---

Pitfall 1: Using Deprecated JobState
-------------------------------------

**The Pitfall**

Using the old ``JobState`` API that no longer exists:

.. code-block:: python
   :emphasize-lines: 7

   # WRONG - JobState doesn't exist in v2!
   from routilux.core import JobState  # ImportError!

   # Also wrong:
   job_state.set_routine_state(...)  # AttributeError!
   job_state.get_routine_state(...)  # Doesn't exist!

**Why It Happens**

Old documentation or tutorials reference the deprecated JobState API.
The v2 architecture replaced JobState with:
- ``JobContext`` for per-job state
- ``WorkerState`` for worker-level state

**Symptoms**

- ``ImportError`` or ``AttributeError``
- Code examples don't work
- Confusion about which state API to use

**Solution**

Use the correct v2 APIs:

.. code-block:: python

   # RIGHT - Use WorkerState for persistent state
   def logic(slot_data, policy_message, worker_state):
       # WorkerState is passed to logic function
       state = worker_state.get_routine_state("my_routine") or {}
       worker_state.update_routine_state("my_routine", {"key": "value"})

   # RIGHT - Use JobContext for job-specific state
   from routilux.core import get_current_job

   def logic(slot_data, policy_message, worker_state):
       job = get_current_job()
       if job:
           job.set_data("key", "value")
           value = job.get_data("key")

**Prevention**

- ✅ Use ``WorkerState`` for persistent, worker-level state
- ✅ Use ``JobContext`` for temporary, job-level state
- ❌ Never reference ``JobState`` (removed in v2)

**Related**

- :doc:`../tutorial/state/worker_state` - WorkerState guide
- :doc:`../tutorial/state/job_context` - JobContext guide

---

Pitfall 2: Confusing WorkerState and JobContext
-----------------------------------------------

**The Pitfall**

Using WorkerState for job-specific data or vice versa:

.. code-block:: python
   :emphasize-lines: 4

   # WRONG - Using WorkerState for request-specific data
   def process_user_request(slot_data, policy_message, worker_state):
       job = get_current_job()
       user_id = job.metadata.get("user_id")

       # Storing request-specific data in WorkerState
       worker_state.update_routine_state("processor", {
           "current_user": user_id  # Wrong! Gets mixed with other requests
       })

**Why It Happens**

The distinction between worker-level (long-running) and job-level (temporary)
state is subtle. It's easy to confuse when to use which.

**Symptoms**

- Data from different requests getting mixed
- User A seeing User B's data
- Inexplicable data corruption
- Test failures under concurrent load

**Solution**

Match state type to lifetime:

.. code-block:: python

   # RIGHT - Job-specific data goes in JobContext
   def process_user_request(slot_data, policy_message, worker_state):
       job = get_current_job()
       user_id = job.metadata.get("user_id")

       # Store in JobContext (isolated per job)
       job.set_data("current_user", user_id)
       job.set_data("request_start", time.time())

       # RIGHT - Shared cache goes in WorkerState
       state = worker_state.get_routine_state("cache") or {}
       if "user_profiles" not in state:
           state["user_profiles"] = {}  # Shared across requests
       worker_state.update_routine_state("cache", state)

**Decision Tree**:

.. code-block:: text

   Need to store data?
        │
        ├─ Is it specific to THIS request/job?
        │     └─▶ Use JobContext
        │
        ├─ Should it persist across jobs?
        │     └─▶ Use WorkerState
        │
        └─ Should other jobs access it?
              ├─ Yes ─▶ WorkerState (shared key)
              └─ No ─▶ JobContext

**Prevention**

- ✅ Ask: "Should this data survive after the job completes?"
- ✅ If yes → WorkerState, if no → JobContext
- ✅ Use JobContext for: request IDs, user IDs, trace data
- ✅ Use WorkerState for: caches, counters, connection pools

**Related**

- :doc:`../tutorial/state/state_isolation` - State isolation boundaries
- :doc:`../user_guide/state_management` - State management guide

---

Pitfall 3: Non-Serializable State
----------------------------------

**The Pitfall**

Storing non-serializable objects in state:

.. code-block:: python
   :emphasize-lines: 5

   # WRONG - Storing non-serializable objects
   def init_logic(slot_data, policy_message, worker_state):
       import sqlite3
       conn = sqlite3.connect(":memory:")

       # Can't serialize connection object!
       worker_state.update_routine_state("db", {"connection": conn})

**Why It Happens**

Developers try to store expensive resources (connections, file handles, etc.)
in WorkerState. These objects aren't JSON-serializable.

**Symptoms**

- ``SerializationError`` or ``TypeError``
- State not persisting across restarts
- ``Object of type X is not JSON serializable``
- Failure when saving/restoring flow state

**Solution**

Store serializable data or use handles:

.. code-block:: python

   # RIGHT - Store connection string, not connection
   def init_logic(slot_data, policy_message, worker_state):
       # Store config, not object
       worker_state.update_routine_state("db", {
           "connection_string": "sqlite:///tmp/db.sqlite3"
       })

   def query_logic(slot_data, policy_message, worker_state):
       # Recreate connection from config
       state = worker_state.get_routine_state("db") or {}
       conn_str = state.get("connection_string")

       # Create connection when needed
       import sqlite3
       conn = sqlite3.connect(conn_str)
       try:
           result = conn.execute("SELECT ...")
           return result.fetchall()
       finally:
           conn.close()  # Always close

**Prevention**

- ✅ Only store JSON-serializable types: str, int, float, bool, list, dict, None
- ✅ Store connection strings, file paths, not objects
- ✅ Recreate resources from configuration when needed
- ❌ Never store: file handles, sockets, connections, locks, threads

**Related**

- :doc:`serialization` - Serialization pitfalls
- :doc:`../user_guide/serialization` - Serialization guide

---

Pitfall 4: Memory Leaks in State
---------------------------------

**The Pitfall**

Unbounded growth of state data:

.. code-block:: python
   :emphasize-lines: 7

   # WRONG - Unbounded cache growth
   def cache_logic(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("cache") or {}
       cache = state.get("data", {})

       # Never removes old entries!
       cache[new_key] = expensive_computation(new_key)

       worker_state.update_routine_state("cache", {"data": cache})

**Why It Happens**

Caches and collections grow without bounds. Over time, this causes memory
issues.

**Symptoms**

- Memory usage grows continuously
- ``MemoryError`` after extended runtime
- Slow performance due to large state
- OOM kills in containerized environments

**Solution**

Implement cache limits and cleanup:

.. code-block:: python

   # RIGHT - Bounded cache with LRU eviction
   from collections import OrderedDict

   def cache_logic(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("cache") or {}
       cache = state.get("data", OrderedDict())

       MAX_CACHE_SIZE = 1000

       # Add new entry
       cache[key] = value

       # Evict oldest if too large
       if len(cache) > MAX_CACHE_SIZE:
           cache.popitem(last=False)  # Remove oldest

       worker_state.update_routine_state("cache", {"data": cache})

   # RIGHT - Periodic cleanup
   def cleanup_logic(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("cache") or {}
       cache = state.get("data", {})

       # Remove entries older than 1 hour
       import time
       now = time.time()
       cache = {k: v for k, v in cache.items()
                if now - v.get("timestamp", 0) < 3600}

       worker_state.update_routine_state("cache", {"data": cache})

**Prevention**

- ✅ Always set maximum sizes for collections
- ✅ Implement TTL or LRU eviction
- ✅ Periodic cleanup of old data
- ✅ Monitor memory usage
- ❌ Never let caches grow unbounded

---

Pitfall 5: Race Conditions on Shared State
-------------------------------------------

**The Pitfall**

Concurrent access to shared WorkerState:

.. code-block:: python
   :emphasize-lines: 4

   # WRONG - Race condition
   def increment_counter(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("counter") or {}
       count = state.get("count", 0)  # Read

       # ... some processing ...

       state["count"] = count + 1  # Write
       worker_state.update_routine_state("counter", state)
       # Problem: Two jobs might read same value!

**Why It Happens**

Multiple jobs execute concurrently. Both read the same count value, both
increment to same result.

**Symptoms**

- Lost updates (count doesn't reflect all operations)
- Inconsistent data under load
- Tests pass in development, fail in production
- Counts lower than expected

**Solution**

Accept imprecision or use JobContext:

.. code-block:: python

   # RIGHT - Use JobContext for precise counting
   def increment_counter(slot_data, policy_message, worker_state):
       job = get_current_job()
       count = job.get_data("count", 0) + 1
       job.set_data("count", count)

   # OR - Accept imprecision for WorkerState counters
   # Note: Might miss some increments under high concurrency
   def approximate_counter(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("counter") or {}
       count = state.get("count", 0) + 1
       worker_state.update_routine_state("counter", {"count": count})
       # Document that this is approximate!

   # RIGHT - Use atomic operations if available
   from threading import Lock

   # In worker setup:
   state_lock = Lock()

   def increment_counter(slot_data, policy_message, worker_state):
       with state_lock:
           state = worker_state.get_routine_state("counter") or {}
           count = state.get("count", 0) + 1
           worker_state.update_routine_state("counter", {"count": count})

**Prevention**

- ✅ Use JobContext for precise, per-job counters
- ✅ Document that WorkerState counters are approximate
- ✅ Use locks for critical sections (adds overhead)
- ✅ Consider atomic counters from ``threading`` module
- ❌ Don't assume WorkerState updates are atomic

**Related**

- :doc:`concurrency` - Concurrency pitfalls
- :doc:`../tutorial/concurrency/thread_pools` - Thread pool guide

---

Pitfall 6: State Pollution
---------------------------

**The Pitfall**

Accidentally sharing state between unrelated routines:

.. code-block:: python
   :emphasize-lines: 5

   # WRONG - Using generic state keys
   class ProcessorA(Routine):
       def __init__(self):
           super().__init__()
           self.set_config(state_key="data")  # Too generic!

       def process(self, slot_data, policy_message, worker_state):
           worker_state.update_routine_state("data", {"value": 123})

   class ProcessorB(Routine):
       def __init__(self):
           super().__init__()
           # Oops, same key!

**Why It Happens**

Using generic state keys like ``data``, ``result``, ``cache`` causes collisions
between unrelated routines.

**Symptoms**

- Mysterious data in routine state
- Routines reading each other's data
- Inexplicable bugs that disappear when renaming

**Solution**

Use namespaced state keys:

.. code-block:: python

   # RIGHT - Namespace by routine
   class ProcessorA(Routine):
       def __init__(self):
           super().__init__()
           self.set_config(routine_id="processor_a")

       def process(self, slot_data, policy_message, worker_state):
           routine_id = self.get_config("routine_id")
           worker_state.update_routine_state(routine_id, {"value": 123})

   class ProcessorB(Routine):
       def __init__(self):
           super().__init__()
           self.set_config(routine_id="processor_b")

       def process(self, slot_data, policy_message, worker_state):
           routine_id = self.get_config("routine_id")
           worker_state.update_routine_state(routine_id, {"other": 456})

**Prevention**

- ✅ Use routine_id as state key
- ✅ Namespace shared state: ``_shared_cache``, ``_global_config``
- ✅ Use descriptive keys: ``user_cache`` not ``cache``
- ❌ Avoid generic keys: ``data``, ``result``, ``state``

---

Quick Reference: State Type Decision Tree
------------------------------------------

.. code-block:: text

   ┌─────────────────────────────────────────────────────────┐
   │ Need to store data?                                     │
   └────────────────────┬────────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
     Is it THIS job?             Share across jobs?
          │                           │
          ▼                           ▼
   ┌──────────────┐          ┌──────────────┐
   │ JobContext   │          │ WorkerState  │
   │              │          │              │
   │ • Request ID │          │ • Cache      │
   │ • User ID    │          │ • Counters   │
   │ • Trace log  │          │ • Connections│
   │ • Temporary  │          │ • Persistent │
   └──────────────┘          └──────────────┘
          │                           │
          ▼                           ▼
    Destroyed when            Persists until
    job completes             worker stops

Next Steps
----------

- :doc:`routine_design` - Routine design pitfalls
- :doc:`concurrency` - Concurrency pitfalls
- :doc:`../tutorial/state/state_isolation` - State isolation guide

.. seealso::

   :doc:`../api_reference/core/worker`
      WorkerState API reference

   :doc:`../api_reference/core/context`
      JobContext API reference
