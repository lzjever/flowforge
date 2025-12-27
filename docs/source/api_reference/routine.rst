Routine API
============

The ``Routine`` class is the base class for all routines in FlowForge. It provides
core functionality for slots, events, statistics tracking, and configuration management.

Key Features
------------

* **Input Data Extraction**: Use ``_extract_input_data()`` to simplify slot handler data extraction
* **Operation Tracking**: Use ``_track_operation()`` for consistent statistics tracking
* **Configuration Management**: Store configuration in ``_config`` dictionary
* **Statistics Tracking**: Track execution metrics in ``_stats`` dictionary

.. automodule:: flowforge.routine
   :members:
   :undoc-members:
   :show-inheritance:

Helper Methods
--------------

The ``Routine`` class provides several helper methods for common operations:

* ``_extract_input_data(data, **kwargs)``: Extract and normalize input data from slot parameters
* ``_track_operation(operation_name, success=True, **metadata)``: Track operation statistics with metadata

These methods are available to all routines that inherit from ``Routine``.

