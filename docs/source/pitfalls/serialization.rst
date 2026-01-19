Serialization Pitfalls
======================

Routilux uses serialization for persistence and distributed execution. This section
covers common serialization-related mistakes.

.. note:: **Overview**

   | Pitfall | Severity | Frequency |
   |---------|----------|-----------|
   | Non-Serializable Objects | 🔴 Critical | High |
   | Circular References | 🔴 Critical | Low |
   | Lambda Functions | 🟡 High | Medium |
   | File Handles/Connections | 🔴 Critical | High |
   | Large State | 🟢 Medium | Medium |

---

Pitfall 1: Non-Serializable Objects
------------------------------------

**The Pitfall**

Storing non-serializable objects in routines:

.. code-block:: python
   :emphasize-lines: 5

   # WRONG - Storing non-serializable object
   class DatabaseRoutine(Routine):
       def __init__(self):
           super().__init__()
           import sqlite3
           self.connection = sqlite3.connect(":memory:")  # Not serializable!

**Why It Happens**

Developers try to store connection objects, file handles, or other resources
in instance variables or state.

**Symptoms**

- ``TypeError: Object of type X is not JSON serializable``
- ``SerializationError``
- State not persisting correctly
- Failures when saving/restoring flows

**Solution**

Store configuration, not objects:

.. code-block:: python

   # RIGHT - Store configuration string
   class DatabaseRoutine(Routine):
       def __init__(self):
           super().__init__()
           # Store connection config, not connection
           self.set_config(
               connection_string="sqlite:///tmp/db.sqlite3"
           )

       def query_logic(slot_data, policy_message, worker_state):
           # Create connection when needed
           conn_str = self.get_config("connection_string")
           conn = sqlite3.connect(conn_str)
           try:
               result = conn.execute("SELECT ...")
               return result.fetchall()
           finally:
               conn.close()

**Prevention**

- ✅ Only store JSON-serializable types
- ✅ Store connection strings, file paths
- ✅ Recreate resources from config
- ❌ Never store: connections, handles, sockets, locks

---

Pitfall 2: Circular References
-------------------------------

**The Pitfall**

Creating circular references in state:

.. code-block:: python

   # WRONG - Circular reference
   def logic(slot_data, policy_message, worker_state):
       parent = {"name": "parent"}
       child = {"name": "child", "parent": parent}
       parent["child"] = child  # Circular!

       worker_state.update_routine_state("data", {"obj": parent})

**Why It Happens**

Nested data structures can accidentally create circular references.

**Symptoms**

- ``RecursionError`` during serialization
- ``ValueError: Circular reference detected``
- JSON encoding failures

**Solution**

Avoid circular references:

.. code-block:: python

   # RIGHT - Use references instead of nesting
   def logic(slot_data, policy_message, worker_state):
       parent_id = "parent_123"
       child_id = "child_456"

       # Store IDs, not objects
       worker_state.update_routine_state("data", {
           "parent": {"id": parent_id, "name": "Parent"},
           "child": {"id": child_id, "name": "Child", "parent_id": parent_id}
       })

**Prevention**

- ✅ Use ID references instead of nesting
- ✅ Flatten data structures
- ✅ Use dictionaries instead of object graphs
- ❌ Avoid bidirectional links

---

Pitfall 3: Lambda Functions
----------------------------

**The Pitfall**

Using lambda functions with serialization:

.. code-block:: python

   # WRONG - Lambda can't be serialized
   from routilux.activation_policies import custom_policy

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           threshold = 10

           # Lambda won't serialize properly
           self.set_activation_policy(custom_policy(
               lambda slots, ws: slots["input"].get_unconsumed_count() > threshold
           ))

**Why It Happens**

Lambda functions capture closures and can't be serialized.

**Symptoms**

- ``PicklingError``
- ``AttributeError: Can't pickle local object``
- State not persisting

**Solution**

Use named functions:

