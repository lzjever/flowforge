Testing
=======

This document provides comprehensive testing information for flowforge.

Test Organization
-----------------

FlowForge tests are organized into two separate categories:

1. **Core Tests**: Located in ``tests/`` directory, testing only the core
   FlowForge framework functionality.

2. **Builtin Routines Tests**: Located in ``flowforge/builtin_routines/*/tests/``
   directories, testing built-in routine implementations.

This separation ensures that:
* Core framework tests are independent of built-in routines
* Built-in routines can be tested and maintained independently
* Each built-in routine package is self-contained and portable

Core Test Structure
--------------------

Core tests are located in the ``tests/`` directory:

.. code-block:: text

   tests/
   ├── __init__.py                          # Test package initialization
   ├── conftest.py                          # pytest configuration and fixtures
   ├── README.md                            # Test documentation
   ├── test_routine.py                      # Routine class tests
   ├── test_slot.py                         # Slot tests
   ├── test_event.py                        # Event tests
   ├── test_connection.py                   # Connection tests
   ├── test_flow.py                         # Flow orchestration tests
   ├── test_job_state.py                    # JobState tests
   ├── test_persistence.py                  # Persistence tests
   ├── test_integration.py                  # Integration tests
   ├── test_resume.py                       # Resume functionality tests
   ├── test_aggregator_pattern.py           # Aggregation pattern tests
   ├── test_flow_comprehensive.py           # Comprehensive Flow tests
   ├── test_error_handler_comprehensive.py  # ErrorHandler tests
   ├── test_execution_tracker_comprehensive.py  # ExecutionTracker tests
   ├── test_connection_comprehensive.py     # Comprehensive Connection tests
   ├── test_slot_comprehensive.py          # Comprehensive Slot tests
   ├── test_event_comprehensive.py         # Comprehensive Event tests
   ├── test_serialization_utils.py          # Serialization utilities tests
   ├── test_concurrent_execution.py        # Concurrent execution tests
   └── test_utils.py                        # Utility function tests

Builtin Routines Test Structure
--------------------------------

Built-in routines tests are located in their respective sub-packages:

.. code-block:: text

   flowforge/builtin_routines/
   ├── text_processing/
   │   └── tests/
   │       └── test_text_processing.py      # Text processing routines tests
   ├── utils/
   │   └── tests/
   │       └── test_utils.py                # Utility routines tests
   ├── data_processing/
   │   └── tests/
   │       └── test_data_processing.py      # Data processing routines tests
   └── control_flow/
       └── tests/
           └── test_control_flow.py         # Control flow routines tests

Running Tests
-------------

Install Dependencies
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install pytest pytest-cov pytest-mock

Run Core Tests Only
~~~~~~~~~~~~~~~~~~~~

Run all core framework tests (excluding builtin_routines):

.. code-block:: bash

   pytest tests/

Run a specific core test file:

.. code-block:: bash

   pytest tests/test_routine.py

Run a specific test case:

.. code-block:: bash

   pytest tests/test_routine.py::TestRoutineBasic::test_create_routine

Run Builtin Routines Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run all builtin_routines tests using pytest:

.. code-block:: bash

   pytest flowforge/builtin_routines/ -v

Run tests for a specific builtin routine package:

.. code-block:: bash

   pytest flowforge/builtin_routines/text_processing/tests/ -v
   pytest flowforge/builtin_routines/utils/tests/ -v
   pytest flowforge/builtin_routines/data_processing/tests/ -v
   pytest flowforge/builtin_routines/control_flow/tests/ -v

Run a specific test file:

.. code-block:: bash

   pytest flowforge/builtin_routines/text_processing/tests/test_text_processing.py -v

Run All Tests
~~~~~~~~~~~~~

Run both core and builtin_routines tests:

.. code-block:: bash

   pytest tests/ flowforge/builtin_routines/ -v

Generate Coverage Report
~~~~~~~~~~~~~~~~~~~~~~~~

Core tests coverage:

.. code-block:: bash

   pytest --cov=flowforge --cov-report=html tests/

Builtin routines coverage:

.. code-block:: bash

   pytest flowforge/builtin_routines/ --cov=flowforge.builtin_routines --cov-report=html

All tests coverage:

.. code-block:: bash

   pytest --cov=flowforge --cov-report=html tests/ flowforge/builtin_routines/

Test Coverage
-------------

Core Framework Tests
~~~~~~~~~~~~~~~~~~~~

**Unit Tests** (193 test cases):

* ✅ Routine basic functionality
* ✅ Slot connection and data reception
* ✅ Event connection and triggering
* ✅ Connection parameter mapping
* ✅ Flow management and execution
* ✅ JobState state management
* ✅ ErrorHandler strategies
* ✅ ExecutionTracker functionality
* ✅ Serialization utilities
* ✅ Aggregation patterns

**Integration Tests**:

* ✅ Complete workflow execution
* ✅ Error handling workflows
* ✅ Parallel processing workflows
* ✅ Complex nested workflows
* ✅ Concurrent execution

**Persistence Tests**:

* ✅ Flow serialization/deserialization
* ✅ JobState serialization/deserialization
* ✅ Consistency verification

**Resume Tests**:

* ✅ Resume from intermediate state
* ✅ Resume from completed state
* ✅ Resume from error state
* ✅ State consistency verification

Builtin Routines Tests
~~~~~~~~~~~~~~~~~~~~~~~

All built-in routines have comprehensive test coverage with **50 test cases**:

* **Text Processing Routines**: 23 tests
  * TextClipper: 6 tests
  * TextRenderer: 6 tests
  * ResultExtractor: 11 tests

* **Utility Routines**: 9 tests
  * TimeProvider: 4 tests
  * DataFlattener: 5 tests

* **Data Processing Routines**: 9 tests
  * DataTransformer: 4 tests
  * DataValidator: 5 tests

* **Control Flow Routines**: 10 tests
  * ConditionalRouter: 10 tests

All tests pass with 100% success rate. Each routine package includes its own
test directory for easy maintenance and standalone usage.

Test Coverage Statistics
------------------------

* **Core Tests**: 193 test cases
* **Builtin Routines Tests**: 50 test cases
* **Total Test Cases**: 243+
* **Function Coverage**: Comprehensive
* **Boundary Cases**: Complete
* **Error Handling**: Complete

All core functionality and built-in routines have been tested and verified.

Test Configuration
------------------

The ``pytest.ini`` configuration file:

* Excludes ``builtin_routines`` from core test runs
* Configures coverage reporting
* Sets up test markers (unit, integration, slow, persistence, resume)

Quick Reference
---------------

**Run Core Tests Only**:

.. code-block:: bash

   pytest tests/

**Run Builtin Routines Tests Only**:

.. code-block:: bash

   pytest flowforge/builtin_routines/ -v

**Run All Tests**:

.. code-block:: bash

   pytest tests/ flowforge/builtin_routines/ -v

For more details, see ``tests/README.md`` in the project root.

