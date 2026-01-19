Understanding Routines
======================

Routines are the fundamental building blocks of Routilux workflows. A **Routine**
is a self-contained unit of work that receives data through **slots**, processes
it using **logic functions**, and emits results through **events**.

.. note:: **What You'll Learn**

   - The Routine class structure and lifecycle
   - How to define slots (inputs) and events (outputs)
   - How to write logic functions
   - How to use configuration with ``set_config()``
   - The critical constraint: NO constructor parameters

.. note:: **Prerequisites**

   - :doc:`../hello_world` - Complete the Hello World tutorial first

The Routine Structure
---------------------

A Routine consists of four key components:

.. code-block:: text

   ┌─────────────────────────────────────────────────────────┐
   │                    Routine                               │
   │                                                         │
   │  ┌────────────────┐      ┌────────────────┐            │
   │  │   Slots (In)   │ ───▶ │   Logic        │ ───▶  Events │
   │  │                │      │   Function     │      (Out)  │
   │  │ • data         │      │                │      •      │
   │  │ • trigger      │      │  • Process     │      •      │
   │  │ • input        │      │  • Transform   │      •      │
   │  └────────────────┘      │  • Emit        │      └──────┘
   │                          └────────────────┘             │
   │                                                         │
   │  Configuration: _config = {}                             │
   └─────────────────────────────────────────────────────────┘

1. **Slots** - Input mechanisms that receive data
2. **Logic Function** - Contains the processing logic
3. **Events** - Output mechanisms that send data
4. **Configuration** - Stores routine settings (via ``_config``)

Creating a Routine
------------------

Here's a complete example of a Routine that processes numbers:

.. code-block:: python
   :linenos:
   :name: understanding_routines_basic

   from routilux import Routine
   from routilux.activation_policies import immediate_policy

   class NumberDoubler(Routine):
       """A routine that doubles numbers and counts executions."""

       def __init__(self):
           # CRITICAL: Always call super().__init__() first
           super().__init__()

           # Add input slot
           self.add_slot("number")

           # Add output event with parameter names
           self.add_event("result", ["doubled"])

           # Set configuration values
           self.set_config(
               multiplier=2,
               max_number=1000
           )

           # Define logic function
           def double_number(slot_data, policy_message, worker_state):
               # Extract data from slot
               number_list = slot_data.get("number", [])
               if number_list:
                   number = number_list[0].get("value", 0)

                   # Get configuration
                   multiplier = self.get_config("multiplier", 2)
                   max_number = self.get_config("max_number", 1000)

                   # Validate
                   if number > max_number:
                       print(f"Number {number} exceeds maximum {max_number}")
                       return

                   # Process
                   result = number * multiplier

                   # Update worker-level state
                   worker_state.update_routine_state(
                       worker_state.current_routine_id,
                           "processed_count": worker_state.routine_states.get(
                               worker_state.current_routine_id, {}
                           ).get("processed_count", 0) + 1,
                           "last_processed": number
                       }
                   )

                   # Emit result
                   self.emit("result", doubled=result)
                   print(f"Doubled {number} → {result}")

           # Set logic and activation policy
           self.set_logic(double_number)
           self.set_activation_policy(immediate_policy())

.. tip:: **Understanding slot_data Structure**

   The ``slot_data`` parameter in your logic function is a dictionary where:

   - Keys are slot names (e.g., ``"number"``, ``"input"``)
   - Values are lists of data items received by that slot
   - Each item is a dictionary with the data you sent

   Example: If you call ``runtime.post(..., {"value": 42})``, then
   ``slot_data["number"][0]["value"]`` equals ``42``.

.. danger:: **CRITICAL CONSTRAINT: No Constructor Parameters**

   Routines **MUST NOT** accept constructor parameters (except ``self``). This is
   required for proper serialization and deserialization.

   **WRONG** ❌:

   .. code-block:: python

      class MyRoutine(Routine):
          def __init__(self, multiplier=2):  # Don't do this!
              super().__init__()
              self.multiplier = multiplier

   **RIGHT** ✅:

   .. code-block:: python

      class MyRoutine(Routine):
          def __init__(self):
              super().__init__()
              self.set_config(multiplier=2)  # Use _config instead

   **Why this constraint?**

   Routines need to be serializable (saved to disk/transferred over network).
   Constructor parameters would be lost during serialization. The ``_config``
   dictionary is automatically serialized.

Understanding Slots
-------------------

Slots are the **input** mechanism for routines. They receive data from events
emitted by other routines.

.. code-block:: python

   # Add a slot with default settings
   self.add_slot("input")

   # Add a slot with custom queue size
   self.add_slot("data", max_queue_length=5000, watermark=0.9)

.. note:: **Slot Parameters**

   - ``name``: Unique slot name within the routine
   - ``max_queue_length``: Maximum queue size (default: 1000)
   - ``watermark``: Threshold for auto-shrink (default: 0.8 = 80%)

.. warning:: **Pitfall: Slot Queue Full**

   When a slot's queue is full, new data will be rejected and raise
   ``SlotQueueFullError``. Choose an appropriate ``max_queue_length`` based on
   your expected data volume.

Understanding Events
--------------------

Events are the **output** mechanism for routines. They send data to connected
slots.

.. code-block:: python

   # Add an event with parameter names (for documentation)
   self.add_event("result", ["doubled", "original"])

   # Emit the event in your logic
   self.emit("result", doubled=42, original=21)

.. note:: **Event Parameter Names**

   The parameter names in ``add_event()`` are for documentation and API
   generation. They don't affect runtime behavior but help users understand
   what data the event provides.

.. tip:: **Emitting Multiple Events**

   A single logic execution can emit multiple events:

   .. code-block:: python

      def process_logic(slot_data, policy_message, worker_state):
          self.emit("success", result=42)
          self.emit("metadata", processed_at="2024-01-01")
          self.emit("stats", count=1)

Understanding Logic Functions
------------------------------

The logic function contains your routine's processing logic. It receives three
parameters:

.. code-block:: python

   def my_logic(slot_data, policy_message, worker_state):
       # slot_data: dict[str, list[dict]] - Data from slots
       # policy_message: Any - Message from activation policy
       # worker_state: WorkerState - Worker-level state tracking

       pass

**slot_data** structure:

.. code-block:: python

   {
       "slot_name_1": [
           {"key": "value", "other": 123},
           {"key": "value2", "other": 456}
       ],
       "slot_name_2": [
           {"data": "item1"}
       ]
   }

.. warning:: **Pitfall: Empty Slot Lists**

   Always check if slot data exists before accessing:

   .. code-block:: python
      :emphasize-lines: 3

      def my_logic(slot_data, policy_message, worker_state):
          data_list = slot_data.get("input", [])
          if not data_list:  # Always check!
              return

          value = data_list[0].get("key", "default")

**policy_message** contains information from the activation policy:

.. code-block:: python

   def my_logic(slot_data, policy_message, worker_state):
       # Check why routine was activated
       reason = policy_message.get("reason", "unknown")
       if reason == "immediate":
           print("Activated by immediate policy")
       elif reason == "all_slots_ready":
           print("Activated by all_slots_ready policy")

**worker_state** is for tracking long-running state across job executions:

.. code-block:: python

   def my_logic(slot_data, policy_message, worker_state):
       # Get routine-specific state
       state = worker_state.get_routine_state("my_routine_id") or {}
       count = state.get("count", 0)

       # Update state
       worker_state.update_routine_state("my_routine_id", {
           "count": count + 1,
           "last_processed": "data"
       })

.. note:: **WorkerState vs JobContext**

   - **WorkerState**: Long-running, persistent state (like a server process)
   - **JobContext**: Per-request state (like an HTTP request)

   See :doc:`../state/worker_state` for details.

Configuration with set_config()
-------------------------------

Use ``set_config()`` to store routine configuration. This is the recommended
way to pass settings to routines.

.. code-block:: python
   :linenos:

   class ConfigurableRoutine(Routine):
       def __init__(self):
           super().__init__()

           # Set configuration values
           self.set_config(
               timeout=30,
               retry_count=3,
               enabled_features=["feature1", "feature2"]
           )

           def process_logic(slot_data, policy_message, worker_state):
               # Read configuration
               timeout = self.get_config("timeout", 10)
               retry_count = self.get_config("retry_count", 1)

               print(f"Processing with timeout={timeout}, retries={retry_count}")

           self.set_logic(process_logic)
           self.set_activation_policy(immediate_policy())

   # Later, you can update configuration (before execution starts)
   routine = ConfigurableRoutine()
   routine.set_config(timeout=60)  # Update timeout

.. warning:: **Don't Modify Config During Execution**

   Once execution starts, ``_config`` becomes read-only. Use ``WorkerState``
   for execution-time state changes.

   .. code-block:: python

      # WRONG - Will raise RuntimeError during execution
      def logic(slot_data, policy_message, worker_state):
          self.set_config(new_value=123)  # Don't do this!

      # RIGHT - Use WorkerState for execution state
      def logic(slot_data, policy_message, worker_state):
          worker_state.update_routine_state("my_id", {
              "new_value": 123
          })

Activation Policies
-------------------

Every routine **must** have an activation policy set. The policy determines
when the routine's logic function executes.

.. code-block:: python

   # Immediate execution when data arrives
   self.set_activation_policy(immediate_policy())

   # Wait until all slots have data
   self.set_activation_policy(all_slots_ready_policy())

   # Wait for a batch of data
   self.set_activation_policy(batch_size_policy(10))

   # Time-based execution
   self.set_activation_policy(time_interval_policy(5.0))

.. danger:: **CRITICAL: Always Set Activation Policy**

   Routines without an activation policy will **never execute**. Always call
   ``set_activation_policy()`` after defining your logic function.

   .. code-block:: python
      :emphasize-lines: 8

      class MyRoutine(Routine):
          def __init__(self):
              super().__init__()
              self.add_slot("input")
              self.add_event("output")
              self.set_logic(process)
              # Missing: self.set_activation_policy(immediate_policy())!
              # This routine will NEVER execute!