.. code-block:: python

   # RIGHT - Named function
   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           self.set_config(threshold=10)

           # Named function works
           self.set_activation_policy(custom_policy(check_threshold))

   def check_threshold(slots, worker_state):
       from routilux.core import get_current_worker_state
       ws = get_current_worker_state()
       threshold = ws.get_routine_state("my_routine", {}).get("threshold", 10)
       return slots["input"].get_unconsumed_count() > threshold

**Prevention**

- ✅ Use named functions for policies
- ✅ Store config in ``_config``
- ✅ Pass parameters via config
- ❌ Avoid lambdas in serializable contexts

---

Pitfall 4: Large State
----------------------

**The Pitfall**

Accumulating large state that slows serialization:

.. code-block:: python

   # WRONG - Accumulating large state
   def collect_results(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("collector") or {}
       results = state.get("results", [])

       # Keeps growing!
       results.append(large_object)  # 1MB each

       worker_state.update_routine_state("collector", {
           "results": results  # Eventually: 1GB, 10GB, 100GB...
       })

**Why It Happens**

State grows unbounded, causing slow serialization and high memory usage.

**Symptoms**

- Slow save/load operations
- High memory usage
- Large state files
- Slow startup/shutdown

**Solution**

Implement bounds and cleanup:

.. code-block:: python

   # RIGHT - Bounded state with cleanup
   MAX_RESULTS = 1000

   def collect_results(slot_data, policy_message, worker_state):
       state = worker_state.get_routine_state("collector") or {}
       results = state.get("results", [])

       # Add new results
       results.append(new_result)

       # Trim to max size
       if len(results) > MAX_RESULTS:
           results = results[-MAX_RESULTS:]  # Keep most recent

       worker_state.update_routine_state("collector", {
           "results": results,
           "dropped_count": state.get("dropped_count", 0) +
                          (len(results) - MAX_RESULTS)
       })

**Prevention**

- ✅ Set maximum sizes for collections
   - ✅ Implement LRU eviction
- ✅ Periodic cleanup
- ✅ Stream to disk instead of memory
- ❌ Don't let state grow unbounded

---

Serialization Best Practices
-----------------------------

**DO ✅**:

- Store JSON-serializable types only: str, int, float, bool, list, dict, None
- Store connection strings, not connections
- Store file paths, not file handles
- Store IDs, not object references
- Set maximum sizes for collections
- Flatten nested structures
- Use named functions, not lambdas

**DON'T ❌**:

- Store connection objects, sockets, file handles
- Store thread locks, semaphores
- Store lambda functions or local functions
- Create circular references
- Let collections grow unbounded
- Store large binary data (use external storage)

**Serializable Types**:

.. code-block:: python

   # ✅ Serializable
   {
       "string": "hello",
       "number": 42,
       "float": 3.14,
       "bool": True,
       "none": None,
       "list": [1, 2, 3],
       "dict": {"nested": "value"},
       "timestamp": "2024-01-01T00:00:00"
   }

   # ❌ Not Serializable
   {
       "connection": sqlite3.connect(":memory:"),  # Connection object
       "file": open("data.txt"),  # File handle
       "lock": threading.Lock(),  # Lock object
       "lambda": lambda x: x * 2,  # Function
       "circular": {"parent": None}  # After setting circular reference
   }

---

Quick Reference: Serialization Checklist
----------------------------------------

Before deploying, verify all state is serializable:

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Check
     - Status
   * - Only JSON types in state
     - ☐
   * - No connection objects
     - ☐
   * - No file handles
     - ☐
   * - No lambda functions
     - ☐
   * - No circular references
     - ☐
   * - Collections have max sizes
     - ☐
   * - Test save/load cycle
     - ☐

Next Steps
----------

- :doc:`routine_design` - Routine design pitfalls
- :doc:`state_management` - State management pitfalls
- :doc:`../user_guide/serialization` - Serialization guide

.. seealso::

   :doc:`../api_reference/core/routine`
      Routine serialization API
