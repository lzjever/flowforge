Testing
=======

This document provides comprehensive testing information for routilux.

Test Organization
-----------------

Routilux tests are located in the ``tests/`` directory, testing the core
Routilux framework functionality.

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

Running Tests
-------------

Install Dependencies
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip install pytest pytest-cov pytest-mock

Run Tests
~~~~~~~~~

Run all tests:

.. code-block:: bash

   pytest tests/

Run a specific test file:

.. code-block:: bash

   pytest tests/test_routine.py

Run a specific test case:

.. code-block:: bash

   pytest tests/test_routine.py::TestRoutineBasic::test_create_routine

Generate Coverage Report
~~~~~~~~~~~~~~~~~~~~~~~~

Generate coverage report:

.. code-block:: bash

   pytest --cov=routilux --cov-report=html tests/

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

Test Coverage Statistics
------------------------

* **Core Tests**: 193 test cases
* **Total Test Cases**: 193+
* **Function Coverage**: Comprehensive
* **Boundary Cases**: Complete
* **Error Handling**: Complete

All core functionality has been tested and verified.

Test Configuration
------------------

The ``pytest.ini`` configuration file:

* Configures coverage reporting
* Sets up test markers (unit, integration, slow, persistence, resume)
* Excludes integration tests by default (use ``-m integration`` to run them)

Quick Reference
---------------

**Run All Tests**:

.. code-block:: bash

   pytest tests/

**Run Integration Tests**:

.. code-block:: bash

   pytest tests/ -m integration

**Run with Coverage**:

.. code-block:: bash

   pytest tests/ --cov=routilux --cov-report=html

For more details, see ``tests/README.md`` in the project root.
