Design Optimization
===================

This document describes the design optimization for pause/resume/cancel functionality.

Optimization Goals
------------------

Optimize the design of pause/resume/cancel methods to clarify responsibility separation, avoid interface duplication, and reduce user confusion.

Design Principles
-----------------

Separation of Concerns
~~~~~~~~~~~~~~~~~~~~~~

1. **JobState (Data Model Layer)**
   * Responsibility: State storage and queries
   * Provides: State fields, query methods, internal state update methods (``_set_*``)
   * Does NOT provide: Public execution control methods (pause/resume/cancel)

2. **Flow (Control Layer)**
   * Responsibility: Execution control and state updates
   * Provides: ``pause()``, ``resume()``, ``cancel()`` and other execution control methods
   * Calls: JobState's internal methods to update state

Optimized Design
----------------

JobState Class
~~~~~~~~~~~~~~

.. code-block:: python

   class JobState:
       # State fields
       status: str
       pause_points: List[Dict]
       
       # Query methods (public)
       def get_routine_state(self, routine_id: str) -> Dict
       def get_execution_history(self, routine_id: Optional[str] = None) -> List
       
       # Internal state update methods (private, called by Flow)
       def _set_paused(self, reason: str, checkpoint: Optional[Dict] = None) -> None
       def _set_running(self) -> None
       def _set_cancelled(self, reason: str = "") -> None

Flow Class
~~~~~~~~~~

.. code-block:: python

   class Flow:
       # Execution control methods (public, main entry points)
       def pause(self, reason: str = "", checkpoint: Optional[Dict] = None) -> None
       def resume(self, job_state: Optional[JobState] = None) -> JobState
       def cancel(self, reason: str = "") -> None

Usage Guidelines
----------------

Correct Usage
~~~~~~~~~~~~~

**Execution Control - Through Flow:**

.. code-block:: python

   # Pause execution
   flow.pause(reason="User requested pause")
   
   # Resume execution
   flow.resume(job_state)
   
   # Cancel execution
   flow.cancel(reason="User cancelled")

**State Queries - Through JobState:**

.. code-block:: python

   # Query status
   status = job_state.status
   
   # Query routine state
   routine_state = job_state.get_routine_state("routine1")
   
   # Query execution history
   history = job_state.get_execution_history()

Design Benefits
---------------

1. **Clear Responsibility**: Each class has a single, clear responsibility
2. **No Interface Duplication**: Execution control methods only exist in Flow
3. **Better Encapsulation**: Internal state update methods are private
4. **Easier to Use**: Users have a single, clear entry point for execution control
5. **Better Maintainability**: Changes to execution control logic only affect Flow

