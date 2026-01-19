Understanding Slots and Events
===============================

Slots and events are how Routilux routines communicate with each other. **Slots**
receive data (input), and **events** send data (output). Understanding how they
work together is essential for building effective workflows.

.. note:: **What You'll Learn**

   - How slots receive and queue data
   - How events transmit data to connected slots
   - The one-way data flow pattern
   - Queue management and backpressure
   - Parameter mapping between events and slots

.. note:: **Prerequisites**

   - :doc:`understanding_routines` - Understand Routines first

The Data Flow Model
-------------------

Routilux uses a **one-way data flow** model:

.. code-block:: text

   ┌──────────────┐ emit()   ┌─────────────────────────────────┐
   │   Routine A  │──────────▶│ Event: "result"                 │
   │              │           │  • data                         │
   │              │           │  • metadata                     │
   └──────────────┘           └────────────┬────────────────────┘
                                          │
                                          │ Connection
                                          │ (routes data)
                                          ▼
                              ┌─────────────────────────────────┐
                              │ Slot: "input"                    │
                              │  • Queue (FIFO)                  │
                              │  • max_queue_length: 1000       │
                              └────────────┬────────────────────┘
                                           │
                                           │ consume()
                                           ▼
                              ┌─────────────────────────────────┐
                              │   Routine B                      │
                              │   Logic processes data           │
                              └─────────────────────────────────┘

**Key Characteristics**:

1. **One-way flow**: Events → Slots, never the reverse
2. **Queue-based**: Slots buffer incoming data in FIFO queues
3. **Decoupled**: Routines don't know who they're connected to
4. **Scalable**: One event can connect to multiple slots (fan-out)

Understanding Slots
-------------------

A **Slot** is an input mechanism that:

- Receives data from connected events
- Queues data in a FIFO (First-In-First-Out) buffer
- Tracks consumed vs. unconsumed data
- Can trigger routine activation

.. code-block:: python

   from routilux import Routine

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()

           # Basic slot with defaults
           self.add_slot("input")

           # Slot with custom queue size
           self.add_slot("data", max_queue_length=5000)

           # Slot with custom queue and watermark
           self.add_slot("items",
                        max_queue_length=10000,
                        watermark=0.9)  # Auto-shrink at 90%

**Slot Parameters**:

- ``name``: Unique slot identifier within the routine
- ``max_queue_length``: Maximum items in queue (default: 1000)
- ``watermark``: Auto-shrink threshold (default: 0.8 = 80%)

.. note:: **Watermark Behavior**

   When ``watermark=0.8`` and the queue has 1000 items consumed but only 200
   unconsumed remaining (20%), the queue capacity shrinks to 250 items. This
   helps manage memory automatically.

**Slot Data Structure**:

When data arrives at a slot, it's stored as a dictionary:

.. code-block:: python

   # Sending data via runtime.post()
   runtime.post("my_flow", "routine1", "input", {
       "name": "Alice",
       "age": 30,
       "city": "NYC"
   })

   # Inside the receiving routine's logic
   def my_logic(slot_data, policy_message, worker_state):
       # slot_data structure:
       # {
       #     "input": [
       #         {"name": "Alice", "age": 30, "city": "NYC"}
       #     ]
       # }

       input_list = slot_data.get("input", [])
       if input_list:
           first_item = input_list[0]
           name = first_item.get("name", "Unknown")
           print(f"Received: {name}")

.. warning:: **Pitfall: Slot Queue Full**

   When a slot's queue reaches ``max_queue_length``, new data is rejected
   and raises ``SlotQueueFullError``.

   **Solution**: Increase queue size or process faster:

   .. code-block:: python

      # For high-volume data
      self.add_slot("stream", max_queue_length=100000)

Understanding Events
--------------------

An **Event** is an output mechanism that:

- Sends data to connected slots
- Can connect to multiple slots (fan-out)
- Defines the data structure via parameter names

.. code-block:: python

   from routilux import Routine

   class MyRoutine(Routine):
       def __init__(self):
           super().__init__()

           # Event with parameter names (for documentation)
           self.add_event("result", ["value", "status", "timestamp"])

           def my_logic(slot_data, policy_message, worker_state):
               # Emit the event
               self.emit("result",
                        value=42,
                        status="success",
                        timestamp="2024-01-01T00:00:00")

           self.set_logic(my_logic)
           self.set_activation_policy(immediate_policy())

**Event Parameters**:

- ``name``: Unique event identifier within the routine
- ``output_params``: List of parameter names (for documentation/API)

