Error Handling API
==================

The error handling module provides strategies for handling errors in workflows.

Overview
--------

Routilux provides flexible error handling through:

* **ErrorHandler**: Centralized error handling for flows and routines
* **ErrorStrategy**: Pre-defined error handling strategies

Error Strategies
----------------

.. code-block:: python

    from routilux import ErrorStrategy, ErrorHandler

    # Create error handler with strategy
    handler = ErrorHandler(ErrorStrategy.LOG_AND_CONTINUE)

    # Apply to flow
    flow.set_error_handler(handler)

Available Strategies
~~~~~~~~~~~~~~~~~~~~

* ``ErrorStrategy.FAIL``: Stop execution on error
* ``ErrorStrategy.RETRY``: Retry failed operations
* ``ErrorStrategy.LOG``: Log error and continue
* ``ErrorStrategy.LOG_AND_CONTINUE``: Log error and continue with next operation

.. automodule:: routilux.core.error
   :members:
   :undoc-members:
   :show-inheritance:

ErrorHandler
------------

.. autoclass:: routilux.core.error.ErrorHandler
   :members:
   :show-inheritance:

ErrorStrategy
-------------

.. autoclass:: routilux.core.error.ErrorStrategy
   :members:
   :show-inheritance:
