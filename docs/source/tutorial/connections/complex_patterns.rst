Complex Connection Patterns
============================

Real-world workflows often require combining multiple connection patterns:
fan-out followed by fan-in, conditional routing, feedback loops, and more.
This tutorial covers advanced patterns for building sophisticated workflows.

.. note:: **What You'll Learn**

   - Diamond pattern (fan-out then fan-in)
   - Conditional branching and routing
   - Feedback loops and recursion
   - Multi-stage workflows with complex topologies
   - Pattern composition strategies

.. note:: **Prerequisites**

   - :doc:`simple_connection` - Basic connections
   - :doc:`one_to_many` - Fan-out patterns
   - :doc:`many_to_one` - Fan-in patterns

Diamond Pattern: Fan-Out Then Fan-In
-------------------------------------

The diamond pattern splits work across parallel processors, then merges results:

.. code-block:: text

        ┌──────────┐
        │  Source  │
        └─────┬────┘
              │
       ┌──────┴──────┐
       │             │
   ┌───▼────┐   ┌───▼────┐   ┌───▼────┐
   │Process A│   │Process B│   │Process C│
   └───┬────┘   └───┬────┘   └───┬────┘
       │             │             │
       └──────┬──────┴─────────────┘
              │
       ┌──────▼──────┐
       │  Aggregator │
       └─────────────┘

**Use Cases**:
- Parallel data validation (multiple validators)
- Multi-format processing (PDF, HTML, plain text)
- Redundant processing (compare results from multiple sources)

.. code-block:: python
   :linenos:
   :name: connections_complex_diamond

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy, all_slots_ready_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   import time

   # Source
   class WorkGenerator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("task", ["task_id", "data"])

           def generate(slot_data, policy_message, worker_state):
               tasks = [
                   {"task_id": 1, "data": "analyze"},
                   {"task_id": 2, "data": "process"},
                   {"task_id": 3, "data": "validate"},
               ]
               for task in tasks:
                   print(f"Generator: Created task {task['task_id']}")
                   self.emit("task", **task)

           self.set_logic(generate)
           self.set_activation_policy(immediate_policy())

   # Parallel processors
   class QuickProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("task")
           self.add_event("quick_result", ["task_id", "processor", "result", "duration"])

           def process(slot_data, policy_message, worker_state):
               task_list = slot_data.get("task", [])
               if task_list:
                   task = task_list[0]
                   start = time.time()
                   # Quick processing
                   time.sleep(0.1)
                   result = f"quick_{task['data']}"
                   duration = time.time() - start
                   print(f"  [Quick] Processed task {task['task_id']} in {duration:.2f}s")
                   self.emit("quick_result",
                            task_id=task['task_id'],
                            processor="quick",
                            result=result,
                            duration=duration)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   class ThoroughProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("task")
           self.add_event("thorough_result", ["task_id", "processor", "result", "duration"])

           def process(slot_data, policy_message, worker_state):
               task_list = slot_data.get("task", [])
               if task_list:
                   task = task_list[0]
                   start = time.time()
                   # Thorough processing (slower)
                   time.sleep(0.2)
                   result = f"thorough_{task['data']}_detailed"
                   duration = time.time() - start
                   print(f"  [Thorough] Processed task {task['task_id']} in {duration:.2f}s")
                   self.emit("thorough_result",
                            task_id=task['task_id'],
                            processor="thorough",
                            result=result,
                            duration=duration)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   class AlternativeProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("task")
           self.add_event("alt_result", ["task_id", "processor", "result", "duration"])

           def process(slot_data, policy_message, worker_state):
               task_list = slot_data.get("task", [])
               if task_list:
                   task = task_list[0]
                   start = time.time()
                   # Alternative processing
                   time.sleep(0.15)
                   result = f"alt_{task['data']}_experimental"
                   duration = time.time() - start
                   print(f"  [Alt] Processed task {task['task_id']} in {duration:.2f}s")
                   self.emit("alt_result",
                            task_id=task['task_id'],
                            processor="alternative",
                            result=result,
                            duration=duration)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   # Aggregator - waits for all results
   class ResultAggregator(Routine):
       def __init__(self):
           super().__init__()
           # Need multiple slots to receive from different processors
           self.add_slot("quick")
           self.add_slot("thorough")
           self.add_slot("alt")
           self.add_event("final", ["task_id", "results"])

           def aggregate(slot_data, policy_message, worker_state):
               # Collect results from all slots
               results = {}
               for slot_name in ["quick", "thorough", "alt"]:
                   slot_list = slot_data.get(slot_name, [])
                   if slot_list:
                       item = slot_list[0]
                       results[item.get("processor")] = {
                           "result": item.get("result"),
                           "duration": item.get("duration")
                       }

               if results:
                   task_id = list(results.values())[0].get("task_id", "unknown")
                   print(f"\nAggregator: Task {task_id} complete")
                   for processor, data in results.items():
                       print(f"  {processor}: {data['result']} ({data['duration']:.2f}s)")
                   print()

           self.set_logic(aggregate)
           # Wait for all three slots to have data
           self.set_activation_policy(all_slots_ready_policy())

   # Build diamond flow
   flow = Flow("diamond_processing")

   flow.add_routine(WorkGenerator(), "generator")
   flow.add_routine(QuickProcessor(), "quick")
   flow.add_routine(ThoroughProcessor(), "thorough")
   flow.add_routine(AlternativeProcessor(), "alt")
   flow.add_routine(ResultAggregator(), "aggregator")

   # Fan-out: generator → all processors
   flow.connect("generator", "task", "quick", "task")
   flow.connect("generator", "task", "thorough", "task")
   flow.connect("generator", "task", "alt", "task")

   # Fan-in: all processors → aggregator
   flow.connect("quick", "quick_result", "aggregator", "quick")
   flow.connect("thorough", "thorough_result", "aggregator", "thorough")
   flow.connect("alt", "alt_result", "aggregator", "alt")

   FlowRegistry.get_instance().register_by_name("diamond_processing", flow)

   with Runtime(thread_pool_size=5) as runtime:
       runtime.exec("diamond_processing")
       runtime.post("diamond_processing", "generator", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=10.0)

