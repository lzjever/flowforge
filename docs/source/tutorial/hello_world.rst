Hello World - Your First Routilux Workflow
==========================================

This is the fastest way to get started with Routilux. In about 5 minutes, you'll
create a working workflow that prints "Hello, World!" and understand the core
concepts.

.. note:: **What You'll Learn**

   - How to create a simple ``Routine``
   - How to create a ``Flow`` and add routines
   - How to execute flows with ``Runtime``
   - The core pattern: Slots → Logic → Events

.. note:: **Prerequisites**

   Install Routilux:

   .. code-block:: bash

      pip install routilux

The Complete Example
--------------------

Here's the complete Hello World example. Save this as ``hello.py``:

.. code-block:: python
   :linenos:
   :name: hello_world_complete

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy

   # Step 1: Define a simple routine
   class HelloWorld(Routine):
       """A routine that prints a greeting."""

       def __init__(self):
           super().__init__()
           # Add an input slot (receives data)
           self.add_slot("trigger")
           # Add an output event (sends data)
           self.add_event("greeting", ["message"])

           # Define the logic function
           def say_hello(slot_data, policy_message, worker_state):
               # Print the greeting
               print("Hello, World!")
               # Emit the greeting event
               self.emit("greeting", message="Hello, World!")

           # Set logic and activation policy
           self.set_logic(say_hello)
           self.set_activation_policy(immediate_policy())

   # Step 2: Create a flow and add the routine
   flow = Flow("hello_flow")
   flow.add_routine(HelloWorld(), "greeter")

   # Step 3: Register the flow
   from routilux.monitoring.flow_registry import FlowRegistry
   FlowRegistry.get_instance().register_by_name("hello_flow", flow)

   # Step 4: Execute with Runtime
   with Runtime(thread_pool_size=2) as runtime:
       # Execute the flow
       worker_state = runtime.exec("hello_flow")
       # Trigger the routine by sending data to its slot
       runtime.post(
           "hello_flow",
           "greeter",      # routine name
           "trigger",      # slot name
           {}              # data to send
       )
       # Wait for completion
       runtime.wait_until_all_jobs_finished(timeout=5.0)

**Expected Output**:

.. code-block:: text

   Hello, World!

.. tip:: **Quick Tip: Context Manager**

   Using ``with Runtime() as runtime:`` ensures proper cleanup of thread pools.
   Always use this pattern or call ``runtime.shutdown()`` explicitly.

Breaking It Down
----------------

Let's understand each part of the example.

**Step 1: Define a Routine**

