All Slots Ready Policy
======================

The ``all_slots_ready_policy`` activates a routine only when ALL slots have at
least one data item. This ensures all required inputs are present before processing.

.. note:: **What You'll Learn**

   - How all_slots_ready_policy works
   - Synchronizing multiple inputs
   - Common patterns and use cases
   - Differences from immediate_policy

.. note:: **Prerequisites**

   - :doc:`immediate_policy` - Understand immediate policy first
   - :doc:`../basics/understanding_slots_events` - Understand slots

How All Slots Ready Works
----------------------------

The all slots ready policy activates only when every slot has data:

.. code-block:: text

   Items arrive in slots
       │
       ▼
   Check: Do ALL slots have data?
       │
       ├─ No ──▶ Do nothing (wait for missing slots)
       │
       └─ Yes ─▶ Consume ONE item from EACH slot
                   │
                   ▼
              Execute logic(one_per_slot_data)
                   │
                   ▼
              Return data_slice to logic

**Key Characteristics**:

- **Trigger**: ALL slots must have at least one item
- **Data scope**: Consumes ONE item from each slot
- **Execution**: Waits for all inputs to be ready
- **Use case**: Correlated/dependent data, synchronization

Basic Usage
-----------

.. code-block:: python
   :linenos:

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import all_slots_ready_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   class DataJoiner(Routine):
       """Joins data from two sources."""

       def __init__(self):
           super().__init__()
           self.add_slot("user_data")
           self.add_slot("profile_data")
           self.add_event("joined", ["user_id", "name", "email"])

           def join(slot_data, policy_message, worker_state):
           # Each slot has ONE item (not a list of all items)
           user_list = slot_data.get("user_data", [])
           profile_list = slot_data.get("profile_data", [])

           if user_list and profile_list:
               user = user_list[0]
               profile = profile_list[0]

               # Join the data
               user_id = user.get("user_id")
               name = profile.get("name")
               email = profile.get("email")

               print(f"Joined: {user_id} - {name} ({email})")
               self.emit("joined", user_id=user_id, name=name, email=email)

           self.set_logic(join)
           self.set_activation_policy(all_slots_ready_policy())

   # Build flow
   flow = Flow("join_flow")
   flow.add_routine(DataJoiner(), "joiner")
   FlowRegistry.get_instance().register_by_name("join_flow", flow)

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("join_flow")

       # User data arrives first (no execution yet - waits)
       print("Posting user_data...")
       _, job1 = runtime.post("join_flow", "joiner", "user_data",
                            {"user_id": 123, "age": 30})
       time.sleep(0.1)

       # Profile data arrives (now both slots have data - executes!)
       print("Posting profile_data...")
       _, job2 = runtime.post("join_flow", "joiner", "profile_data",
                            {"user_id": 123, "name": "Alice", "email": "alice@example.com"})

       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Posting user_data...
   Posting profile_data...
   Joined: 123 - Alice (alice@example.com)

.. tip:: **Synchronization**

   The all_slots_ready_policy is perfect for synchronizing data from multiple
   sources. It ensures all required inputs are present before processing.

Multiple Items Per Slot
-------------------------

When slots have multiple items, only ONE item from each slot is consumed:

.. code-block:: python

   class MultiItemProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("primary")
           self.add_slot("secondary")
           self.add_event("result")

           def process(slot_data, policy_message, worker_state):
               # Get ONE item from each slot (not all items!)
           primary_list = slot_data.get("primary", [])
           secondary_list = slot_data.get("secondary", [])

           if primary_list and secondary_list:
               primary = primary_list[0]  # Only the FIRST item
               secondary = secondary_list[0]  # Only the FIRST item

               print(f"Processing: {primary} + {secondary}")
               self.emit("result", combined=f"{primary}+{secondary}")

           self.set_logic(process)
           self.set_activation_policy(all_slots_ready_policy())

   flow = Flow("multi_item")
   flow.add_routine(MultiItemProcessor(), "processor")
   FlowRegistry.get_instance().register_by_name("multi_item", flow)

   with Runtime() as runtime:
       runtime.exec("multi_item")

       # Fill both slots with multiple items
       for i in range(5):
           runtime.post("multi_item", "processor", "primary", {"p": i})
           runtime.post("multi_item", "processor", "secondary", {"s": i})

       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output** (order may vary):

.. code-block:: text

   Processing: {'p': 0} + {'s': 0}
   Processing: {'p': 1} + {'s': 1}
   Processing: {'p': 2} + {'s': 2}
   Processing: {'p': 3} + {'s': 3}
   Processing: {'p': 4} + {'s': 4}

