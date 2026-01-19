Batch Size Policy
=================

The ``batch_size_policy`` activates a routine when a specified number of items
have accumulated in its slot(s), enabling efficient batch processing.

.. note:: **What You'll Learn**

   - How batch_size_policy improves throughput
   - Configuring batch sizes
   - Handling batched data in logic functions
   - When to use batching vs immediate execution

.. note:: **Prerequisites**

   - :doc:`immediate_policy` - Understand immediate policy first
   - :doc:`../basics/understanding_slots_events` - Understand slots

How Batch Size Policy Works
-----------------------------

The batch policy activates when a slot reaches a specified threshold:

.. code-block:: text

   Items arrive in slot
       │
       ▼
   Check: slot.unconsumed_count >= batch_size?
       │
       ├─ No ──▶ Do nothing (continue accumulating)
       │
       └─ Yes ──▶ Consume batch_size items
                   │
                   ▼
              Execute logic(batch_data)
                   │
                   ▼
              Return consumed items

**Key Characteristics**:

- **Trigger**: Slot reaches specified count
- **Data scope**: Consumes exactly ``batch_size`` items (or all if fewer)
- **Execution**: Runs logic once per batch
- **Use case**: High-volume data, expensive operations

Basic Usage
-----------

.. code-block:: python
   :linenos:

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import batch_size_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   class BatchProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")
           self.add_event("processed", ["batch_size", "items"])

           def process(slot_data, policy_message, worker_state):
               items = slot_data.get("items", [])
               batch_size = len(items)

               print(f"Processing batch of {batch_size} items:")

               # Process all items in this batch
               results = []
               for item in items:
                   value = item.get("value", 0)
                   result = value * 2
                   results.append(result)
                   print(f"  Item {value} → {result}")

               # Emit batch summary
               self.emit("processed", batch_size=batch_size, items=results)

           self.set_logic(process)
           # Activate when 5 items are ready
           self.set_activation_policy(batch_size_policy(5))

   # Build flow
   flow = Flow("batch_demo")
   flow.add_routine(BatchProcessor(), "processor")
   FlowRegistry.get_instance().register_by_name("batch_demo", flow)

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("batch_demo")

       # Post 12 items - will execute in 3 batches
       for i in range(12):
           runtime.post("batch_demo", "processor", "items", {"value": i})

       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Processing batch of 5 items:
     Item 0 → 0
     Item 1 → 2
     Item 2 → 4
     Item 3 → 6
     Item 4 → 8
   Processing batch of 5 items:
     Item 5 → 10
     Item 6 → 12
     Item 7 → 14
     Item 8 → 16
     Item 9 → 18
   Processing batch of 2 items:
     Item 10 → 20
     Item 11 → 22

.. tip:: **Throughput Improvement**

   Batching amortizes overhead:

   - **Immediate**: 12 executions for 12 items
   - **Batch (5)**: 3 executions for 12 items

   For expensive operations (database writes, API calls), this is significantly
   more efficient.

Configuring Batch Size
----------------------

The batch size should match your use case:

.. list-table::
   :widths: 30 30 40
   :header-rows: 1

   * - Batch Size
     - Use Case
     - Example
   * - 5-20
     - Expensive operations (database writes, API calls)
     - ``batch_size_policy(10)``
   * - 50-100
     - Moderate operations (calculations, transformations)
     - ``batch_size_policy(100)``
   * - 500-1000
     - Fast operations (simple computations)
     - ``batch_size_policy(1000)``
   * - 1000+
     - Very fast operations (aggregations, filtering)
     - ``batch_size_policy(5000)``

**Dynamic Batch Size**:

