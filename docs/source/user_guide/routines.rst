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
--------------

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

