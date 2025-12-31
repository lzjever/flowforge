Execution Completion API
========================

This module provides a robust, systematic approach to waiting for flow execution
to complete, handling race conditions, long-running tasks, and edge cases.

.. automodule:: routilux.flow.completion
   :members:
   :undoc-members:
   :show-inheritance:

ExecutionCompletionChecker
---------------------------

The ``ExecutionCompletionChecker`` class provides a systematic mechanism to check
if flow execution has completed, handling race conditions and edge cases properly.

**Key Features:**

- Multiple verification passes to avoid race conditions
- Configurable stability requirements
- Support for long-running tasks
- Proper handling of paused/cancelled states

**Example:**

.. code-block:: python

   from routilux.flow.completion import ExecutionCompletionChecker
   
   checker = ExecutionCompletionChecker(
       flow=flow,
       job_state=job_state,
       stability_checks=5,
       check_interval=0.1,
       stability_delay=0.05
   )
   
   if checker.check_with_stability():
       print("Execution is complete")

wait_for_execution_completion
-----------------------------

The ``wait_for_execution_completion()`` function provides a robust, systematic way
to wait for flow execution to complete.

**Features:**

- **Completion Detection**: Checks if execution is complete by verifying:
  - Task queue is empty (no pending tasks)
  - No active tasks (all running tasks finished)
  - This works even if ``job_state.status`` is still ``"running"``
- **Stability Verification**: Performs multiple consecutive checks to avoid race conditions
  where tasks might be enqueued between checks
- **Timeout Safety**: The timeout parameter serves as a safety limit. If execution doesn't
  complete within the timeout, the function returns ``False`` and the caller should handle
  the timeout (e.g., force stop the event loop)
- **Long-running Tasks**: Supports long-running tasks (e.g., LLM calls) with configurable
  timeout
- **Event Loop Management**: Handles edge cases where event loop might exit prematurely
- **Progress Monitoring**: Optional progress callback for monitoring execution status

**Example:**

.. code-block:: python

   from routilux.flow.completion import wait_for_execution_completion
   
   job_state = flow.execute(entry_routine_id="routine1")
   
   def progress_callback(queue_size, active_count, status):
       print(f"Queue: {queue_size}, Active: {active_count}, Status: {status}")
   
   completed = wait_for_execution_completion(
       flow=flow,
       job_state=job_state,
       timeout=300.0,
       progress_callback=progress_callback
   )
   
   if completed:
       print("Execution completed successfully")
   else:
       print("Execution timed out")

ensure_event_loop_running
--------------------------

The ``ensure_event_loop_running()`` function ensures the event loop is running,
restarting it if needed when there are tasks in the queue.

**Example:**

.. code-block:: python

   from routilux.flow.completion import ensure_event_loop_running
   
   # Check and restart event loop if needed
   if ensure_event_loop_running(flow):
       print("Event loop is running")

