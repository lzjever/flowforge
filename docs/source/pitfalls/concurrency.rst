Concurrency Pitfalls
====================

Routilux executes routines concurrently using thread pools. This introduces
concurrency-related pitfalls that can cause race conditions, deadlocks, and
performance issues.

.. note:: **Overview**

   | Pitfall | Severity | Frequency |
   |---------|----------|-----------|
   | Shared Mutable State | 🔴 Critical | High |
   | Blocking Thread Pool | 🟡 High | High |
   | Deadlocks | 🔴 Critical | Medium |
   | Thread Pool Exhaustion | 🔴 Critical | Medium |
   | Incorrect Barrier Usage | 🟢 Medium | Low |

---

Pitfall 1: Shared Mutable State
--------------------------------

**The Pitfall**

Multiple routines modifying shared state without synchronization:

.. code-block:: python

   # WRONG - Race condition
   class Counter(Routine):
       def __init__(self):
           super().__init__()
           self.counter = 0  # Shared mutable instance variable!

       def increment(self, slot_data, policy_message, worker_state):
           self.counter += 1  # Not atomic!
           print(f"Count: {self.counter}")

**Why It Happens**

Python's GIL doesn't protect against race conditions in all cases. Multiple
threads can read-modify-write the same variable concurrently.

**Symptoms**

- Lost updates (counter doesn't reflect all operations)
- Inconsistent data under load
- Counts lower than expected
- Data corruption

**Solution**

Use WorkerState's thread-safe operations or JobContext:

.. code-block:: python

   # RIGHT - Use JobContext for per-job state
   from routilux.core import get_current_job

   def increment(slot_data, policy_message, worker_state):
       job = get_current_job()
       count = job.get_data("count", 0) + 1
       job.set_data("count", count)

   # RIGHT - Document approximate WorkerState counters
   def increment_approx(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("counter") or {}
       count = state.get("count", 0) + 1
       # Note: May miss some increments under high concurrency
       worker_state.update_routine_state("counter", {"count": count})

**Prevention**

- ✅ Use JobContext for precise per-job state
- ✅ Accept approximate counts for WorkerState
- ✅ Use locks for critical sections (with care)
- ❌ Never modify instance variables in logic

---

Pitfall 2: Blocking the Thread Pool
------------------------------------

**The Pitfall**

Long-running operations that block threads:

.. code-block:: python

   # WRONG - Blocking call in thread pool
   def process(slot_data, policy_message, worker_state):
       import time
       time.sleep(10)  # Blocks thread for 10 seconds!
       self.emit("output", result="done")

**Why It Happens**

Blocking operations (sleep, I/O, network calls) tie up threads, preventing
other jobs from executing.

**Symptoms**

- Poor performance under load
- Jobs queue up but don't execute
- Thread pool appears "stuck"
- Timeout errors

**Solution**

Use async operations or increase thread pool:

.. code-block:: python

   # RIGHT - Increase thread pool for blocking operations
   runtime = Runtime(thread_pool_size=100)  # More threads

   # RIGHT - Use async/await patterns
   async def async_operation():
       await asyncio.sleep(10)

   def process(slot_data, policy_message, worker_state):
       loop = asyncio.new_event_loop()
       result = loop.run_until_complete(async_operation())

**Prevention**

- ✅ Use async libraries for I/O
- ✅ Increase thread pool for blocking operations
- ✅ Consider separate process pool for CPU-bound work
- ❌ Avoid blocking calls in thread pool logic

---

Pitfall 3: Deadlocks
--------------------

**The Pitfall**

Circular wait conditions causing deadlocks:

.. code-block:: python

   # WRONG - Potential deadlock
   def logic_a(slot_data, policy_message, worker_state):
       with lock_a:
           with lock_b:
               process()

   def logic_b(slot_data, policy_message, worker_state):
       with lock_b:
           with lock_a:  # Deadlock if logic_a has lock_a!
               process()

**Why It Happens**

Two routines wait for each other's locks indefinitely.

**Symptoms**

- Jobs hang indefinitely
- No error messages
- Thread pool shows threads as "running" but not progressing
- Only occurs under specific timing conditions

**Solution**

Use consistent lock ordering:

.. code-block:: python

   # RIGHT - Always acquire locks in same order
   def logic_a(slot_data, policy_message, worker_state):
       with lock_a:  # Always lock_a first
           with lock_b:
               process()

   def logic_b(slot_data, policy_message, worker_state):
       with lock_a:  # Always lock_a first
           with lock_b:
               process()

**Prevention**

- ✅ Always acquire locks in consistent order
- ✅ Use timeout locks when possible
- ✅ Minimize lock scope
- ✅ Consider lock-free data structures

---

Pitfall 4: Thread Pool Exhaustion
----------------------------------

**The Pitfall**

Too many concurrent jobs exhausting the thread pool:

.. code-block:: python

   # WRONG - Submitting more jobs than thread pool can handle
   runtime = Runtime(thread_pool_size=4)

   # Submit 1000 jobs - only 4 can run at once!
   for i in range(1000):
       runtime.post("flow", "routine", "slot", {"data": i})

**Why It Happens**

Thread pool has fixed size. Exceeding it causes queue buildup.

**Symptoms**

- Jobs take forever to complete
- Memory usage grows (queued jobs)
- Timeout errors
- Poor throughput

**Solution**

Match submission rate to thread pool capacity:

.. code-block:: python

   # RIGHT - Use semaphore or rate limiting
   from threading import Semaphore

   semaphore = Semaphore(thread_pool_size)

   def submit_job(data):
       with semaphore:
           runtime.post("flow", "routine", "slot", data)

   # RIGHT - Increase thread pool for expected load
   runtime = Runtime(thread_pool_size=100)

**Prevention**

- ✅ Size thread pool for expected load
- ✅ Use rate limiting on job submission
- ✅ Monitor queue depths
- ✅ Consider backpressure mechanisms

---

Quick Reference: Thread Pool Sizing
------------------------------------

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Workload Type
     - Thread Pool Size
   * - CPU-bound (computation)
     - ``os.cpu_count()``
   * - I/O-bound (network, disk)
     - ``2-4x os.cpu_count()``
   * - Mixed
     - Start with ``os.cpu_count()`` and tune
   * - Blocking operations
     - Larger pools (50-100)

**Formula**:

.. code-block:: python

   import os

   # CPU-bound: One thread per core
   cpu_bound_size = os.cpu_count()

   # I/O-bound: Multiple threads per core
   io_bound_size = os.cpu_count() * 4

   # Conservative default
   default_size = max(4, os.cpu_count())

Next Steps
----------

- :doc:`state_management` - State management pitfalls
- :doc:`../tutorial/concurrency/thread_pools` - Thread pool guide
- :doc:`../user_guide/runtime` - Runtime configuration

.. seealso::

   :doc:`../api_reference/core/runtime`
      Runtime API reference