**Expected Output**:

.. code-block:: text

   Generator: Created task 1
   Generator: Created task 2
   Generator: Created task 3
     [Quick] Processed task 1 in 0.10s
     [Thorough] Processed task 1 in 0.20s
     [Alt] Processed task 1 in 0.15s

   Aggregator: Task 1 complete
     quick: quick_analyze (0.10s)
     thorough: thorough_analyze_detailed (0.20s)
     alternative: alt_analyze_experimental (0.15s)

     [Quick] Processed task 2 in 0.10s
     [Thorough] Processed task 2 in 0.20s
     [Alt] Processed task 2 in 0.15s

   Aggregator: Job 2 complete
     quick: quick_process (0.10s)
     thorough: thorough_process_detailed (0.20s)
     alternative: alt_process_experimental (0.15s)
   ...

Conditional Branching Pattern
-------------------------------

Route data to different processors based on conditions:

.. code-block:: text

        ┌──────────┐
        │  Source  │
        └─────┬────┘
              │
         ┌────┴────┐
         │ Router  │
         └────┬────┘
              │
      ┌───────┼────────┬─────────┐
      │       │        │         │
   High▶   Med▶     Low▶     Error▶
   Proc    Proc     Proc      Handler

.. code-block:: python
   :linenos:

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   # Data with priority
   class PrioritySource(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("item", ["id", "priority", "data"])

           def generate(slot_data, policy_message, worker_state):
               import random
               items = [
                   {"id": 1, "priority": random.randint(1, 10), "data": f"item_{i}"}
                   for i in range(1, 11)
               ]
               for item in items:
                   prio = item["priority"]
                   print(f"Source: Item {item['id']} (priority: {prio})")
                   self.emit("item", **item)

           self.set_logic(generate)
           self.set_activation_policy(immediate_policy())

   # Router that branches based on priority
   class PriorityRouter(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("item")
           self.add_event("high", ["id", "priority", "data"])
           self.add_event("medium", ["id", "priority", "data"])
           self.add_event("low", ["id", "priority", "data"])
           self.add_event("error", ["id", "priority", "data", "reason"])

           def route(slot_data, policy_message, worker_state):
               items = slot_data.get("item", [])
               if items:
                   item = items[0]
                   priority = item.get("priority", 0)
                   item_id = item.get("id")

                   # Branch based on priority
                   if priority > 8:
                       print(f"  Router: Item {item_id} → HIGH priority path")
                       self.emit("high", **item)
                   elif priority >= 5:
                       print(f"  Router: Item {item_id} → MEDIUM priority path")
                       self.emit("medium", **item)
                   elif priority >= 1:
                       print(f"  Router: Item {item_id} → LOW priority path")
                       self.emit("low", **item)
                   else:
                       print(f"  Router: Item {item_id} → ERROR (invalid priority)")
                       self.emit("error", **item, reason="invalid_priority")

           self.set_logic(route)
           self.set_activation_policy(immediate_policy())

   # Priority-specific processors
   class HighPriorityProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("high")

           def process(slot_data, policy_message, worker_state):
               items = slot_data.get("high", [])
               if items:
                   item = items[0]
                   print(f"    [HIGH] Expedited processing for item {item['id']}")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   class MediumPriorityProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("medium")

           def process(slot_data, policy_message, worker_state):
               items = slot_data.get("medium", [])
               if items:
                   item = items[0]
                   print(f"    [MEDIUM] Standard processing for item {item['id']}")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   class LowPriorityProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("low")

           def process(slot_data, policy_message, worker_state):
               items = slot_data.get("low", [])
               if items:
                   item = items[0]
                   print(f"    [LOW] Batch processing for item {item['id']}")

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   class ErrorHandler(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("error")

           def handle(slot_data, policy_message, worker_state):
               items = slot_data.get("error", [])
               if items:
                   item = items[0]
                   reason = item.get("reason", "unknown")
                   print(f"    [ERROR] Item {item['id']}: {reason}")

           self.set_logic(handle)
           self.set_activation_policy(immediate_policy())

   # Build conditional branching flow
   flow = Flow("priority_branching")

   flow.add_routine(PrioritySource(), "source")
   flow.add_routine(PriorityRouter(), "router")
   flow.add_routine(HighPriorityProcessor(), "high_proc")
   flow.add_routine(MediumPriorityProcessor(), "med_proc")
   flow.add_routine(LowPriorityProcessor(), "low_proc")
   flow.add_routine(ErrorHandler(), "error_handler")

   # Connect source to router
   flow.connect("source", "item", "router", "item")

   # Connect router branches to processors
   flow.connect("router", "high", "high_proc", "high")
   flow.connect("router", "medium", "med_proc", "medium")
   flow.connect("router", "low", "low_proc", "low")
   flow.connect("router", "error", "error_handler", "error")

   FlowRegistry.get_instance().register_by_name("priority_branching", flow)

   with Runtime(thread_pool_size=6) as runtime:
       runtime.exec("priority_branching")
       runtime.post("priority_branching", "source", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=10.0)

Multi-Stage Pipeline with Feedback
-----------------------------------

Workflows that feed results back to earlier stages:

.. code-block:: text

   ┌─────────┐
   │  Input  │
   └────┬────┘
        │
   ┌────▼─────┐
   │ Process  │
   └────┬─────┘
        │
   ┌────▼─────┐
   │ Validate │────┐
   └────┬─────┘    │ (feedback if invalid)
        │          │
        ▼          │
   ┌─────────┐    │
   │ Output  │    │
   └─────────┘    │
                  │
   ┌──────────────┘
   │
   ▼
   [retry queue]

.. code-block:: python
   :linenos:

   class WorkItemGenerator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("work", ["id", "attempts", "data"])

           def generate(slot_data, policy_message, worker_state):
               items = [
                   {"id": i, "attempts": 0, "data": f"work_{i}"}
                   for i in range(1, 6)
               ]
               for item in items:
                   print(f"Generator: Created work item {item['id']}")
                   self.emit("work", **item)

           self.set_logic(generate)
           self.set_activation_policy(immediate_policy())

   class WorkProcessor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("work")
           self.add_event("processed", ["id", "attempts", "result"])

           def process(slot_data, policy_message, worker_state):
               items = slot_data.get("work", [])
               if items:
                   item = items[0]
                   import random
                   # Simulate 30% failure rate
                   success = random.random() > 0.3
                   result = "success" if success else "needs_retry"
                   print(f"  Processor: Work {item['id']} → {result}")
                   self.emit("processed", id=item['id'],
                            attempts=item['attempts'], result=result)

           self.set_logic(process)
           self.set_activation_policy(immediate_policy())

   class WorkValidator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("processed")
           self.add_event("accepted", ["id"])
           self.add_event("rejected", ["id", "attempts"])

           def validate(slot_data, policy_message, worker_state):
               items = slot_data.get("processed", [])
               if items:
                   item = items[0]
                   if item['result'] == "success":
                       print(f"    Validator: Work {item['id']} ACCEPTED")
                       self.emit("accepted", id=item['id'])
                   else:
                       attempts = item['attempts'] + 1
                       print(f"    Validator: Work {item['id']} REJECTED (attempt {attempts})")
                       self.emit("rejected", id=item['id'], attempts=attempts)

           self.set_logic(validate)
           self.set_activation_policy(immediate_policy())

   class RetryHandler(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("rejected")
           self.add_event("retry", ["id", "attempts", "data"])
           self.add_event("failed", ["id"])

           def handle(slot_data, policy_message, worker_state):
               items = slot_data.get("rejected", [])
               if items:
                   item = items[0]
                   attempts = item['attempts']
                   if attempts < 3:
                       print(f"      Retry: Re-queueing work {item['id']} (attempt {attempts})")
                       self.emit("retry", id=item['id'], attempts=attempts,
                                data=f"work_{item['id']}")
                   else:
                       print(f"      Retry: Work {item['id']} FAILED after {attempts} attempts")
                       self.emit("failed", id=item['id'])

           self.set_logic(handle)
           self.set_activation_policy(immediate_policy())

   class OutputCollector(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("accepted")
           self.add_slot("failed")

           def collect(slot_data, policy_message, worker_state):
               accepted = slot_data.get("accepted", [])
               failed = slot_data.get("failed", [])

               if accepted:
                   for item in accepted:
                       print(f"✓ Work {item['id']} completed successfully")
               if failed:
                   for item in failed:
                       print(f"✗ Work {item['id']} failed after max retries")

           self.set_logic(collect)
           self.set_activation_policy(all_slots_ready_policy())

   # Build feedback loop flow
   flow = Flow("retry_pipeline")

   flow.add_routine(WorkItemGenerator(), "generator")
   flow.add_routine(WorkProcessor(), "processor")
   flow.add_routine(WorkValidator(), "validator")
   flow.add_routine(RetryHandler(), "retry_handler")
   flow.add_routine(OutputCollector(), "collector")

   # Main pipeline
   flow.connect("generator", "work", "processor", "work")
   flow.connect("processor", "processed", "validator", "processed")
   flow.connect("validator", "accepted", "collector", "accepted")
   flow.connect("validator", "rejected", "retry_handler", "rejected")
   flow.connect("retry_handler", "failed", "collector", "failed")

   # FEEDBACK LOOP: retry → processor
   flow.connect("retry_handler", "retry", "processor", "work")

   FlowRegistry.get_instance().register_by_name("retry_pipeline", flow)

   with Runtime(thread_pool_size=5) as runtime:
       runtime.exec("retry_pipeline")
       runtime.post("retry_pipeline", "generator", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=15.0)

Pattern Composition Guidelines
-------------------------------

**1. Combine Patterns Modularity**:

.. code-block:: python

   # Build complex flows from simple, reusable sub-flows

   # Sub-flow: validation
   validation_flow = create_validation_subflow()

   # Sub-flow: processing
   processing_flow = create_processing_subflow()

   # Sub-flow: output
   output_flow = create_output_subflow()

   # Compose into complete flow
   complete_flow = compose_flows(
       validation_flow,
       processing_flow,
       output_flow
   )

**2. Use Intermediate Buffers**:

.. code-block:: python

   # Add buffer routines between stages to decouple timing
   flow.add_routine(BufferRoutine(), "buffer1")
   flow.add_routine(BufferRoutine(), "buffer2")

   flow.connect("stage1", "output", "buffer1", "input")
   flow.connect("buffer1", "output", "stage2", "input")

**3. Design for Scalability**:

.. code-block:: python

   # Make it easy to add more processors
   for i in range(num_processors):
       flow.add_routine(Processor(), f"processor_{i}")
       flow.connect("router", f"output_{i}", f"processor_{i}", "input")
       flow.connect(f"processor_{i}", "result", "aggregator", "results")

Pitfalls Reference
------------------

.. list-table:: Complex Pattern Pitfalls
   :widths: 50 50
   :header-rows: 1

   * - Pitfall
     - Solution
   * - Feedback loops causing infinite cycles
     - Use maximum retry counters
   * - Diamond pattern deadlocks
     - Use all_slots_ready_policy correctly
   * - Race conditions in aggregation
     - Use WorkerState for shared data
   * - Over-complex topologies
     - Break into sub-flows
   * - Hard to debug
     - Add logging at each stage

Next Steps
----------

- :doc:`../cookbook/data_processing_pipeline` - Complete pipeline examples
- :doc:`../advanced/flow_builder` - Declarative flow construction
- :doc:`../../user_guide/connections` - Comprehensive connection guide

.. seealso::

   :doc:`../../api_reference/core/flow`
      Complete Flow API reference

   :doc:`../../pitfalls/routine_design`
      Common design pitfalls