.. code-block:: python
   :linenos:
   :emphasize-lines: 5-7, 16-17

   class HelloWorld(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("trigger")           # Input
           self.add_event("greeting", ["message"])  # Output

           def say_hello(slot_data, policy_message, worker_state):
               print("Hello, World!")
               self.emit("greeting", message="Hello, World!")

           self.set_logic(say_hello)
           self.set_activation_policy(immediate_policy())

A **Routine** is a unit of work that:
- Receives data through **Slots** (input)
- Processes data in a **Logic Function**
- Sends data through **Events** (output)

.. danger:: **CRITICAL: No Constructor Parameters**

   Routines MUST NOT accept constructor parameters (except ``self``):

   .. code-block:: python
      :emphasize-lines: 2

      # WRONG - Will break serialization!
      class MyRoutine(Routine):
          def __init__(self, greeting="Hello"):  # Don't do this!
              super().__init__()

      # RIGHT - Use set_config() instead
      class MyRoutine(Routine):
          def __init__(self):
              super().__init__()
              self.set_config(greeting="Hello")

**Step 2: Create a Flow**

.. code-block:: python
   :linenos:

   flow = Flow("hello_flow")
   flow.add_routine(HelloWorld(), "greeter")

A **Flow** is a container that:
- Holds multiple routines
- Manages connections between them
- Orchestrates execution

.. note:: **Flow Registration**

   Flows MUST be registered with ``FlowRegistry`` before execution.
   Always call ``FlowRegistry.get_instance().register_by_name()``.

**Step 3: Execute with Runtime**

.. code-block:: python
   :linenos:

   with Runtime(thread_pool_size=2) as runtime:
       worker_state = runtime.exec("hello_flow")
       runtime.post("hello_flow", "greeter", "trigger", {})
       runtime.wait_until_all_jobs_finished(timeout=5.0)

A **Runtime**:
- Manages thread pools for execution
- Routes events between routines
- Tracks worker and job state

Understanding the Data Flow
----------------------------

Here's how data flows through your workflow:

.. code-block:: text

   ┌─────────────────────────────────────────────────────────────┐
   │ Runtime                                                      │
   │                                                             │
   │  runtime.post("hello_flow", "greeter", "trigger", {})      │
   │                        │                                   │
   │                        ▼                                   │
   │  ┌─────────────────────────────────────┐                   │
   │  │ Flow: hello_flow                    │                   │
   │  │                                    │                   │
   │  │  ┌────────────────────────────┐    │                   │
   │  │  │ Routine: greeter           │    │                   │
   │  │  │                            │    │                   │
   │  │  │  ┌──────────┐    ┌────────┐│    │                   │
   │  │  │  │ Slot:    │───▶│ Logic: ││    │                   │
   │  │  │  │ trigger  │    │say_hello│   │                   │
   │  │  │  └──────────┘    │        ││    │                   │
   │  │  │                  │        ││    │                   │
   │  │  │                  └───┬────┘│    │                   │
   │  │  │                      │     │    │                   │
   │  │  │                      ▼     │    │                   │
   │  │  │              ┌───────────┐ │    │                   │
   │  │  │              │Event:     │ │    │                   │
   │  │  │              │greeting   │ │    │                   │
   │  │  │              └───────────┘ │    │                   │
   │  │  └────────────────────────────┘    │                   │
   │  └─────────────────────────────────────┘                   │
   └─────────────────────────────────────────────────────────────┘

   1. runtime.post() sends data to "greeter" routine's "trigger" slot
   2. Slot receives data, activates the routine
   3. Logic function executes (prints "Hello, World!")
   4. Routine emits "greeting" event
   5. Runtime routes event to any connected slots

Common Pitfalls
---------------

.. warning:: **Pitfall 1: Forgetting super().__init__()**

   Always call ``super().__init__()`` first in your routine's ``__init__``:

   .. code-block:: python

      class MyRoutine(Routine):
          def __init__(self):
              # Missing: super().__init__()!
              self.add_slot("input")  # This will fail

   **Solution**:

   .. code-block:: python

      class MyRoutine(Routine):
          def __init__(self):
              super().__init__()  # Must be first!
              self.add_slot("input")

.. warning:: **Pitfall 2: Not Setting Activation Policy**

   Routines without an activation policy will never execute:

   .. code-block:: python
      :emphasize-lines: 7

      class MyRoutine(Routine):
          def __init__(self):
              super().__init__()
              self.add_slot("input")
              self.add_event("output")
              self.set_logic(process)
              # Missing: self.set_activation_policy(immediate_policy())!

   **Solution**: Always set an activation policy.

.. warning:: **Pitfall 3: Not Registering Flow**

   Forgetting to register the flow causes ``ValueError``:

   .. code-block:: python
      :emphasize-lines: 2

      flow = Flow("my_flow")
      # Missing: FlowRegistry.get_instance().register_by_name("my_flow", flow)
      runtime.exec("my_flow")  # ValueError: Flow not found!

   **Solution**: Always register flows before execution.

.. warning:: **Pitfall 4: Using Constructor Parameters**

   Routines MUST NOT accept constructor parameters:

   .. code-block:: python
      :emphasize-lines: 2

      # WRONG - Breaks serialization!
      class Greeter(Routine):
          def __init__(self, name="World"):
              super().__init__()

   **Solution**: Use ``set_config()`` instead:

   .. code-block:: python

      # RIGHT
      class Greeter(Routine):
          def __init__(self):
              super().__init__()
              self.set_config(name="World")

              # Then in logic:
              def greet(slot_data, policy_message, worker_state):
                  name = self.get_config("name", "World")
                  print(f"Hello, {name}!")

Best Practices
--------------

1. **Use context managers** for Runtime to ensure proper cleanup
2. **Always set activation policies** or routines won't execute
3. **Always register flows** before execution
4. **Use descriptive names** for routines, slots, and events
5. **Wait for completion** before checking results

.. tip:: **Naming Convention**

   - Routines: Nouns or noun phrases (``Greeter``, ``DataProcessor``, ``Validator``)
   - Slots: What they receive (``input``, ``data``, ``trigger``)
   - Events: What they send (``output``, ``result``, ``greeting``)

Next Steps
----------

You've created your first Routilux workflow! Here's what to learn next:

1. **Connecting Routines**: :doc:`basics/understanding_slots_events`
   - Learn how to connect multiple routines together
   - Understand data flow between routines

2. **Activation Policies**: :doc:`activation/immediate_policy`
   - Learn when routines execute
   - Control execution timing with different policies

3. **State Management**: :doc:`state/worker_state`
   - Track data across routine executions
   - Understand WorkerState vs JobContext

4. **Error Handling**: :doc:`error_handling/error_strategies`
   - Handle errors gracefully
   - Build resilient workflows

.. note:: **Tutorial Structure**

   The tutorials are designed to be followed in order. Each tutorial builds
   on concepts from previous tutorials. If you're new to Routilux, we recommend
   starting with :doc:`basics/understanding_routines` and progressing through
   the basics section.
