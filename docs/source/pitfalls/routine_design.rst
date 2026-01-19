Routine Design Pitfalls
======================

This section covers common mistakes when designing and implementing Routines.
These are the most frequent sources of bugs and confusion for new users.

.. note:: **Overview**

   | Pitfall | Severity | Frequency |
   |---------|----------|-----------|
   | Constructor Parameters | 🔴 Critical | Very High |
   | Modifying Instance Variables | 🟡 High | High |
   | Forgetting Activation Policy | 🔴 Critical | High |
   | Wrong Signature in Logic | 🟡 High | Medium |
   | Not Handling Empty Slots | 🟢 Medium | Medium |
   | Blocking in Thread Pool | 🟡 High | Medium |

---

Pitfall 1: Constructor Parameters
----------------------------------

**The Pitfall**

Passing parameters to Routine ``__init__`` breaks serialization:

.. code-block:: python
   :emphasize-lines: 2

   # WRONG - This will break!
   class MyRoutine(Routine):
       def __init__(self, api_key="default"):
           super().__init__()
           self.api_key = api_key  # Lost during serialization!

   # Usage
   routine = MyRoutine(api_key="secret_key")
   flow.add_routine(routine, "processor")
   # Serialization/deserialization will lose api_key!

**Why It Happens**

Routines must be serializable for:
- Persistence (saving flow state to disk)
- Network transfer (distributed execution)
- Cloning (multiple workers)

Constructor parameters are not included in automatic serialization.

**Symptoms**

- Configuration is lost after serialization
- Routines use default values instead of custom ones
- ``AttributeError`` when accessing missing attributes after deserialization
- Inexplicable behavior in distributed/clustered setups

**Solution**

Use ``set_config()`` for all configuration:

.. code-block:: python

   # RIGHT - Use _config dictionary
   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.set_config(api_key="default")  # Stored in _config

       def logic(self, slot_data, policy_message, worker_state):
           # Read from _config
           api_key = self.get_config("api_key", "default")

   # Set custom config after creation
   routine = MyRoutine()
   routine.set_config(api_key="secret_key")

**Prevention**

- ✅ Always use parameterless ``__init__`` (except ``self``)
- ✅ Use ``set_config()`` for all configuration
- ✅ Use ``get_config()`` to read configuration in logic
- ❌ Never pass parameters to Routine constructor

**Related**

- :doc:`serialization` - Serialization requirements
- :doc:`../tutorial/basics/understanding_routines` - Routine design basics

---

Pitfall 2: Modifying Instance Variables
----------------------------------------

**The Pitfall**

Modifying ``self`` attributes during execution:

.. code-block:: python
   :emphasize-lines: 8

   # WRONG - Modifying instance variables
   class Counter(Routine):
       def __init__(self):
           super().__init__()
           self.count = 0  # Instance variable
           self.add_slot("input")

       def count_logic(self, slot_data, policy_message, worker_state):
           self.count += 1  # This breaks thread-safety!
           print(f"Count: {self.count}")

**Why It Happens**

Developers are used to storing state in instance variables. However, in
Routilux:
- Multiple threads may execute the same routine concurrently
- Instance variables are shared across executions
- No automatic synchronization

**Symptoms**

- Inconsistent counts (race conditions)
- Data corruption under load
- Values changing unexpectedly
- Heisenbugs (disappear when debugging)

**Solution**

Use ``WorkerState`` for execution state:

.. code-block:: python

   # RIGHT - Use WorkerState
   class Counter(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")

       def count_logic(self, slot_data, policy_message, worker_state):
           # Get routine state
           state = worker_state.get_routine_state("counter") or {}
           count = state.get("count", 0) + 1

           # Update state
           worker_state.update_routine_state("counter", {"count": count})
           print(f"Count: {count}")

**Prevention**

- ✅ Use ``WorkerState`` for all execution state
- ✅ Use ``JobContext`` for per-request state
- ✅ Use ``_config`` for read-only configuration
- ❌ Never modify ``self`` attributes in logic()

**Related**

- :doc:`state_management` - WorkerState vs JobContext
- :doc:`concurrency` - Thread safety considerations

---

Pitfall 3: Forgetting Activation Policy
---------------------------------------

**The Pitfall**

Creating a routine without setting an activation policy:

.. code-block:: python
   :emphasize-lines: 8

   # WRONG - No activation policy!
   class Processor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def process(slot_data, policy_message, worker_state):
               self.emit("output", result="done")

           self.set_logic(process)
           # Missing: self.set_activation_policy(...)

   # Result: Routine never executes!

**Why It Happens**

The activation policy determines *when* a routine executes. Without one,
the routine never activates even when data arrives.

**Symptoms**

- Routine never executes
- Data sits in slots unprocessed
- No errors or warnings (silent failure)
- Flow appears "stuck"

**Solution**

Always set an activation policy:

.. code-block:: python

   # RIGHT - Set activation policy
   from routilux.activation_policies import immediate_policy

   class Processor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("output")

           def process(slot_data, policy_message, worker_state):
               self.emit("output", result="done")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())  # Required!

