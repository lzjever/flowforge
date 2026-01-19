One-to-Many Connections (Fan-Out)
==================================

Fan-out is a powerful pattern where one event connects to multiple slots,
allowing data to be processed in parallel by multiple routines or broadcast to
multiple subscribers.

.. note:: **What You'll Learn**

   - How to connect one event to multiple slots
   - Building parallel processing pipelines
   - Broadcasting patterns
   - Use cases and best practices

.. note:: **Prerequisites**

   - :doc:`simple_connection` - Understand simple connections first

Understanding Fan-Out
---------------------

In a fan-out pattern, one routine's event connects to multiple routines' slots:

.. code-block:: text

   ┌──────────────┐
   │   Source     │
   │              │
   │  emit()      │─────┬──────────────┬─────────────┐
   │  "data"      │     │              │             │
   └──────────────┘     ▼              ▼             ▼
                 ┌──────────┐   ┌──────────┐   ┌──────────┐
                 │Processor A│   │Processor B│   │Processor C│
                 └──────────┘   └──────────┘   └──────────┘

**Key Characteristics**:

- **One event** → **Multiple slots**
- **Same data** sent to all destinations
- **Independent processing** - routines execute in parallel
- **Order not guaranteed** - routines may finish in any order

Basic Fan-Out Example
----------------------