.. code-block:: python

   # Set batch size dynamically based on configuration
   class ConfigurableBatch(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           # Configure batch size
           self.set_config(batch_size=50)

           def process(slot_data, policy_message, worker_state):
               batch_size = self.get_config("batch_size", 10)
               # ... process ...

           self.set_logic(process)
           # Use configured batch size
           self.set_activation_policy(batch_size_policy(lambda s, w: batch_size))

Multiple Slots with Batching
-----------------------------

With batch_size_policy, all slots are checked for the threshold:

.. code-block:: python

   from routilux.activation_policies import batch_size_policy

   class MultiSlotBatch(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("primary")
           self.add_slot("secondary")
           self.add_event("result")

           def process(slot_data, policy_message, worker_state):
               primary_count = len(slot_data.get("primary", []))
               secondary_count = len(slot_data.get("secondary", []))

               print(f"Primary: {primary_count}, Secondary: {secondary_count}")

               # Process combined data from both slots
               all_items = (
                   slot_data.get("primary", []) +
                   slot_data.get("secondary", [])
               )

               for item in all_items:
                   print(f"  Processing: {item}")

           self.set_logic(process)
           # Activate when either slot has 10 items
           self.set_activation_policy(batch_size_policy(10))

.. note:: **Batch Threshold Logic**

   With multiple slots, the policy activates when **ANY** slot reaches the
   batch size. The logic function then receives data from **ALL** slots.

Complete Example: Database Batch Writer
--------------------------------------

.. code-block:: python
   :linenos:

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import batch_size_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   class DatabaseBatchWriter(Routine):
       """Efficiently writes records to database in batches."""

       def __init__(self):
           super().__init__()
           self.add_slot("records")
           self.add_event("committed", ["batch_size", "record_ids"])

           def write_batch(slot_data, policy_message, worker_state):
               records = slot_data.get("records", [])
               batch_size = len(records)

               if not records:
                   return

               # Simulate batch database write
               print(f"\nWriting {batch_size} records to database...")
               record_ids = []

               for record in records:
                   record_id = f"rec_{record['id']}"
                   # Simulate database insert
                   print(f"  INSERT: {record_id} ({record})")
                   record_ids.append(record_id)

               # Emit confirmation
               self.emit("committed", batch_size=batch_size, record_ids=record_ids)

               # Track statistics in WorkerState
               state = worker_state.get_routine_state("writer") or {}
               state["total_written"] = state.get("total_written", 0) + batch_size
               state["total_batches"] = state.get("total_batches", 0) + 1
               worker_state.update_routine_state("writer", state)

               print(f"Stats: {state['total_written']} total, {state['total_batches']} batches\n")

           self.set_logic(write_batch)
           # Batch writes of 50 records
           self.set_activation_policy(batch_size_policy(50))

   # Build flow
   flow = Flow("db_writer")
   flow.add_routine(DatabaseBatchWriter(), "writer")
   FlowRegistry.get_instance().register_by_name("db_writer", flow)

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("db_writer")

       # Simulate 175 records
       print("Posting 175 records...\n")
       for i in range(175):
           runtime.post("db_writer", "writer", "records", {"id": i, "data": f"record_{i}"})

       runtime.wait_until_all_jobs_finished(timeout=10.0)

   # Check final stats
   writer_state = runtime._worker_state.get_routine_state("writer", {})
   print(f"Final stats: {writer_state}")

**Expected Output**:

.. code-block:: text

   Posting 175 records...

   Writing 50 records to database...
     INSERT: rec_0 ({'id': 0, 'data': 'record_0'})
     INSERT: rec_1 ({'id': 1, 'data': 'record_1'})
     ...
   Stats: 50 total, 1 batches

   Writing 50 records to database...
   ...

   Writing 50 records to database...
   ...

   Writing 25 records to database...
     INSERT: rec_174 ({'id': 174, 'data': 'record_174'})
   Stats: 175 total, 4 batches

   Final stats: {'total_written': 175, 'total_batches': 4}

Performance Considerations
---------------------------

**Latency vs Throughput**:

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Metric
     - Effect
   * - Latency
     - Higher (waits for batch to fill)
   * - Throughput
     - Much higher (amortizes overhead)
   * - CPU Usage
     - Lower (fewer executions)
   * - Memory
     - Higher (items queued)

**Choosing Batch Size**:

.. code-block:: text

   Too Small (< 10):
   ├─ Pros: Low latency
   └─ Cons: High overhead, poor throughput

   Just Right (10-100):
   ├─ Pros: Balanced latency/throughput
   └─ Cons: Some latency

   Too Large (> 1000):
   ├─ Pros: Maximum throughput
   └─ Cons: High latency, large memory usage

**Tuning Batch Size**:

.. code-block:: python

   # Start with a reasonable batch size
   routine.set_activation_policy(batch_size_policy(100))

   # Monitor and adjust:
   # - If queue is always full → Increase batch size or thread pool
   # - If jobs take too long → Decrease batch size
   # - If memory usage is high → Decrease batch size

Partial Batches
----------------

When the flow completes, remaining items are processed as a partial batch:

.. code-block:: python

   class BatchProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")
           self.add_event("processed")

           def process(slot_data, policy_message, worker_state):
           items = slot_data.get("items", [])
           print(f"Processing batch of {len(items)} items")

       self.set_logic(process)
       self.set_activation_policy(batch_size_policy(10))

   # Post only 7 items (less than batch size)
   for i in range(7):
       runtime.post("flow", "processor", "items", {"value": i})

   runtime.wait_until_all_jobs_finished(timeout=5.0)

   # Output: "Processing batch of 7 items"
   # The partial batch is processed when flow completes

Pitfalls and Solutions
----------------------

.. warning:: **Pitfall 1: Batch Size Too Large**

   Large batches cause high memory usage and latency:

   .. code-block:: python

      # WRONG - Too large
      self.set_activation_policy(batch_size_policy(100000))

   **Solution**: Size appropriately for your data size and memory constraints.

.. warning:: **Pitfall 2: Batch Size Too Small**

   Small batches don't provide throughput benefits:

   .. code-block:: python

      # WRONG - Too small (no real batching benefit)
      self.set_activation_policy(batch_size_policy(2))

   **Solution**: Use batch size of at least 10-20 for meaningful throughput gains.

.. warning:: **Pitfall 3: Assuming Fixed Batch Sizes**

   Batch sizes vary based on arrival timing:

   .. code-block:: python

      # Posting 100 items rapidly
      for i in range(100):
          runtime.post("flow", "routine", "slot", {"value": i})

      # Might get: [50], [50] or [100] or [33, 33, 34]
      # Depends on timing!

   **Solution**: Don't assume fixed batch sizes in your logic.

Next Steps
----------

- :doc:`all_slots_ready` - Wait for all slots with data
- :doc:`time_interval` - Time-based activation
- :doc:`../basics/understanding_runtime` - Runtime execution

.. seealso::

   :doc:`../../api_reference/activation_policies`
      Complete activation policy reference