**Prevention**

- ✅ Always call ``set_activation_policy()`` after ``set_logic()``
- ✅ Choose policy based on use case:
     - ``immediate_policy()`` - Execute as soon as data arrives
     - ``all_slots_ready_policy()`` - Wait for all slots
     - ``batch_size_policy(n)`` - Batch n items
     - ``time_interval_policy(seconds)`` - Time-based execution
- ❌ Never leave routine without activation policy

**Related**

- :doc:`../tutorial/activation/immediate_policy` - Activation policies
- :doc:`../user_guide/activation_policies` - Policy reference

---

Pitfall 4: Wrong Logic Signature
---------------------------------

**The Pitfall**

Using wrong function signature for logic:

.. code-block:: python
   :emphasize-lines: 3

   # WRONG - Wrong signature
   class Processor(Routine):
       def __init__(self):
           super().__init__()

           def process(data):  # Missing parameters!
               print(data)

           self.set_logic(process)

**Why It Happens**

The logic function signature must be:
```python
def logic(slot_data, policy_message, worker_state):
```

**Symptoms**

- ``TypeError`` when routine activates
- "Missing required positional argument"
- Routine fails immediately on activation

**Solution**

Use correct signature:

.. code-block:: python

   # RIGHT - Correct signature
   class Processor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")

           def process(slot_data, policy_message, worker_state):
               # slot_data: dict[str, list[dict]] - Data from slots
               # policy_message: Any - Message from activation policy
               # worker_state: WorkerState - Worker state object

               input_list = slot_data.get("input", [])
               if input_list:
                   print(input_list[0])

           self.set_logic(process)

**Prevention**

- ✅ Always use 3 parameters: ``slot_data, policy_message, worker_state``
- ✅ Type hints help: ``def logic(slot_data: dict, policy_message: Any,
                            worker_state: WorkerState)``
- ✅ Use unused parameter prefix if not needed: ``_policy_message``

---

Pitfall 5: Not Handling Empty Slots
-----------------------------------

**The Pitfall**

Assuming slots always have data:

.. code-block:: python
   :emphasize-lines: 4

   # WRONG - Assumes data exists
   def process_logic(slot_data, policy_message, worker_state):
       data = slot_data["input"][0]  # IndexError if empty!
       value = data["value"]

**Why It Happens**

Slots may be empty if:
- Activation policy triggered but no data
- Previous routine emitted nothing
- Race condition in concurrent execution

**Symptoms**

- ``IndexError: list index out of range``
- ``KeyError: 'input'``
- Routine crashes intermittently

**Solution**

Always check for data:

.. code-block:: python

   # RIGHT - Always check
   def process_logic(slot_data, policy_message, worker_state):
       input_list = slot_data.get("input", [])
       if not input_list:
           return  # No data, exit gracefully

       data = input_list[0]
       value = data.get("value", "default")

**Prevention**

- ✅ Always use ``.get(key, [])`` for slot access
- ✅ Always check ``if list:`` before accessing
- ✅ Provide defaults for nested access: ``.get("key", "default")``

---

Pitfall 6: Blocking Operations in Thread Pool
----------------------------------------------

**The Pitfall**

Blocking operations in routine logic:

.. code-block:: python
   :emphasize-lines: 4

   # WRONG - Blocking call
   def process_logic(slot_data, policy_message, worker_state):
       result = requests.get("https://api.example.com")  # Blocks!
       self.emit("output", data=result)

**Why It Happens**

Routines execute in a thread pool. Blocking operations tie up threads,
reducing throughput.

**Symptoms**

- Poor performance under load
- Threads appear "stuck"
- Queue backups
- Timeout errors

**Solution**

Use async patterns or increase thread pool:

.. code-block:: python

   # RIGHT - Use async or increase pool
   import asyncio

   def process_logic(slot_data, policy_message, worker_state):
       # Option 1: Use async HTTP library
       loop = asyncio.new_event_loop()
       result = loop.run_until_complete(fetch_async(url))

       # Option 2: Increase thread pool size for blocking calls
       runtime = Runtime(thread_pool_size=50)  # More threads for blocking I/O

**Prevention**

- ✅ Use async libraries for I/O
- ✅ Increase thread pool for blocking operations
- ✅ Offload blocking work to separate processes
- ❌ Avoid blocking calls in logic when possible

---

Quick Reference Checklist
--------------------------

Before deploying a routine, verify:

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Check
     - Status
   * - No constructor parameters (except ``self``)
     - ☐
   * - Using ``set_config()`` for configuration
     - ☐
   * - Using ``WorkerState`` for execution state
     - ☐
   * - Activation policy set
     - ☐
   * - Correct logic signature
     - ☐
   * - Checking for empty slots
     - ☐
   * - No blocking operations (or handled)
     - ☐

Next Steps
----------

- :doc:`state_management` - State management pitfalls
- :doc:`concurrency` - Concurrency pitfalls
- :doc:`../tutorial/basics/understanding_routines` - Routine basics

.. seealso::

   :doc:`../api_reference/core/routine`
      Complete Routine API reference
