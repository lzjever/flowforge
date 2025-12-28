Serialization
=============

routilux provides full serialization support for persistence and state recovery.

Serializing Objects
-------------------

All core classes support serialization:

.. code-block:: python

   # Serialize a flow
   data = flow.serialize()
   
   # Serialize a routine
   data = routine.serialize()
   
   # Serialize a job state
   data = job_state.serialize()

   # Serialize an error handler
   data = error_handler.serialize()

Deserializing Objects
---------------------

Deserialize objects:

.. code-block:: python

   # Deserialize a flow
   flow = Flow()
   flow.deserialize(data)
   
   # Deserialize a routine
   routine = Routine()
   routine.deserialize(data)
   
   # Deserialize a job state
   job_state = JobState()
   job_state.deserialize(data)
   
   # Deserialize an error handler
   error_handler = ErrorHandler()
   error_handler.deserialize(data)

Saving to JSON
--------------

Save serialized data to JSON:

.. code-block:: python

   import json
   
   data = flow.serialize()
   with open("flow.json", "w") as f:
       json.dump(data, f, indent=2)

Loading from JSON
-----------------

Load from JSON:

.. code-block:: python

   import json
   
   with open("flow.json", "r") as f:
       data = json.load(f)
   
   flow = Flow()
   flow.deserialize(data)

Serializable Fields
-------------------

Classes register fields for serialization:

.. code-block:: python

   self.add_serializable_fields(["field1", "field2", "field3"])

Only registered fields are serialized. Complex objects (lists, dicts, other Serializable objects) are automatically handled.

Serialization Validation
-------------------------

Before serializing a Flow, the system automatically validates that all
Serializable objects (routines, connections, slots, events, etc.) can be
constructed without arguments. This ensures that deserialization will succeed.

**Why This Matters**:

When deserializing, the system needs to create new instances of all Serializable
objects. It does this by calling ``Class()`` with no arguments. If a class
requires constructor parameters, deserialization will fail.

**Automatic Validation**:

When you call ``flow.serialize()``, the system:

1. Recursively traverses all Serializable objects in the Flow
2. Checks that each object's class can be instantiated without arguments
3. Raises a clear error if any object fails validation

**Example Error**:

.. code-block:: python

   # ❌ This will fail during serialization
   class BadRoutine(Routine):
       def __init__(self, required_param):
           super().__init__()
           self.param = required_param
   
   flow = Flow()
   routine = BadRoutine("value")  # This works
   flow.add_routine(routine, "bad_routine")
   
   # This will raise TypeError with clear error message
   data = flow.serialize()
   # TypeError: Routine 'bad_routine' (BadRoutine) cannot be serialized:
   # BadRoutine cannot be deserialized because its __init__ method requires
   # parameters: required_param
   # Serializable classes must support initialization with no arguments.
   # For Routine subclasses, use _config dictionary instead of constructor parameters.

**Correct Pattern**:

.. code-block:: python

   # ✅ Correct: Use _config dictionary
   class GoodRoutine(Routine):
       def __init__(self):
           super().__init__()
           # Configuration is set after creation
       
       def configure(self, param1, param2):
           self.set_config(param1=param1, param2=param2)
   
   flow = Flow()
   routine = GoodRoutine()
   routine.configure(param1="value1", param2="value2")
   flow.add_routine(routine, "good_routine")
   
   # This will succeed
   data = flow.serialize()

**What Gets Validated**:

* All routines in the Flow
* All connections
* All slots and events within routines
* All nested Serializable objects
* Error handlers, job states, and other Serializable fields

**Error Messages**:

The validation provides detailed error messages that include:

* Which object failed (routine ID, connection index, field name, etc.)
* Which class has the problem
* What parameters are required
* How to fix the issue

This allows you to catch serialization issues early, before attempting to
save or transfer the Flow.

Constructor Requirements
-------------------------

**Critical Rule**: All Serializable classes (including Routine subclasses)
must support initialization with no arguments.

**For Routine Subclasses**:

* ❌ **Don't**: Accept constructor parameters
* ✅ **Do**: Use ``_config`` dictionary for configuration

**Example**:

.. code-block:: python

   # ❌ Wrong: Constructor with parameters
   class MyRoutine(Routine):
       def __init__(self, max_items: int, timeout: float):
           super().__init__()
           self.max_items = max_items
           self.timeout = timeout
   
   # ✅ Correct: No constructor parameters, use _config
   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           # Configuration is set after creation
       
       def setup(self, max_items: int, timeout: float):
           self.set_config(max_items=max_items, timeout=timeout)
   
   # Usage
   routine = MyRoutine()
   routine.setup(max_items=10, timeout=5.0)
   flow.add_routine(routine, "my_routine")

**Why This Constraint Exists**:

During deserialization, the system needs to:

1. Load the class from the registry
2. Create an instance: ``routine = RoutineClass()``
3. Restore state: ``routine.deserialize(data)``

If the class requires constructor parameters, step 2 will fail because the
system doesn't know what values to pass.

**Validation Timing**:

* **At Class Definition**: The ``@register_serializable`` decorator checks
  the class definition when it's first loaded
* **At Serialization**: ``flow.serialize()`` validates all objects in the
  Flow before serialization, providing early error detection

This two-stage validation ensures that:

1. Classes are correctly defined from the start
2. Runtime issues are caught before serialization

Special Handling
----------------

Some classes have special serialization behavior:

* **ErrorHandler**: The ``ErrorStrategy`` enum is automatically converted to/from strings during serialization/deserialization.

Handler Method Validation
--------------------------

When serializing slot handlers and merge strategies, the system validates that
methods belong to the routine being serialized. This ensures cross-process
serialization safety.

**Why This Matters**:

When serialized data is transferred to another process (e.g., for distributed
execution), only methods of the serialized routine itself can be properly
restored. Methods from other routines cannot be deserialized because their
object instances don't exist in the new process.

**Validation Rules**:

* ✅ **Allowed**: Methods of the routine being serialized
* ✅ **Allowed**: Module-level functions (can be imported in any process)
* ✅ **Allowed**: Builtin functions
* ❌ **Not Allowed**: Methods from other routine instances

**Example - Correct Usage**:

.. code-block:: python

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           # ✅ Correct: Use method from this routine
           self.input_slot = self.define_slot("input", handler=self.process_data)
       
       def process_data(self, data):
           return {"processed": data}

**Example - Incorrect Usage**:

.. code-block:: python

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           other_routine = OtherRoutine()
           # ❌ Wrong: Using method from another routine
           # This will raise ValueError during serialization
           self.input_slot = self.define_slot("input", handler=other_routine.process)

**Error Message**:

If you try to serialize a method from another routine, you'll get a clear error:

.. code-block:: python

   ValueError: Cannot serialize method 'process' from OtherRoutine[other_id]. 
   Only methods of the serialized object itself (MyRoutine[my_id]) 
   can be serialized for cross-process execution.

**What Gets Validated**:

* Slot handlers (in ``Routine.define_slot()``)
* Merge strategies (if they are callable methods)
* Conditional router conditions (if they are callable methods)

**Note**: Functions (not methods) are always allowed because they can be
imported by module name in any process.