.. note:: **One-to-One Consumption**

   With all_slots_ready_policy, items are consumed in pairs:
   - First execution: item[0] from primary + item[0] from secondary
   - Second execution: item[1] from primary + item[1] from secondary
   - etc.

   This ensures paired processing of correlated items.

Common Patterns
---------------

**Pattern 1: Data Join**

.. code-block:: python

   class DataJoiner(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("left_table")
           self.add_slot("right_table")
           self.add_event("joined")

           def join_logic(slot_data, policy_message, worker_state):
               left = slot_data.get("left_table", [{}])[0]
               right = slot_data.get("right_table", [{}])[0]

               # Join on key
               if left["key"] == right["key"]:
                   joined = {**left, **right}
                   self.emit("joined", data=joined)

           self.set_logic(join_logic)
           self.set_activation_policy(all_slots_ready_policy())

**Pattern 2: Configuration Validation**

.. code-block:: python

   class Validator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("config")
           self.add_slot("data")
           self.add_event("validated")

           def validate(slot_data, policy_message, worker_state):
               config = slot_data.get("config", [{}])[0]
               data = slot_data.get("data", [{}])[0]

               # Validate data against config
               if meets_requirements(data, config):
                   self.emit("validated", data=data)

           self.set_logic(validate)
           self.set_activation_policy(all_slots_ready_policy())

**Pattern 3: Correlation**

.. code-block:: python

   class Correlator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("sensor_a")
           self.add_slot("sensor_b")
           self.add_event("correlation")

           def correlate(slot_data, policy_message, worker_state):
               reading_a = slot_data.get("sensor_a", [{}])[0]
               reading_b = slot_data.get("sensor_b", [{}])[0]

               # Correlate readings from same timestamp
               if abs(reading_a["timestamp"] - reading_b["timestamp"]) < 0.1:
                   correlation = (reading_a["value"] + reading_b["value"]) / 2
                   self.emit("correlation", value=correlation)

           self.set_logic(correlate)
           self.set_activation_policy(all_slots_ready_policy())

Immediate vs All Slots Ready
----------------------------

.. list-table::
   :widths: 40 30 30
   :header-rows: 1

   * - Aspect
     - Immediate
     - All Slots Ready
     - Use Case
   * - Trigger condition
     - ANY slot has data
     - ALL slots have data
     -
   * - Data consumed
     - ALL new data from ALL slots
     - ONE item from EACH slot
     -
   * - Execution frequency
     - Higher (more executions)
     - Lower (synchronized)
     -
   * - Best for
     - Independent data
     - Correlated/dependent data
     -
   * - Avoid when
     - Data must be synchronized
     - Slots fill at different rates
     -

**Example Comparison**:

.. code-block:: python

   # Immediate: Executes 3 times (once per slot)
   class ImmediateProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("a")
           self.add_slot("b")
           self.add_slot("c")

           def process(slot_data, policy_message, worker_state):
           # Gets ALL new data from ALL slots
           for slot_name, items in slot_data.items():
               for item in items:
                   print(f"Processing: {slot_name} - {item}")

       self.set_logic(process)
       self.set_activation_policy(immediate_policy())

   # All Slots Ready: Executes 1 time (one per slot pair)
   class SynchronizedProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("a")
           self.add_slot("b")
           self.add_slot("c")

           def process(slot_data, policy_message, worker_state):
           # Gets ONE item from EACH slot
           for slot_name, items in slot_data.items():
               item = items[0]  # Only first item
               print(f"Processing: {slot_name} - {item}")

       self.set_logic(process)
       self.set_activation_policy(all_slots_ready_policy())

Pitfalls and Solutions
----------------------

.. warning:: **Pitfall 1: Deadlock with Missing Slots**

   If one slot never receives data, the routine never executes:

   .. code-block:: python

      # Problem: "secondary" slot never receives data
      runtime.post("flow", "routine", "primary", {"data": "A"})
      # "secondary" slot stays empty → routine never executes!

   **Solution**: Ensure all slots receive data, or use timeout mechanisms.

.. warning:: **Pitfall 2: Assuming All Data is Processed**

   All slots ready only consumes ONE item per slot:

   .. code-block:: python

      # Post 10 items to each slot
      for i in range(10):
          runtime.post("flow", "routine", "slot_a", {"id": i})
          runtime.post("flow", "routine", "slot_b", {"id": i})

      # With all_slots_ready_policy:
      # - Executes 10 times (not 1 time!)
      # - Each execution processes: slot_a[i] + slot_b[i]
      # - Items are paired by position

   **Solution**: Understand the one-to-one consumption pattern.

.. warning:: **Pitfall 3: Unbounded Queue Growth**

   If one slot fills faster than others, queues can grow unbounded:

   .. code-block:: python

      # "fast_slot" receives 1000 items
      # "slow_slot" receives only 10 items
      # fast_slot's queue grows to 990 items!

   **Solution**:
   - Use ``max_queue_length`` to limit queue size
   - Ensure balanced data rates
   - Monitor queue depths

Complete Example: Correlating Sensor Data
-----------------------------------------

.. code-block:: python
   :linenos:

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import all_slots_ready_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   import time

   class TemperatureSensor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("temperature", ["sensor_id", "value", "timestamp"])

           def read_sensor(slot_data, policy_message, worker_state):
               import random
               for i in range(5):
                   value = random.uniform(20, 30)
                   timestamp = time.time()
                   print(f"[Temp] Sensor A: {value:.1f}°C at {timestamp}")
                   self.emit("temperature", sensor_id="A", value=value, timestamp=timestamp)
                   time.sleep(0.05)

           self.set_logic(read_sensor)
           self.set_activation_policy(immediate_policy())

   class PressureSensor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("pressure", ["sensor_id", "value", "timestamp"])

           def read_sensor(slot_data, policy_message, worker_state):
               import random
               for i in range(5):
                   value = random.uniform(100, 120)
                   timestamp = time.time()
                   print(f"[Pressure] Sensor B: {value:.1f}kPa at {timestamp}")
                   self.emit("pressure", sensor_id="B", value=value, timestamp=timestamp)
                   time.sleep(0.05)

           self.set_logic(read_sensor)
           self.set_activation_policy(immediate_policy())

   class SensorCorrelator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("temperature")
           self.add_slot("pressure")

           def correlate(slot_data, policy_message, worker_state):
               temp_list = slot_data.get("temperature", [])
               pressure_list = slot_data.get("pressure", [])

               if temp_list and pressure_list:
                   temp = temp_list[0]
                   pressure = pressure_list[0]

                   # Correlate readings within 0.1 seconds
                   if abs(temp["timestamp"] - pressure["timestamp"]) < 0.1:
                       print(f"\n[Correlator] Correlated readings:")
                       print(f"  Temperature: {temp['value']:.1f}°C")
                       print(f"  Pressure: {pressure['value']:.1f}kPa")
                       print(f"  Time diff: {abs(temp['timestamp'] - pressure['timestamp']):.3f}s\n")

           self.set_logic(correlate)
           self.set_activation_policy(all_slots_ready_policy())

   # Build flow
   flow = Flow("sensor_correlation")

   flow.add_routine(TemperatureSensor(), "temp_sensor")
   flow.add_routine(PressureSensor(), "pressure_sensor")
   flow.add_routine(SensorCorrelator(), "correlator")

   # Connect: sensors → correlator
   flow.connect("temp_sensor", "temperature", "correlator", "temperature")
   flow.connect("pressure_sensor", "pressure", "correlator", "pressure")

   FlowRegistry.get_instance().register_by_name("sensor_correlation", flow)

   with Runtime(thread_pool_size=3) as runtime:
       runtime.exec("sensor_correlation")

       # Trigger both sensors
       runtime.post("sensor_correlation", "temp_sensor", "trigger", {})
       runtime.post("sensor_correlation", "pressure_sensor", "trigger", {})

       runtime.wait_until_all_jobs_finished(timeout=10.0)

**Expected Output** (timestamps will vary):

.. code-block:: text

   [Temp] Sensor A: 25.3°C at 1700000000.000
   [Pressure] Sensor B: 110.5kPa at 1700000000.050

   [Correlator] Correlated readings:
     Temperature: 25.3°C
     Pressure: 110.5kPa
     Time diff: 0.050s

   [Temp] Sensor A: 26.1°C at 1700000000.100
   [Pressure] Sensor B: 112.3kPa at 1700000000.150

   [Correlator] Correlated readings:
     Temperature: 26.1°C
     Pressure: 112.3kPa
     Time diff: 0.050s

   ... (continues for all 5 readings)

Next Steps
----------

- :doc:`batch_size` - Batch processing for efficiency
- :doc:`time_interval` - Time-based activation
- :doc:`../connections/many_to_one` - Fan-in aggregation patterns

.. seealso::

   :doc:`../../api_reference/activation_policies`
      Complete activation policy reference
