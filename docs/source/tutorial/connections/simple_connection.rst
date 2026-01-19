Simple Connections
==================

The most common pattern in Routilux is a simple point-to-point connection: one
routine's event connects to another routine's slot. This pattern forms the basis
of linear pipelines and sequential workflows.

.. note:: **What You'll Learn**

   - How to create point-to-point connections
   - Understanding the connection syntax
   - Building linear pipelines
   - Validation and error handling

.. note:: **Prerequisites**

   - :doc:`../basics/understanding_flows` - Understand Flows first

Basic Connection Syntax
-----------------------

A simple connection links one event to one slot:

.. code-block:: python

   flow.connect(
       "source_routine_id",   # Routine that emits
       "event_name",         # Event to connect
       "dest_routine_id",    # Routine that receives
       "slot_name"           # Slot that receives
   )

.. code-block:: text

   ┌──────────────┐                ┌──────────────┐
   │  Routine A   │                │  Routine B   │
   │              │                │              │
   │  emit()      │──────────────▶│  Slot        │
   │  "output"    │   Connection   │  "input"     │
   └──────────────┘                └──────────────┘

Complete Example: Two-Routine Pipeline
--------------------------------------

.. code-block:: python
   :linenos:
   :name: connections_simple_two_routines

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   # Source routine - generates numbers
   class NumberGenerator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("number", ["value"])

           def generate(slot_data, policy_message, worker_state):
               import random
               value = random.randint(1, 100)
               print(f"Generator: Producing {value}")
               self.emit("number", value=value)

           self.set_logic(generate)
           self.set_activation_policy(immediate_policy())

   # Sink routine - receives numbers
   class NumberPrinter(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("input")
           self.add_event("received", ["value"])

           def print_number(slot_data, policy_message, worker_state):
               data_list = slot_data.get("input", [])
               if data_list:
                   value = data_list[0].get("value", 0)
                   print(f"Printer: Received {value}")
                   self.emit("received", value=value)

           self.set_logic(print_number)
           self.set_activation_policy(immediate_policy())

   # Build flow
   flow = Flow("number_pipeline")

   flow.add_routine(NumberGenerator(), "generator")
   flow.add_routine(NumberPrinter(), "printer")

   # SIMPLE CONNECTION: generator → printer
   flow.connect("generator", "number", "printer", "input")

   # Register and execute
   FlowRegistry.get_instance().register_by_name("number_pipeline", flow)

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("number_pipeline")

       # Trigger the generator
       for i in range(3):
           runtime.post("number_pipeline", "generator", "trigger", {})

       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Generator: Producing 42
   Printer: Received 42
   Generator: Producing 17
   Printer: Received 17
   Generator: Producing 89
   Printer: Received 89

Multi-Stage Pipeline
--------------------

Multiple simple connections can create longer pipelines:

.. code-block:: python
   :linenos:

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy
   from routilux.monitoring.flow_registry import FlowRegistry

   # Stage 1: Ingest
   class Ingestor(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("raw")
           self.add_event("clean", ["data"])

           def ingest(slot_data, policy_message, worker_state):
               data_list = slot_data.get("raw", [])
               if data_list:
                   raw = data_list[0]
                   # Simple cleaning: strip whitespace
                   clean = {"text": raw.get("text", "").strip()}
                   print(f"Ingest: '{raw.get('text')}' → '{clean['text']}'")
                   self.emit("clean", data=clean)

           self.set_logic(ingest)
           self.set_activation_policy(immediate_policy())

   # Stage 2: Transform
   class Transformer(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("clean")
           self.add_event("upper", ["data"])

           def transform(slot_data, policy_message, worker_state):
               data_list = slot_data.get("clean", [])
               if data_list:
                   item = data_list[0]
                   text = item["data"].get("text", "")
                   upper = {"text": text.upper()}
                   print(f"Transform: '{text}' → '{upper['text']}'")
                   self.emit("upper", data=upper)

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
                   print(f"OUTPUT: {item['data']['text']}")

           self.set_logic(output)
           self.set_activation_policy(immediate_policy())

   # Build 3-stage pipeline
   flow = Flow("text_pipeline")

   flow.add_routine(Ingestor(), "ingest")
   flow.add_routine(Transformer(), "transform")
   flow.add_routine(Outputter(), "output")

   # Connect stages in sequence
   flow.connect("ingest", "clean", "transform", "clean")
   flow.connect("transform", "upper", "output", "final")

   FlowRegistry.get_instance().register_by_name("text_pipeline", flow)

   with Runtime(thread_pool_size=3) as runtime:
       runtime.exec("text_pipeline")

       # Input raw data
       inputs = [
           {"text": "  hello  "},
           {"text": "  world  "},
           {"text": "  test  "},
       ]

       for item in inputs:
           runtime.post("text_pipeline", "ingest", "raw", item)

       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Ingest: '  hello  ' → 'hello'
   Transform: 'hello' → 'HELLO'
   OUTPUT: HELLO
   Ingest: '  world  ' → 'world'
   Transform: 'world' → 'WORLD'
   OUTPUT: WORLD
   Ingest: '  test  ' → 'test'
   Transform: 'test' → 'TEST'
   OUTPUT: TEST

.. code-block:: text

   Pipeline Diagram:

   ┌─────────┐      ┌────────────┐      ┌──────────┐
   │ Ingestor │───▶ │Transformer │───▶ │Outputter │
   │         │      │            │      │          │
   │ emit()  │      │ emit()     │      │          │
   │ "clean" │      │ "upper"    │      │          │
   └─────────┘      └────────────┘      └──────────┘

Connection Validation
---------------------

Flows validate connections when they're created:

.. code-block:: python

   flow = Flow("validation_test")
   flow.add_routine(Source(), "source")
   flow.add_routine(Dest(), "dest")

   # Valid connection - succeeds
   flow.connect("source", "output", "dest", "input")

   # Invalid connection - raises ValueError
   # flow.connect("source", "nonexistent", "dest", "input")
   # ValueError: Event "nonexistent" not found on routine "source"

   # flow.connect("source", "output", "nonexistent", "input")
   # ValueError: Routine "nonexistent" not found in flow

   # flow.connect("source", "output", "dest", "nonexistent")
   # ValueError: Slot "nonexistent" not found on routine "dest"

.. tip:: **Connection Validation Benefits**

   Early validation catches errors before execution:
   - Typos in event/slot names
   - Missing routines
   - Incorrect routine IDs
   - Incompatible flow structures

Bidirectional Communication
----------------------------

For two-way communication, create two connections:

.. code-block:: python
   :linenos:

   class Requester(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")
           self.add_slot("response")
           self.add_event("request", ["query"])

           def send_request(slot_data, policy_message, worker_state):
               # Check if this is a response
               response_list = slot_data.get("response", [])
               if response_list:
                   answer = response_list[0].get("answer", "")
                   print(f"Requester received: {answer}")
                   return

               # Send a request
               print("Requester: Sending request")
               self.emit("request", query="What is the meaning of life?")

           self.set_logic(send_request)
           self.set_activation_policy(all_slots_ready_policy())

   class Responder(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("request")
           self.add_event("response", ["answer"])

           def respond(slot_data, policy_message, worker_state):
               data_list = slot_data.get("request", [])
               if data_list:
                   query = data_list[0].get("query", "")
                   print(f"Responder received: {query}")
                   self.emit("response", answer="42")

           self.set_logic(respond)
           self.set_activation_policy(immediate_policy())

   # Build bidirectional flow
   flow = Flow("bidirectional")

   flow.add_routine(Requester(), "requester")
   flow.add_routine(Responder(), "responder")

   # Two connections for bidirectional communication
   flow.connect("requester", "request", "responder", "request")
   flow.connect("responder", "response", "requester", "response")

   FlowRegistry.get_instance().register_by_name("bidirectional", flow)

   with Runtime(thread_pool_size=2) as runtime:
       runtime.exec("bidirectional")
       runtime.post("bidirectional", "requester", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Requester: Sending request
   Responder received: What is the meaning of life?
   Requester received: 42

.. code-block:: text

   Bidirectional Diagram:

        ┌────────────┐
        │ Requester  │
        └──────┬─────┘
               │
        ┌──────┴──────┐
        │             │
   request ▼           ▼ response
        ┌────────────┐
        │ Responder  │
        └────────────┘

Connection Best Practices
--------------------------

**1. Use Descriptive Names**:

.. code-block:: python

   # Good - Clear names
   flow.add_routine(UserAuthenticator(), "auth")
   flow.add_routine(UserProfileLoader(), "profile")
   flow.connect("auth", "authenticated", "profile", "user_id")

   # Avoid - Unclear names
   flow.add_routine(A(), "r1")
   flow.add_routine(B(), "r2")
   flow.connect("r1", "out", "r2", "in")

**2. Document Event Data**:

.. code-block:: python

   class DataProcessor(Routine):
       def __init__(self):
           super().__init__()
           # Document what the event emits
           self.add_event("processed", [
               "user_id",      # int - User identifier
               "username",     # str - Username
               "is_valid",     # bool - Whether data is valid
               "timestamp"     # str - ISO timestamp
           ])

**3. Validate Data Early**:

.. code-block:: python

   def validate_logic(slot_data, policy_message, worker_state):
       data_list = slot_data.get("input", [])
       if not data_list:
           return  # No data

       item = data_list[0]
       # Validate required fields
       if "id" not in item:
           print("WARNING: Missing 'id' field")
           return

       # Process valid data
       process(item)

Common Pitfalls
---------------

.. warning:: **Pitfall 1: Wrong Connection Order**

   The order matters: source → destination

   .. code-block:: python

      # WRONG - Reversed order
      flow.connect("dest", "input", "source", "output")

      # RIGHT - Source first, then destination
      flow.connect("source", "output", "dest", "input")

.. warning:: **Pitfall 2: Forgetting Connection**

   A routine without connections won't receive or send data:

   .. code-block:: python

      flow.add_routine(Source(), "source")
      flow.add_routine(Dest(), "dest")
      # Missing: flow.connect("source", "output", "dest", "input")

      # Dest routine will never receive data!

.. warning:: **Pitfall 3: Event/Slot Name Mismatch**

   Typos in names cause silent failures (validation catches this):

   .. code-block:: python

      # Event is "output" but trying to connect "out"
      flow.connect("source", "out", "dest", "input")  # ValueError!

Next Steps
----------

Learn about more complex connection patterns:

- :doc:`one_to_many` - Fan-out connections
- :doc:`many_to_one` - Fan-in connections
- :doc:`complex_patterns` - Diamond, branching, and loops

.. seealso::

   :doc:`../../api_reference/core/connection`
      Complete Connection API reference

   :doc:`../../user_guide/connections`
      Comprehensive connection patterns guide