Complete Example: Data Validator
---------------------------------

Here's a complete, practical example of a Routine that validates data:

.. code-block:: python
   :linenos:
   :name: understanding_routines_validator

   from routilux import Routine
   from routilux.activation_policies import immediate_policy
   from datetime import datetime

   class DataValidator(Routine):
       """Validates incoming data and emits valid/invalid events."""

       def __init__(self):
           super().__init__()

           # Input/output
           self.add_slot("data")
           self.add_event("valid", ["data", "validated_at"])
           self.add_event("invalid", ["data", "reason", "validated_at"])

           # Configuration
           self.set_config(
               require_email=True,
               require_phone=False,
               min_age=18
           )

           def validate(slot_data, policy_message, worker_state):
               data_list = slot_data.get("data", [])
               if not data_list:
                   return

               data = data_list[0]
               validated_at = datetime.now().isoformat()

               # Get validation rules from config
               require_email = self.get_config("require_email", True)
               require_phone = self.get_config("require_phone", False)
               min_age = self.get_config("min_age", 18)

               # Validate
               reasons = []

               if require_email and not data.get("email"):
                   reasons.append("missing_email")

               if require_phone and not data.get("phone"):
                   reasons.append("missing_phone")

               age = data.get("age", 0)
               if age < min_age:
                   reasons.append(f"age_below_minimum:{age}<{min_age}")

               # Update statistics
               routine_id = worker_state.current_routine_id
               state = worker_state.get_routine_state(routine_id) or {}
               total_validated = state.get("total_validated", 0) + 1
               if reasons:
                   invalid_count = state.get("invalid_count", 0) + 1
                   worker_state.update_routine_state(routine_id, {
                       "total_validated": total_validated,
                       "invalid_count": invalid_count,
                       "last_validation": "invalid"
                   })
               else:
                   valid_count = state.get("valid_count", 0) + 1
                   worker_state.update_routine_state(routine_id, {
                       "total_validated": total_validated,
                       "valid_count": valid_count,
                       "last_validation": "valid"
                   })

               # Emit appropriate event
               if reasons:
                   self.emit("invalid", data=data, reason=",".join(reasons),
                             validated_at=validated_at)
                   print(f"Invalid data: {reasons}")
               else:
                   self.emit("valid", data=data, validated_at=validated_at)
                   print(f"Valid data: {data}")

           self.set_logic(validate)
           self.set_activation_policy(immediate_policy())

Common Patterns
---------------

**Pattern 1: Transform and Forward**

.. code-block:: python

   class Transformer(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output", ["result"])

           def transform(slot_data, policy_message, worker_state):
               input_data = slot_data.get("input", [{}])[0]
               result = input_data.get("value", 0) * 2
               self.emit("output", result=result)

           self.set_logic(transform)
           self.set_activation_policy(immediate_policy())

**Pattern 2: Aggregate and Batch**

.. code-block:: python

   class Aggregator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")
           self.add_event("batch", ["items", "count"])

           def aggregate(slot_data, policy_message, worker_state):
               items_list = slot_data.get("items", [])
               # items_list contains all items in the batch
               self.emit("batch", items=items_list, count=len(items_list))

           self.set_logic(aggregate)
           self.set_activation_policy(batch_size_policy(10))

**Pattern 3: Conditional Routing**

.. code-block:: python

   class Router(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("high_priority", ["data"])
           self.add_event("low_priority", ["data"])

           def route(slot_data, policy_message, worker_state):
               data = slot_data.get("input", [{}])[0]
               priority = data.get("priority", 0)

               if priority >= 5:
                   self.emit("high_priority", data=data)
               else:
                   self.emit("low_priority", data=data)

           self.set_logic(route)
           self.set_activation_policy(immediate_policy())

Pitfalls Reference
------------------

.. list-table:: Common Routine Pitfalls
   :widths: 50 50
   :header-rows: 1

   * - Pitfall
     - Solution
   * - Passing constructor parameters
     - Use ``set_config()`` instead
   * - Forgetting ``super().__init__()``
     - Always call it first in ``__init__``
   * - Not setting activation policy
     - Always call ``set_activation_policy()``
   * - Modifying instance variables in logic
     - Use ``WorkerState`` for state
   * - Not checking empty slot lists
     - Always check ``if data_list:`` before accessing
   * - Forgetting to emit events
     - Always call ``self.emit()`` to send results
   * - Modifying config during execution
     - Config is read-only during execution

Next Steps
----------

Now that you understand Routines, learn about:

- :doc:`understanding_slots_events` - How slots and events work together
- :doc:`understanding_flows` - Connecting routines in flows
- :doc:`../activation/immediate_policy` - Activation policies in detail
- :doc:`../state/worker_state` - WorkerState for persistent state

.. seealso::

   :doc:`../../pitfalls/routine_design`
      Common routine design pitfalls and solutions

   :doc:`../../api_reference/core/routine`
      Complete Routine API reference
