Immediate Policy
================

The ``immediate_policy`` is the default activation policy that executes a routine
immediately when any slot receives data.

.. note:: **What You'll Learn**

   - How immediate_policy works
   - When to use it (and when not to)
   - Expected behavior and performance characteristics
   - Common pitfalls

.. note:: **Prerequisites**

   - :doc:`../basics/understanding_routines` - Understand Routines first

How Immediate Policy Works
----------------------------

The immediate policy activates a routine as soon as ANY slot receives new data:

.. code-block:: text

   Slot receives data
       │
       ▼
   Check: Does ANY slot have data?
       │
       ├─ No ──▶ Do nothing (wait)
       │
       └─ Yes ──▶ Consume ALL new data from ALL slots
                │
                ▼
           Execute logic()
                │
                ▼
           Return data_slice to logic

**Key Characteristics**:

- **Trigger**: ANY slot receiving data triggers execution
- **Data scope**: Consumes ALL new data from ALL slots
- **Execution**: Runs logic function immediately
- **Use case**: Most common pattern, simple workflows

Basic Usage
-----------

.. code-block:: python
   :linenos:

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   class QuickProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("data")
           self.add_event("result", ["processed"])

           def process(slot_data, policy_message, worker_state):
               data_list = slot_data.get("data", [])
               for item in data_list:
                   value = item.get("value", 0)
                   result = value * 2
                   print(f"Processed: {value} → {result}")
                   self.emit("result", processed=result)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Build flow
   flow = Flow("immediate_demo")
   flow.add_routine(QuickProcessor(), "processor")
   FlowRegistry.get_instance().register_by_name("immediate_demo", flow)

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("immediate_demo")

       # Each post triggers immediate execution
       runtime.post("immediate_demo", "processor", "data", {"value": 1})
       runtime.post("immediate_demo", "processor", "data", {"value": 2})
       runtime.post("immediate_demo", "processor", "data", {"value": 3})

       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Processed: 1 → 2
   Processed: 2 → 4
   Processed: 3 → 6

.. tip:: **Immediate is the Default**

   For simple workflows, ``immediate_policy`` is usually the right choice. It's
   predictable and straightforward.

When to Use Immediate Policy
-----------------------------

**Good Use Cases**:

1. **Simple request/response**: Process each request independently
2. **Real-time processing**: React immediately to incoming data
3. **Independent items**: Each data item doesn't depend on others
4. **Low latency requirements**: Need fast processing

**Example - Real-time Data Processing**:

.. code-block:: python

   class SensorProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("sensor_reading")
           self.add_event("alert", ["sensor_id", "value"])

           def process(slot_data, policy_message, worker_state):
               readings = slot_data.get("sensor_reading", [])
               for reading in readings:
                   value = reading.get("value", 0)
                   sensor_id = reading.get("sensor_id")

                   # Immediate alert if threshold exceeded
                   if value > 100:
                       print(f"ALERT: Sensor {sensor_id} value {value}")
                       self.emit("alert", sensor_id=sensor_id, value=value)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

When NOT to Use Immediate Policy
-------------------------------

**Avoid immediate policy when**:

1. **Need to aggregate data**: Use ``batch_size_policy`` instead
2. **Multiple inputs must arrive together**: Use ``all_slots_ready_policy``
3. **Processing is expensive**: Batching improves throughput
4. **Need to correlate data**: Data from multiple sources needs coordination

**Example - When Batching is Better**:

.. code-block:: python

   # WRONG with immediate_policy (poor performance)
   class BatchWriter(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("record")
           self.add_event("written")

           def write(slot_data, policy_message, worker_state):
           # Writing one record at a time is slow
           for record in slot_data.get("record", []):
               write_to_database(record)  # Expensive I/O

   # RIGHT with batch_size_policy
   from routilux.activation_policies import batch_size_policy

   class BatchWriter(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("records")
           self.add_event("written")

           def write_batch(slot_data, policy_message, worker_state):
           # Writing 100 records at once is efficient
           records = slot_data.get("records", [])
           batch_write_to_database(records)

       self.set_logic(write_batch)
       self.set_activation_policy(batch_size_policy(100))

Behavior with Multiple Slots
-----------------------------

With immediate policy, **any** slot receiving data triggers execution:

.. code-block:: python

   class MultiSlotProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("primary")
           self.add_slot("secondary")
           self.add_event("result")

           def process(slot_data, policy_message, worker_state):
               # Check which slots have data
               has_primary = bool(slot_data.get("primary", []))
               has_secondary = bool(slot_data.get("secondary", []))

               print(f"Primary: {has_primary}, Secondary: {has_secondary}")

               # Process data from both slots
               primary_data = slot_data.get("primary", [])
               secondary_data = slot_data.get("secondary", [])

               for item in primary_data:
                   print(f"Primary: {item}")

               for item in secondary_data:
                   print(f"Secondary: {item}")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   flow = Flow("multi_slot")
   flow.add_routine(MultiSlotProcessor(), "processor")
   FlowRegistry.get_instance().register_by_name("multi_slot", flow)

   with Runtime() as runtime:
       runtime.exec("multi_slot")

       # Only primary has data - executes immediately
       runtime.post("multi_slot", "processor", "primary", {"data": "A"})
       # Output: Primary: True, Secondary: False

       # Only secondary has data - executes immediately
       runtime.post("multi_slot", "processor", "secondary", {"data": "B"})
       # Output: Primary: False, Secondary: True

       runtime.wait_until_all_jobs_finished(timeout=5.0)

.. warning:: **Pitfall: Unexpected Execution**

   With immediate policy, ANY slot receiving data triggers execution. This means:

   .. code-block:: python

      # Unexpected: Routine executes even if only one slot has data
      runtime.post("flow", "routine", "slot_a", {"data": "A"})
      # Executes! (even though slot_b is empty)

   **Solution**: If you need all slots to have data, use ``all_slots_ready_policy`` instead.

Performance Characteristics
---------------------------

**Throughput**: Good for low-volume, poor for high-volume
- Each data item → One routine execution
- High overhead per item

**Latency**: Lowest possible
- No waiting for batches
- Immediate processing

**Resource Usage**: High for high-volume
- More thread pool usage
- More context switching

**Comparison Table**:

.. list-table::
   :widths: 25 25 25 25
   :header-rows: 1

   * - Aspect
     - Immediate
     - Batch (100)
     - All Slots Ready
   * - Trigger
     - Any slot has data
     - Slot has 100 items
     - All slots have data
   * - Latency
     - Lowest
     - Medium
     - Variable
   * - Throughput
     - Low (high overhead)
     - High (amortized)
     - Medium
   * - Thread Usage
     - High
     - Low
     - Medium

Common Patterns
---------------

**Pattern 1: Simple Pipeline Stage**

.. code-block:: python

   class Transformer(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def transform(slot_data, policy_message, worker_state):
               for item in slot_data.get("input", []):
                   result = transform(item)
                   self.emit("output", result=result)

           self.set_logic(transform)
           self.set_activation_policy(immediate_policy())

**Pattern 2: Event Handler**

.. code-block:: python

   class EventHandler(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("event")
           self.add_event("ack")

           def handle(slot_data, policy_message, worker_state):
               for event in slot_data.get("event", []):
                   process_event(event)
                   self.emit("ack", event_id=event["id"])

           self.set_logic(handle)
           self.set_activation_policy(immediate_policy())

**Pattern 3: State Update**

.. code-block:: python

   class StateUpdater(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("update")
           self.add_event("updated")

           def update(slot_data, policy_message, worker_state):
               state = worker_state.get_routine_state("stateful") or {}

               for item in slot_data.get("update", []):
                   key = item.get("key")
                   value = item.get("value")
                   state[key] = value  # Update state

               worker_state.update_routine_state("stateful", state)
               self.emit("updated", keys=list(state.keys()))

           self.set_logic(update)
           self.set_activation_policy(immediate_policy())

Pitfalls and Solutions
----------------------

.. warning:: **Pitfall 1: Processing Empty Slots**

   Immediate policy triggers even when some slots are empty:

   .. code-block:: python

      def logic(slot_data, policy_message, worker_state):
          # Even though only "input_a" has data, "input_b" might be empty
          input_a = slot_data.get("input_a", [])  # Has data
          input_b = slot_data.get("input_b", [])  # Empty list!

   **Solution**: Always check for empty lists:

   .. code-block:: python

      def logic(slot_data, policy_message, worker_state):
          input_a = slot_data.get("input_a", [])
          input_b = slot_data.get("input_b", [])

          if input_a and input_b:  # Only process if both have data
              # Process...

.. warning:: **Pitfall 2: Assuming Execution Order**

   Immediate policy doesn't guarantee execution order with concurrent posts:

   .. code-block:: python

      runtime.post("flow", "routine", "slot", {"id": 1})
      runtime.post("flow", "routine", "slot", {"id": 2})
      runtime.post("flow", "routine", "slot", {"id": 3})

      # May execute in any order: 1, 3, 2 or 2, 1, 3, etc.

   **Solution**: Don't assume execution order for concurrent posts.

.. warning:: **Pitfall 3: Overhead with High Volume**

   Immediate policy creates one execution per data item:

   .. code-block:: python

      # With immediate_policy: 1000 executions
      for i in range(1000):
          runtime.post("flow", "routine", "slot", {"value": i})
      # Creates 1000 logic() executions

   **Solution**: Use batch_size_policy for high-volume data:

   .. code-block:: python

      routine.set_activation_policy(batch_size_policy(100))
      # Creates only ~10 executions for 1000 items

Next Steps
----------

- :doc:`all_slots_ready` - Wait for all slots before executing
- :doc:`batch_size` - Batch processing for efficiency
- :doc:`../basics/understanding_slots_events` - Slots and events

.. seealso::

   :doc:`../../api_reference/activation_policies`
      Complete activation policy reference