.. tip:: **Event Parameter Names**

   Always specify parameter names in ``add_event()``. They:
   - Serve as inline documentation
   - Enable automatic API generation
   - Help IDEs with autocomplete
   - Make the data structure explicit

   .. code-block:: python

      # Good - Explicit parameters
      self.add_event("user_created", ["user_id", "username", "email"])

      # Acceptable - No parameters documented
      self.add_event("generic_event")

**Emitting Events**:

.. code-block:: python

   # Simple emit
   self.emit("output", data="Hello")

   # Multiple parameters
   self.emit("result", value=100, status="ok")

   # Complex data
   self.emit("json_data", payload={
       "nested": {"data": "structure"},
       "list": [1, 2, 3]
   })

.. danger:: **Event Name Must Exist**

   Emitting a non-existent event raises ``ValueError``:

   .. code-block:: python

      self.add_event("output")
      self.emit("output", data=123)     # OK
      self.emit("unknown", data=123)    # ValueError!

Connecting Events to Slots
---------------------------

Connections are made at the **Flow** level, not between routines directly:

.. code-block:: python

   from routilux import Flow, Routine
   from routilux.activation_policies import immediate_policy

   class Source(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("data", ["value"])

           def generate(slot_data, policy_message, worker_state):
               self.emit("data", value=42)

           self.set_logic(generate)
           self.set_activation_policy(immediate_policy())

   class Destination(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("result", ["received"])

           def receive(slot_data, policy_message, worker_state):
               data_list = slot_data.get("input", [])
               if data_list:
                   value = data_list[0].get("value", 0)
                   print(f"Received: {value}")
                   self.emit("result", received=value)

           self.set_logic(receive)
           self.set_activation_policy(immediate_policy())

   # Create flow and connect
   flow = Flow("data_pipeline")
   flow.add_routine(Source(), "source")
   flow.add_routine(Destination(), "dest")

   # Connect: source's "data" event → dest's "input" slot
   flow.connect("source", "data", "dest", "input")

**Connection Syntax**:

.. code-block:: python

   flow.connect(
       "source_routine_id",  # Routine emitting the event
       "event_name",         # Event name
       "dest_routine_id",    # Routine receiving the data
       "slot_name"           # Slot name
   )

Fan-Out: One Event to Multiple Slots
-------------------------------------

A single event can connect to multiple slots, creating a fan-out pattern:

.. code-block:: python
   :linenos:

   from routilux import Flow, Routine
   from routilux.activation_policies import immediate_policy

   class Broadcaster(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("news", ["headline"])

           def broadcast(slot_data, policy_message, worker_state):
               self.emit("news", headline="Breaking: Routilux Released!")

           self.set_logic(broadcast)
           self.set_activation_policy(immediate_policy())

   class Subscriber(Routine):
       def __init__(self, name):
           super().__init__()
           self.add_slot("updates")
           self.add_event("ack", ["subscriber", "received"])

           # Store name in config (NOT constructor parameter!)
           self.set_config(subscriber_name=name)

           def receive(slot_data, policy_message, worker_state):
               data_list = slot_data.get("updates", [])
               if data_list:
                   headline = data_list[0].get("headline", "")
                   name = self.get_config("subscriber_name")
                   print(f"{name} received: {headline}")
                   self.emit("ack", subscriber=name, received=headline)

           self.set_logic(receive)
           self.set_activation_policy(immediate_policy())

   # Create flow
   flow = Flow("news_broadcast")

   # One broadcaster, multiple subscribers
   flow.add_routine(Broadcaster(), "broadcaster")
   flow.add_routine(Subscriber("Alice"), "alice")
   flow.add_routine(Subscriber("Bob"), "bob")
   flow.add_routine(Subscriber("Charlie"), "charlie")

   # Fan-out: broadcaster → all subscribers
   flow.connect("broadcaster", "news", "alice", "updates")
   flow.connect("broadcaster", "news", "bob", "updates")
   flow.connect("broadcaster", "news", "charlie", "updates")

.. code-block:: text

   Diagram:
                        ┌─────────────┐
                        │ Broadcaster │
                        │             │
                        │ emit("news")│
                        └──────┬──────┘
                               │
               ┌───────────────┼───────────────┐
               │               │               │
               ▼               ▼               ▼
         ┌──────────┐    ┌──────────┐    ┌──────────┐
         │  Alice   │    │   Bob    │    │ Charlie  │
         └──────────┘    └──────────┘    └──────────┘

.. tip:: **Fan-Out Use Cases**

   - **Broadcasting**: Send the same data to multiple processors
   - **Parallel Processing**: Route data to concurrent workers
   - **Notification**: Alert multiple subscribers simultaneously
   - **Redundancy**: Send to backup processors

Fan-In: Multiple Events to One Slot
-----------------------------------

Multiple events can connect to a single slot, creating a fan-in pattern:

.. code-block:: python
   :linenos:

   class Producer(Routine):
       def __init__(self, id):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("item", ["producer_id", "value"])
           self.set_config(producer_id=id)

           def produce(slot_data, policy_message, worker_state):
               import random
               value = random.randint(1, 100)
               pid = self.get_config("producer_id")
               print(f"Producer {pid} generated: {value}")
               self.emit("item", producer_id=pid, value=value)

           self.set_logic(produce)
           self.set_activation_policy(immediate_policy())

   class Aggregator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")
           self.add_event("summary", ["count", "total"])

           def aggregate(slot_data, policy_message, worker_state):
               items_list = slot_data.get("items", [])
               count = len(items_list)
               total = sum(item.get("value", 0) for item in items_list)
               print(f"Aggregated {count} items, total: {total}")
               self.emit("summary", count=count, total=total)

           self.set_logic(aggregate)
           self.set_activation_policy(batch_size_policy(5))

   # Fan-in: multiple producers → single aggregator
   flow = Flow("multi_producer")

   flow.add_routine(Producer(1), "producer1")
   flow.add_routine(Producer(2), "producer2")
   flow.add_routine(Producer(3), "producer3")
   flow.add_routine(Aggregator(), "aggregator")

   # All producers connect to the same slot
   flow.connect("producer1", "item", "aggregator", "items")
   flow.connect("producer2", "item", "aggregator", "items")
   flow.connect("producer3", "item", "aggregator", "items")

.. code-block:: text

   Diagram:
      ┌──────────┐
      │Producer 1│───┐
      └──────────┘   │
                     ├──▶┌────────────┐
      ┌──────────┐   │   │Aggregator  │
      │Producer 2│───┤   │ Slot: items│
      └──────────┘   │   └────────────┘
                     │
      ┌──────────┐   │
      │Producer 3│───┘
      └──────────┘

.. warning:: **Fan-In Considerations**

   - Slots maintain **order** by arrival time
   - Data from different sources mixes in the queue
   - Use ``batch_size_policy()`` to control aggregation
   - Consider adding source identifiers in event data

Parameter Mapping
-----------------

Events and slots don't need to have matching parameters. The entire event
payload is delivered to the slot:

.. code-block:: python

   # Source routine emits
   self.emit("user_data",
            user_id=123,
            username="alice",
            email="alice@example.com",
            age=30,
            city="NYC")

   # Destination slot receives ALL data
   def process_logic(slot_data, policy_message, worker_state):
       data_list = slot_data.get("input", [])
       if data_list:
           item = data_list[0]
           # All fields are available
           user_id = item.get("user_id")
           username = item.get("username")
           email = item.get("email")
           age = item.get("age")
           city = item.get("city")

.. tip:: **Design for Partial Consumption**

   Receiving routines don't have to use all emitted data:

   .. code-block:: python

      # Emits lots of data
      self.emit("detailed", id=1, name="X", value=100, meta={...})

      # Consumer only uses what it needs
      def consumer_logic(slot_data, policy_message, worker_state):
          data = slot_data.get("input", [{}])[0]
          name = data.get("name")  # Only uses 'name'

Queue Management
----------------

Slots manage queues automatically, but you should understand the behavior:

**Queue States**:

1. **Empty**: No data available
2. **Available**: Unconsumed data ready
3. **Full**: Reached max_queue_length

**Queue Operations**:

.. code-block:: python

   slot = routine.get_slot("my_slot")

   # Check queue size
   unconsumed_count = slot.get_unconsumed_count()
   consumed_count = slot.get_consumed_count()

   # Manual consumption (rarely needed)
   item = slot.consume_one_new()  # Get one item
   items = slot.consume_all_new()  # Get all items

.. note:: **Automatic Consumption**

   You typically **don't** manually consume from slots. Activation policies
   handle this automatically based on their logic.

Backpressure
------------

When a slot's queue is full, it exerts **backpressure** by rejecting new data:

.. code-block:: python

   try:
       runtime.post("flow", "routine", "slot", {"data": "value"})
   except SlotQueueFullError:
       print("Slot queue is full!")
       # Handle: retry, buffer, or drop

.. warning:: **Pitfall: Ignoring SlotQueueFullError**

   Not handling ``SlotQueueFullError`` causes data loss:

   .. code-block:: python

      # WRONG - Will lose data on full queue
      runtime.post("flow", "routine", "slot", {"data": "value"})

      # RIGHT - Handle the error
      from routilux.core.slot import SlotQueueFullError
      try:
          runtime.post("flow", "routine", "slot", {"data": "value"})
      except SlotQueueFullError:
          # Retry with backoff
          import time
          time.sleep(0.1)
          runtime.post("flow", "routine", "slot", {"data": "value"})

**Strategies for Handling Full Queues**:

1. **Increase queue size**:
   ```python
   self.add_slot("data", max_queue_length=100000)
   ```

2. **Process faster**: Add more workers or optimize logic

3. **Implement backpressure**:
   ```python
   def emit_with_backpressure(event, data, max_retries=3):
       for i in range(max_retries):
           try:
               self.emit(event, **data)
               return True
           except SlotQueueFullError:
               time.sleep(2 ** i)  # Exponential backoff
       return False
   ```

Complete Example: Multi-Stage Pipeline
--------------------------------------

Here's a complete example showing slots and events in a multi-stage pipeline:

.. code-block:: python
   :linenos:
   :name: slots_events_pipeline

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   # Stage 1: Ingest
   class Ingestor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("raw")
           self.add_event("validated", ["data", "is_valid"])

           def ingest(slot_data, policy_message, worker_state):
               data_list = slot_data.get("raw", [])
               if data_list:
                   item = data_list[0]
                   # Simple validation
                   is_valid = "value" in item and isinstance(item["value"], (int, float))
                   self.emit("validated", data=item, is_valid=is_valid)
                   print(f"Ingested: {item}, valid={is_valid}")

           self.set_logic(ingest)
           self.set_activation_policy(immediate_policy())

   # Stage 2: Transform
   class Transformer(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("validated")
           self.add_event("transformed", ["original", "result"])

           def transform(slot_data, policy_message, worker_state):
               data_list = slot_data.get("validated", [])
               if data_list:
                   item = data_list[0]
                   if item.get("is_valid"):
                       value = item["data"]["value"]
                       result = value * 2
                       self.emit("transformed",
                                original=item["data"],
                                result=result)
                       print(f"Transformed: {value} → {result}")

           self.set_logic(transform)
           self.set_activation_policy(immediate_policy())

   # Stage 3: Output
   class Outputter(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("final")

           def output(slot_data, policy_message, worker_state):
               data_list = slot_data.get("final", [])
               if data_list:
                   item = data_list[0]
                   print(f"OUTPUT: {item}")
                   # Could write to database, file, etc.

           self.set_logic(output)
           self.set_activation_policy(immediate_policy())

   # Build pipeline
   flow = Flow("processing_pipeline")

   flow.add_routine(Ingestor(), "ingest")
   flow.add_routine(Transformer(), "transform")
   flow.add_routine(Outputter(), "output")

   # Connect stages
   flow.connect("ingest", "validated", "transform", "validated")
   flow.connect("transform", "transformed", "output", "final")

   # Register and execute
   FlowRegistry.get_instance().register_by_name("processing_pipeline", flow)

   with Runtime(thread_pool_size=3) as runtime:
       # Send data
       runtime.post("processing_pipeline", "ingest", "raw", {"value": 21})
       runtime.post("processing_pipeline", "ingest", "raw", {"value": 42})
       runtime.post("processing_pipeline", "ingest", "raw", {"invalid": "data"})

       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Ingested: {'value': 21}, valid=True
   Ingested: {'value': 42}, valid=True
   Ingested: {'invalid': 'data'}, valid=False
   Transformed: 21 → 42
   OUTPUT: {'original': {'value': 21}, 'result': 42}
   Transformed: 42 → 84
   OUTPUT: {'original': {'value': 42}, 'result': 84}

Pitfalls Reference
------------------

.. list-table:: Common Slot/Event Pitfalls
   :widths: 50 50
   :header-rows: 1

   * - Pitfall
     - Solution
   * - Emitting non-existent event
     - Always add event with ``add_event()`` first
   * - Slot queue full
     - Increase ``max_queue_length`` or handle error
   * - Not checking empty lists
     - Always ``if data_list:`` before accessing
   * - Forgetting to connect
     - Always call ``flow.connect()`` for data flow
   * - Wrong connection order
     - ``connect(source_id, event, dest_id, slot)``
   * - Assuming order preservation
     - Order is preserved per-slot, not globally

Next Steps
----------

Now that you understand slots and events, learn about:

- :doc:`understanding_flows` - Creating and managing flows
- :doc:`../connections/simple_connection` - More connection patterns
- :doc:`../data_flow/parameter_mapping` - Advanced data routing
- :doc:`../../pitfalls/routine_design` - Common pitfalls

.. seealso::

   :doc:`../../api_reference/core/slot`
      Complete Slot API reference

   :doc:`../../api_reference/core/event`
      Complete Event API reference
