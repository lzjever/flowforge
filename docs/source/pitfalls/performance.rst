Performance Pitfalls
====================

This section covers common performance mistakes that can make your Routilux
workflows slow, inefficient, or resource-intensive.

.. note:: **Overview**

   | Pitfall | Severity | Frequency |
   |---------|----------|-----------|
   | Over-Engineering | 🟡 High | High |
   | Excessive Slot Queues | 🟢 Medium | Medium |
   | Small Batch Sizes | 🟢 Medium | Low |
   | Synchronous Chaining | 🟡 High | Medium |
   | Memory Bloat | 🟡 High | Medium |

---

Pitfall 1: Over-Engineering Workflows
--------------------------------------

**The Pitfall**

Creating overly complex flows for simple tasks:

.. code-block:: python

   # WRONG - Over-engineered for a simple task
   flow = Flow("simple_counter")

   flow.add_routine(InputParser(), "parser")
   flow.add_routine(Validator(), "validator")
   flow.add_routine(Normalizer(), "normalizer")
   flow.add_routine(Transformer(), "transformer")
   flow.add_routine(Aggregator(), "aggregator")
   flow.add_routine(Formatter(), "formatter")
   flow.add_routine(Outputter(), "output")

   # All this just to count!

**Why It Happens**

Developers apply enterprise patterns to simple problems, adding unnecessary
complexity.

**Symptoms**

- Slow execution (overhead from many routines)
- Hard to debug (complex interactions)
- Resource waste (many workers)
- Maintenance burden

**Solution**

Match complexity to requirements:

.. code-block:: python

   # RIGHT - Simple solution for simple problem
   class SimpleCounter(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def count(slot_data, policy_message, worker_state):
               state = worker_state.get_routine_state("counter") or {}
               count = state.get("count", 0) + len(slot_data.get("input", []))
               worker_state.update_routine_state("counter", {"count": count})
               self.emit("output", count=count)

           self.set_logic(count)
           self.set_activation_policy(immediate_policy())

   flow = Flow("counter")
   flow.add_routine(SimpleCounter(), "counter")

**Prevention**

- ✅ Start simple, add complexity only when needed
- ✅ One routine per logical operation
- ✅ Combine related operations
- ✅ Profile before optimizing

---

Pitfall 2: Excessive Slot Queue Sizes
--------------------------------------

**The Pitfall**

Setting slot queue sizes too large:

.. code-block:: python

   # WRONG - Unnecessarily large queue
   self.add_slot("input", max_queue_length=1000000)

**Why It Happens**

Developers want to "be safe" and set huge queues, not realizing the memory
impact.

**Symptoms**

- High memory usage
- Slow startup (allocating large queues)
- Memory pressure on system
- Poor cache performance

**Solution**

Size queues appropriately:

.. code-block:: python

   # RIGHT - Size based on expected load
   # Calculate: expected_items_per_second * max_processing_delay
   max_queue = 100 * 5  # 100 items/sec * 5 sec max delay
   self.add_slot("input", max_queue_length=max_queue)

**Prevention**

- ✅ Calculate based on expected throughput
- ✅ Use watermark for auto-shrink
- ✅ Monitor queue depths
- ✅ Default (1000) is usually fine

---

Pitfall 3: Small Batch Sizes
-----------------------------

**The Pitfall**

Processing items one at a time instead of batching:

.. code-block:: python

   # WRONG - Processing one item at a time
   self.set_activation_policy(immediate_policy())  # Activates on every item

**Why It Happens**

Using immediate policy for high-volume data, causing excessive activations.

**Symptoms**

- High CPU usage (context switching)
- Slow throughput
- Thread pool exhaustion
- Poor throughput

**Solution**

Use batch processing:

.. code-block:: python

   # RIGHT - Batch processing
   from routilux.activation_policies import batch_size_policy

   # Process 100 items at a time
   self.set_activation_policy(batch_size_policy(100))

   def process_batch(slot_data, policy_message, worker_state):
       items = slot_data.get("input", [])
       # Process all 100 items efficiently
       for item in items:
           process_item(item)

**Prevention**

- ✅ Use batch_size_policy for high-volume data
- ✅ Typical batch sizes: 10-1000 items
- ✅ Tune based on profiling
- ✅ Balance latency vs throughput

---

Pitfall 4: Synchronous Chaining
--------------------------------

**The Pitfall**

Creating long chains where each step must complete before the next starts:

.. code-block:: text

   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐   ┌─────┐
   │Step1│──▶│Step2│──▶│Step3│──▶│Step4│──▶│Step5│
   └─────┘   └─────┘   └─────┘   └─────┘   └─────┘

   Total time = sum(all step times)

**Why It Happens**

Linear processing is intuitive but slow for independent operations.

**Symptoms**

- Slow overall processing
- Poor resource utilization
- One slow step blocks everything

**Solution**

Parallelize independent operations:

.. code-block:: text

   ┌─────────────────┐
   │     Input       │
   └────┬────┬───────┘
        │    │
   ┌────▼─┐ ┌▼─────┐
   │Step1a│ │Step1b│  # Parallel
   └────┬─┘ └──┬───┘
        │      │
        └───┬──┘
            ▼
        ┌─────┐
        │Step2│     # Sequential after parallel
        └─────┘

**Prevention**

- ✅ Parallelize independent operations
- ✅ Use fan-out patterns
- ✅ Only sequence dependent operations
- ✅ Profile to find bottlenecks

---

Pitfall 5: Memory Bloat
-----------------------

**The Pitfall**

Accumulating data in memory without cleanup:

.. code-block:: python

   # WRONG - Accumulating results
   class Collector(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")

           def collect(slot_data, policy_message, worker_state):
               state = worker_state.get_routine_state("collector") or {}
               results = state.get("all_results", [])

               # Keeps growing!
               new_items = slot_data.get("items", [])
               results.extend(new_items)

               worker_state.update_routine_state("collector", {
                   "all_results": results
               })

**Why It Happens**

Collecting all results for later processing without considering memory limits.

**Symptoms**

- Memory usage grows continuously
- ``MemoryError`` after extended runtime
- Slow performance (garbage collection pressure)
- OOM kills

**Solution**

Implement bounds and cleanup:

.. code-block:: python

   # RIGHT - Bounded collection
   class BoundedCollector(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")

           def collect(slot_data, policy_message, worker_state):
               state = worker_state.get_routine_state("collector") or {}
               results = state.get("recent_results", [])
               new_items = slot_data.get("items", [])

               # Keep only last 1000
               results = (results + new_items)[-1000:]

               worker_state.update_routine_state("collector", {
                   "recent_results": results
               })

   # RIGHT - Stream processing instead of accumulating
   class StreamProcessor(Routine):
       def process_and_discard(slot_data, policy_message, worker_state):
           items = slot_data.get("items", [])
           for item in items:
               result = process(item)
               write_to_disk(result)  # Don't keep in memory!

**Prevention**

- ✅ Set maximum sizes for collections
- ✅ Stream/process and discard
- ✅ Implement periodic cleanup
- ✅ Monitor memory usage

---

Performance Checklist
---------------------

Before deploying to production, verify:

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Check
     - Status
   * - Flow complexity matches requirements
     - ☐
   * - Slot queues sized appropriately
     - ☐
   * - Using batches for high-volume data
     - ☐
   * - Parallelized independent operations
     - ☐
   * - Memory usage is bounded
     - ☐
   * - Profiled and optimized hot paths
     - ☐

Next Steps
----------

- :doc:`../user_guide/analysis` - Performance analysis
- :doc:`../tutorial/activation/batch_size` - Batch processing
- :doc:`../cookbook/data_processing_pipeline` - Efficient patterns

.. seealso::

   :doc:`../api_reference/core/slot`
      Slot API reference
