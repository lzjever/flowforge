Working with Routines
=====================

Routines are the core building blocks of flowforge. This guide explains how to create and use routines.

Creating a Routine
------------------

To create a routine, inherit from ``Routine``:

.. code-block:: python

   from flowforge import Routine

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()
           # Define slots and events here

Defining Slots
--------------

Slots are input mechanisms for routines. Define a slot with a handler function:

.. code-block:: python

   def process_input(self, data):
       # Process the input data
       pass

   self.input_slot = self.define_slot("input", handler=process_input)

You can also specify a merge strategy for slots that receive data from multiple events:

.. code-block:: python

   self.input_slot = self.define_slot(
       "input",
       handler=process_input,
       merge_strategy="append"  # or "override", "merge"
   )

Defining Events
---------------

Events are output mechanisms for routines. Define an event with output parameters:

.. code-block:: python

   self.output_event = self.define_event("output", ["result", "status"])

Emitting Events
---------------

Emit events to trigger connected slots:

.. code-block:: python

   self.emit("output", result="success", status="completed")

When emitting, you can optionally pass a Flow instance for context:

.. code-block:: python

   self.emit("output", flow=current_flow, result="success")

Statistics
----------

Track routine statistics using the ``_stats`` dictionary:

.. code-block:: python

   self._stats["processed_count"] = self._stats.get("processed_count", 0) + 1

Or use the convenient ``_track_operation()`` method for consistent tracking:

.. code-block:: python

   def process_data(self, data):
       try:
           # Process the data
           result = self.process(data)
           # Track successful operation
           self._track_operation("processing", success=True, items_processed=1)
           return result
       except Exception as e:
           # Track failed operation
           self._track_operation("processing", success=False, error=str(e))
           raise

Retrieve statistics:

.. code-block:: python

   stats = routine.stats()
   print(stats)  # {"processed_count": 1, "total_processing": 1, "successful_processing": 1, ...}

Getting Slots and Events
------------------------

Retrieve slots and events by name:

.. code-block:: python

   slot = routine.get_slot("input")
   event = routine.get_event("output")

Extracting Input Data
---------------------

When handling slot inputs, you can use the ``_extract_input_data()`` helper method
to simplify data extraction from various input patterns:

.. code-block:: python

   def process_input(self, data=None, **kwargs):
       # Extract data using the helper method
       # Handles: direct parameter, 'data' key, single value, or multiple values
       extracted_data = self._extract_input_data(data, **kwargs)
       
       # Process the extracted data
       result = self.process(extracted_data)
       self.emit("output", result=result)

This method handles various input patterns:
- Direct parameter: ``_extract_input_data("text")`` → ``"text"``
- 'data' key: ``_extract_input_data(None, data="text")`` → ``"text"``
- Single value: ``_extract_input_data(None, text="value")`` → ``"value"``
- Multiple values: ``_extract_input_data(None, a=1, b=2)`` → ``{"a": 1, "b": 2}``

Executing Routines
------------------

Routines are executed by calling them:

.. code-block:: python

   routine(data="test")

Or through a Flow's execute method (see :doc:`flows`).

Multiple Slots Behavior
------------------------

A routine can have multiple slots, each connected to different upstream routines.
When an upstream routine emits data, it triggers the handler of the connected slot.

**Important**: Each slot has its own handler and is triggered independently.

**Example:**

.. code-block:: python

   class TargetRoutine(Routine):
       def __init__(self):
           super().__init__()
           # Define three slots, each with its own handler
           self.slot1 = self.define_slot("input1", handler=self._handle_input1)
           self.slot2 = self.define_slot("input2", handler=self._handle_input2)
           self.slot3 = self.define_slot("input3", handler=self._handle_input3)
       
       def _handle_input1(self, data1=None, **kwargs):
           # This handler is called when slot1 receives data
           pass
       
       def _handle_input2(self, data2=None, **kwargs):
           # This handler is called when slot2 receives data
           pass
       
       def _handle_input3(self, data3=None, **kwargs):
           # This handler is called when slot3 receives data
           pass

If three upstream routines each emit once:
- **Source1** emits → **slot1** receives → **handler1** is called (1st time)
- **Source2** emits → **slot2** receives → **handler2** is called (2nd time)
- **Source3** emits → **slot3** receives → **handler3** is called (3rd time)

**Result**: The target routine's handlers are called **3 times** (once per slot).

**Multiple Emissions**:

If each upstream routine emits multiple times, the downstream routine is called
for each emission:

.. code-block:: python

   # Each source emits 3 times
   source1()  # Emits 3 times → slot1 handler called 3 times
   source2()  # Emits 3 times → slot2 handler called 3 times
   source3()  # Emits 3 times → slot3 handler called 3 times
   
   # Total: 3 sources × 3 emissions = 9 handler calls

Each slot operates independently:
* Each slot maintains its own ``_data`` state
* Each slot's merge_strategy applies independently
* Each slot's handler is called immediately when data is received
* Each emission triggers the handler once
* Handlers can be different functions or the same function

**Concurrent Execution Mode**:

The same behavior applies in concurrent execution mode. When using
``execution_strategy="concurrent"``, each slot's handler is still called
once for each emission it receives, but handlers may execute concurrently
in different threads.

.. code-block:: python

   # Create concurrent flow
   flow = Flow(execution_strategy="concurrent", max_workers=5)
   
   # Same connections as before
   flow.connect(source1_id, "output", target_id, "input1")
   flow.connect(source2_id, "output", target_id, "input2")
   flow.connect(source3_id, "output", target_id, "input3")
   
   # Each source emits 3 times
   flow.execute(source1_id)  # Emits 3 times → slot1 handler called 3 times
   flow.execute(source2_id)  # Emits 3 times → slot2 handler called 3 times
   flow.execute(source3_id)  # Emits 3 times → slot3 handler called 3 times
   
   # Wait for all concurrent tasks to complete
   flow.wait_for_completion(timeout=10.0)
   
   # Total: Still 9 handler calls (3 sources × 3 emissions)
   # Note: In concurrent mode, calls may be interleaved across threads

**Important Notes for Concurrent Mode**:
* Each slot's handler is called in a separate thread when data is received
* Handler calls may be interleaved (not necessarily in order)
* Use thread-safe operations if handlers share state
* The total number of calls remains the same as sequential mode
* Always call ``wait_for_completion()`` to ensure all handlers finish
* Always call ``shutdown(wait=True)`` when done to clean up resources