.. code-block:: python
   :linenos:
   :name: connections_one_to_many_basic

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   import time

   # Source routine
   class DataBroadcaster(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("news", ["headline", "timestamp"])

           def broadcast(slot_data, policy_message, worker_state):
               headlines = [
                   "Breaking: Python 4.0 Released!",
                   "News: Routilux Documentation Complete",
                   "Update: Async Support Improved"
               ]
               for headline in headlines:
                   import datetime
                   timestamp = datetime.datetime.now().isoformat()
                   print(f"Broadcasting: {headline}")
                   self.emit("news", headline=headline, timestamp=timestamp)
                   time.sleep(0.1)  # Simulate delay

           self.set_logic(broadcast)
           self.set_activation_policy(immediate_policy())

   # Multiple subscriber routines
   class EmailSubscriber(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("news")
           self.set_config(subscriber_name="Email Service")

           def process_news(slot_data, policy_message, worker_state):
               data_list = slot_data.get("news", [])
               if data_list:
                   item = data_list[0]
                   name = self.get_config("subscriber_name")
                   print(f"  [{name}] Would send email: {item['headline']}")

           self.set_logic(process_news)
           self.set_activation_policy(immediate_policy())

   class SMSSubscriber(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("news")
           self.set_config(subscriber_name="SMS Service")

           def process_news(slot_data, policy_message, worker_state):
               data_list = slot_list.get("news", [])
               if data_list:
                   item = data_list[0]
                   name = self.get_config("subscriber_name")
                   print(f"  [{name}] Would send SMS: {item['headline'][:50]}...")

           self.set_logic(process_news)
           self.set_activation_policy(immediate_policy())

   class LogSubscriber(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("news")
           self.set_config(subscriber_name="Log Service")

           def process_news(slot_data, policy_message, worker_state):
               data_list = slot_data.get("news", [])
               if data_list:
                   item = data_list[0]
                   name = self.get_config("subscriber_name")
                   print(f"  [{name}] Logged: {item['timestamp']} - {item['headline']}")

           self.set_logic(process_news)
           self.set_activation_policy(immediate_policy())

   # Build fan-out flow
   flow = Flow("news_fanout")

   flow.add_routine(DataBroadcaster(), "broadcaster")
   flow.add_routine(EmailSubscriber(), "email")
   flow.add_routine(SMSSubscriber(), "sms")
   flow.add_routine(LogSubscriber(), "log")

   # FAN-OUT: broadcaster → all subscribers
   flow.connect("broadcaster", "news", "email", "news")
   flow.connect("broadcaster", "news", "sms", "news")
   flow.connect("broadcaster", "news", "log", "news")

   FlowRegistry.get_instance().register_by_name("news_fanout", flow)

   with Runtime(thread_pool_size=4) as runtime:
       runtime.exec("news_fanout")
       runtime.post("news_fanout", "broadcaster", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=10.0)

**Expected Output**:

.. code-block:: text

   Broadcasting: Breaking: Python 4.0 Released!
     [Email Service] Would send email: Breaking: Python 4.0 Released!
     [SMS Service] Would send SMS: Breaking: Python 4.0 Released!...
     [Log Service] Logged: 2024-01-01T10:00:00 - Breaking: Python 4.0 Released!
   Broadcasting: News: Routilux Documentation Complete
     [Email Service] Would send email: News: Routilux Documentation Complete
     [SMS Service] Would send SMS: News: Routilux Documentation Complete...
     [Log Service] Logged: 2024-01-01T10:00:01 - News: Routilux Documentation Complete
   Broadcasting: Update: Async Support Improved
     [Email Service] Would send email: Update: Async Support Improved
     [SMS Service] Would send SMS: Update: Async Support Improved...
     [Log Service] Logged: 2024-01-01T10:00:02 - Update: Async Support Improved

Parallel Processing Pattern
----------------------------

Fan-out enables parallel processing of the same data:

.. code-block:: python
   :linenos:

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   import time

   # Input data
   class DataProducer(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("image", ["id", "data"])

           def produce(slot_data, policy_message, worker_state):
               # Simulate producing image data
               for i in range(3):
                   print(f"Producer: Sending image {i}")
                   self.emit("image", id=i, data=f"image_{i}_bytes")
                   time.sleep(0.1)

           self.set_logic(produce)
           self.set_activation_policy(immediate_policy())

   # Parallel processors
   class ResizeProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("image")
           self.add_event("resized", ["id", "size"])

           def process(slot_data, policy_message, worker_state):
               data_list = slot_data.get("image", [])
               if data_list:
                   img = data_list[0]
                   img_id = img["id"]
                   # Simulate processing time
                   time.sleep(0.2)
                   print(f"  [Resize] Processed image {img_id}")
                   self.emit("resized", id=img_id, size="800x600")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   class FilterProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("image")
           self.add_event("filtered", ["id", "filter"])

           def process(slot_data, policy_message, worker_state):
               data_list = slot_data.get("image", [])
               if data_list:
                   img = data_list[0]
                   img_id = img["id"]
                   # Different processing time
                   time.sleep(0.15)
                   print(f"  [Filter] Processed image {img_id}")
                   self.emit("filtered", id=img_id, filter="grayscale")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   class CompressProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("image")
           self.add_event("compressed", ["id", "ratio"])

           def process(slot_data, policy_message, worker_state):
               data_list = slot_data.get("image", [])
               if data_list:
                   img = data_list[0]
                   img_id = img["id"]
                   # Different processing time
                   time.sleep(0.25)
                   print(f"  [Compress] Processed image {img_id}")
                   self.emit("compressed", id=img_id, ratio="0.8")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Build parallel processing flow
   flow = Flow("parallel_image_processing")

   flow.add_routine(DataProducer(), "producer")
   flow.add_routine(ResizeProcessor(), "resize")
   flow.add_routine(FilterProcessor(), "filter")
   flow.add_routine(CompressProcessor(), "compress")

   # FAN-OUT: One image → multiple parallel processors
   flow.connect("producer", "image", "resize", "image")
   flow.connect("producer", "image", "filter", "image")
   flow.connect("producer", "image", "compress", "image")

   FlowRegistry.get_instance().register_by_name("parallel_image_processing", flow)

   with Runtime(thread_pool_size=4) as runtime:
       runtime.exec("parallel_image_processing")
       runtime.post("parallel_image_processing", "producer", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=10.0)

**Expected Output** (order may vary due to parallel execution):

.. code-block:: text

   Producer: Sending image 0
   Producer: Sending image 1
     [Filter] Processed image 0
     [Resize] Processed image 0
     [Compress] Processed image 0
   Producer: Sending image 2
     [Filter] Processed image 1
     [Resize] Processed image 1
     [Compress] Processed image 1
     [Filter] Processed image 2
     [Resize] Processed image 2
     [Compress] Processed image 2

.. tip:: **Parallel Execution Benefits**

   Fan-out enables parallelism:
   - **Faster processing**: Multiple routines work simultaneously
   - **Resource utilization**: Use all CPU cores
   - **Independent failures**: One routine's error doesn't affect others

   Total time = max(individual times) instead of sum(individual times)

Conditional Fan-Out
-------------------

Sometimes you want to fan-out based on conditions:

.. code-block:: python
   :linenos:

   class DataRouter(Routine):
       """Routes data to different processors based on type."""

       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("high_priority", ["data"])
           self.add_event("normal_priority", ["data"])
           self.add_event("low_priority", ["data"])

           def route(slot_data, policy_message, worker_state):
               data_list = slot_data.get("input", [])
               if data_list:
                   item = data_list[0]
                   priority = item.get("priority", 0)

                   # Emit to different events based on priority
                   if priority >= 8:
                       print(f"Router: High priority → {item}")
                       self.emit("high_priority", data=item)
                   elif priority >= 5:
                       print(f"Router: Normal priority → {item}")
                       self.emit("normal_priority", data=item)
                   else:
                       print(f"Router: Low priority → {item}")
                       self.emit("low_priority", data=item)

           self.set_logic(route)
           self.set_activation_policy(immediate_policy())

   class PriorityProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("data")
           self.set_config(level="")

           def process(slot_data, policy_message, worker_state):
               data_list = slot_data.get("data", [])
               if data_list:
                   item = data_list[0]
                   level = self.get_config("level")
                   print(f"  [{level}] Processing: {item}")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Build conditional fan-out flow
   flow = Flow("priority_routing")

   flow.add_routine(DataRouter(), "router")
   flow.add_routine(PriorityProcessor(), "high_proc")
   flow.add_routine(PriorityProcessor(), "normal_proc")
   flow.add_routine(PriorityProcessor(), "low_proc")

   # Configure each processor
   flow.routines["high_proc"].set_config(level="HIGH")
   flow.routines["normal_proc"].set_config(level="NORMAL")
   flow.routines["low_proc"].set_config(level="LOW")

   # Connect different events to different processors
   flow.connect("router", "high_priority", "high_proc", "data")
   flow.connect("router", "normal_priority", "normal_proc", "data")
   flow.connect("router", "low_priority", "low_proc", "data")

   FlowRegistry.get_instance().register_by_name("priority_routing", flow)

   with Runtime(thread_pool_size=4) as runtime:
       runtime.exec("priority_routing")

       # Send items with different priorities
       items = [
           {"id": 1, "priority": 9},
           {"id": 2, "priority": 3},
           {"id": 3, "priority": 6},
           {"id": 4, "priority": 2},
       ]

       for item in items:
           runtime.post("priority_routing", "router", "input", item)

       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Router: High priority → {'id': 1, 'priority': 9}
     [HIGH] Processing: {'id': 1, 'priority': 9}
   Router: Low priority → {'id': 2, 'priority': 3}
     [LOW] Processing: {'id': 2, 'priority': 3}
   Router: Normal priority → {'id': 3, 'priority': 6}
     [NORMAL] Processing: {'id': 3, 'priority': 6}
   Router: Low priority → {'id': 4, 'priority': 2}
     [LOW] Processing: {'id': 4, 'priority': 2}

Fan-Out Use Cases
-----------------

**1. Notification Systems**:

.. code-block:: text

   Event ──▶ Email Notifier
          ├─▶ SMS Notifier
          ├─▶ Push Notifier
          └─▶ Webhook Notifier

**2. Data Validation**:

.. code-block:: text

   Input Data ──▶ Schema Validator
               ├─▶ Business Rule Validator
               └─▶ Security Validator

**3. Parallel Transformations**:

.. code-block:: text

   Document ──▶ PDF Converter
             ├─▶ HTML Converter
             └─▶ Plain Text Converter

**4. Multi-Format Export**:

.. code-block:: text

   Data ──▶ JSON Exporter
         ├─▶ CSV Exporter
         ├─▶ XML Exporter
         └─▶ YAML Exporter

Considerations and Pitfalls
----------------------------

.. warning:: **Pitfall 1: Shared Mutable State**

   Multiple routines accessing shared state causes race conditions:

   .. code-block:: python

      # WRONG - Shared mutable state
      counter = {"value": 0}  # Shared!

      class CounterRoutine(Routine):
          def __init__(self):
              super().__init__()
              self.add_slot("input")

              def increment(slot_data, policy_message, worker_state):
                  counter["value"] += 1  # Race condition!
                  print(counter["value"])

              self.set_logic(increment)

   **Solution**: Use WorkerState for thread-safe state:

   .. code-block:: python

      # RIGHT - WorkerState is thread-safe
      class CounterRoutine(Routine):
          def __init__(self):
              super().__init__()
              self.add_slot("input")

              def increment(slot_data, policy_message, worker_state):
                  state = worker_state.get_routine_state("counter") or {}
                  count = state.get("count", 0) + 1
                  worker_state.update_routine_state("counter", {"count": count})
                  print(count)

              self.set_logic(increment)

.. warning:: **Pitfall 2: Assuming Order**

   Fan-out execution order is NOT guaranteed:

   .. code-block:: python

      # Don't rely on execution order!
      flow.connect("source", "data", "proc1", "input")
      flow.connect("source", "data", "proc2", "input")
      flow.connect("source", "data", "proc3", "input")

      # WRONG: Assuming proc1 finishes before proc2
      # RIGHT: Design for independent parallel execution

.. warning:: **Pitfall 3: Resource Exhaustion**

   Too many fan-out connections can overwhelm resources:

   .. code-block:: python

      # Potentially problematic - 100 parallel routines
      for i in range(100):
          flow.add_routine(Processor(), f"proc_{i}")
          flow.connect("source", "data", f"proc_{i}", "input")

   **Solution**: Use batch processing or connection pooling:

   .. code-block:: python

      # Better - Use batch_size_policy to limit concurrency
      class BatchProcessor(Routine):
          def __init__(self):
              super().__init__()
              self.add_slot("items")  # Receives batches
              # Process batch items...

      from routilux.activation_policies import batch_size_policy
      batch_processor.set_activation_policy(batch_size_policy(10))

.. tip:: **Thread Pool Sizing**

   For fan-out patterns, ensure your thread pool is large enough:

   .. code-block:: python

      # Calculate optimal thread pool size
      num_fanout_destinations = 5
      thread_pool_size = num_fanout_destinations + 2  # +2 for source/other
      runtime = Runtime(thread_pool_size=thread_pool_size)

Next Steps
----------

Learn about other connection patterns:

- :doc:`many_to_one` - Fan-in patterns for aggregation
- :doc:`complex_patterns` - Combining fan-out and fan-in
- :doc:`../concurrency/thread_pools` - Thread pool optimization

.. seealso::

   :doc:`../../user_guide/connections`
      Comprehensive connection patterns guide

   :doc:`../../pitfalls/concurrency`
      Common concurrency pitfalls and solutions
