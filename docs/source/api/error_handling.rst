Error Handling
==============

Routilux provides flexible error handling with multiple strategies and
a clear priority system for error handlers.

Error Strategies
----------------

.. autoclass:: routilux.error_handler.ErrorStrategy
    :members:

.. autoclass:: routilux.error_handler.ErrorHandler
    :members:

Priority System
---------------

Error handlers are checked in the following order (first match wins):

1. **Routine-level handler** (set via :meth:`Routine.set_error_handler`)
2. **Flow-level handler** (set via :meth:`Flow.set_error_handler`)
3. **Default behavior** (STOP)

Example::

    from routilux import Flow, Routine
    from routilux.error_handler import ErrorHandler, ErrorStrategy

    flow = Flow("my_flow")

    # Flow-level handler: CONTINUE for all routines
    flow_handler = ErrorHandler(strategy=ErrorStrategy.CONTINUE)
    flow.set_error_handler(flow_handler)

    routine = Routine("my_routine")

    # Routine-level handler: STOP for this routine only
    # This TAKES PRIORITY over the flow-level handler
    routine_handler = ErrorHandler(strategy=ErrorStrategy.STOP)
    routine.set_error_handler(routine_handler)

    flow.add_routine(routine)

    # When routine errors, it will STOP (routine handler wins)
    job_state = flow.execute("my_routine")

Best Practices
--------------

1. **Set flow-level handler** for consistent behavior
2. **Override per routine** for special cases
3. **Use CONTINUE** for non-critical operations
4. **Use STOP** for critical workflows
5. **Use RETRY** for transient failures (network, timeouts)
6. **Use SKIP** for optional processing steps

Retry Configuration
-------------------

When using RETRY strategy, configure:

* ``max_retries``: Maximum retry attempts (default: 3)
* ``retry_delay``: Initial delay in seconds (default: 1.0)
* ``retry_backoff``: Exponential backoff multiplier (default: 2.0)

Delay calculation: ``retry_delay * (retry_backoff ** (attempt - 1))``

Example::

    handler = ErrorHandler(
        strategy=ErrorStrategy.RETRY,
        max_retries=5,
        retry_delay=0.5,
        retry_backoff=2.0
    )

    # Delays: 0.5s, 1.0s, 2.0s, 4.0s, 8.0s
