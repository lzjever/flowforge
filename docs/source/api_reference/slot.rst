Slot API
========

The ``Slot`` class represents input queues for receiving data.

Overview
--------

A ``Slot`` is a queue-based input buffer that:

* Receives data from connected events
* Stores data with timestamps
* Supports many-to-one connections (multiple events → one slot)
* Provides watermark-based auto-shrink
* Thread-safe operations

Basic Usage
-----------

Slots are typically created via ``Routine.add_slot()``:

.. code-block:: python

    class MyRoutine(Routine):
        def __init__(self):
            super().__init__()
            # Add a slot with custom queue size
            self.add_slot("input", max_queue_length=500, watermark=0.8)

.. automodule:: routilux.core.slot
   :members:
   :undoc-members:
   :show-inheritance:

Key Methods
-----------

.. automethod:: routilux.core.slot.Slot.__init__
   :no-index:
.. automethod:: routilux.core.slot.Slot.enqueue
   :no-index:
.. automethod:: routilux.core.slot.Slot.consume_all
   :no-index:
.. automethod:: routilux.core.slot.Slot.consume_all_new
   :no-index:
.. automethod:: routilux.core.slot.Slot.consume_one_new
   :no-index:
.. automethod:: routilux.core.slot.Slot.consume_latest_and_mark_all_consumed

Query Methods
~~~~~~~~~~~~~

.. automethod:: routilux.core.slot.Slot.peek_all_new
.. automethod:: routilux.core.slot.Slot.peek_one_new
.. automethod:: routilux.core.slot.Slot.peek_latest

Status Methods
~~~~~~~~~~~~~~

.. automethod:: routilux.core.slot.Slot.get_unconsumed_count
.. automethod:: routilux.core.slot.Slot.get_total_count
.. automethod:: routilux.core.slot.Slot.get_queue_state
.. automethod:: routilux.core.slot.Slot.get_queue_status

Exceptions
----------

.. autoclass:: routilux.core.slot.SlotQueueFullError
   :members:
   :show-inheritance:
