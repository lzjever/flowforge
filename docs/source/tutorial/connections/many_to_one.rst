Many-to-One Connections (Fan-In)
=================================

Fan-in is the complementary pattern to fan-out: multiple events connect to a
single slot, allowing data from multiple sources to be aggregated, collected,
or processed together.

.. note:: **What You'll Learn**

   - How to connect multiple events to one slot
   - Building aggregation and collection patterns
   - Using batch_size_policy for aggregation
   - Order considerations and best practices

.. note:: **Prerequisites**

   - :doc:`simple_connection` - Understand simple connections first
   - :doc:`one_to_many` - Understand fan-out patterns

Understanding Fan-In
-------------------

In a fan-in pattern, multiple routines' events connect to one routine's slot:

.. code-block:: text

   ┌──────────┐                ┌──────────┐                ┌──────────┐
   │ Source A │                │ Source B │                │ Source C │
   └─────┬────┘                └─────┬────┘                └─────┬────┘
         │                          │                          │
         │ emit()                   │ emit()                   │ emit()
         │ "result"                 │ "result"                 │ "result"
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                                    ▼
                             ┌──────────┐
                             │Aggregator│
                             │  Slot:   │
                             │ "input"  │
                             └──────────┘

**Key Characteristics**:

- **Multiple events** → **One slot**
- **Mixed data** from different sources
- **Queue maintains order** by arrival time
- **Batch processing** often used with batch_size_policy

Basic Fan-In Example
--------------------

.. code-block:: python
   :linenos:
   :name: connections_many_to_one_basic

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy, batch_size_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   import random

   # Multiple producer routines
   class DataProducer(Routine):
       def __init__(self, producer_id):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("item", ["producer_id", "value"])
           self.set_config(producer_id=producer_id)

           def produce(slot_data, policy_message, worker_state):
               value = random.randint(1, 100)
               pid = self.get_config("producer_id")
               print(f"Producer {pid}: Generated {value}")
               self.emit("item", producer_id=pid, value=value)

           self.set_logic(produce)
           self.set_activation_policy(immediate_policy())

   # Aggregator routine
   class DataAggregator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")
           self.add_event("summary", ["count", "sum", "average", "sources"])

           def aggregate(slot_data, policy_message, worker_state):
               items_list = slot_data.get("items", [])
               if items_list:
                   # Calculate statistics
                   count = len(items_list)
                   values = [item.get("value", 0) for item in items_list]
                   total = sum(values)
                   average = total / count if count > 0 else 0
                   sources = list(set(item.get("producer_id") for item in items_list))

                   print(f"\nAggregator: Processing batch of {count} items")
                   print(f"  Values: {values}")
                   print(f"  Sum: {total}, Average: {average:.1f}")
                   print(f"  Sources: {sources}\n")

                   self.emit("summary",
                            count=count,
                            sum=total,
                            average=round(average, 2),
                            sources=sources)

           self.set_logic(aggregate)
           # Wait for 5 items before processing
           self.set_activation_policy(batch_size_policy(5))

   # Build fan-in flow
   flow = Flow("multi_producer_aggregator")

   # Add multiple producers
   flow.add_routine(DataProducer(1), "producer1")
   flow.add_routine(DataProducer(2), "producer2")
   flow.add_routine(DataProducer(3), "producer3")

   # Add aggregator
   flow.add_routine(DataAggregator(), "aggregator")

   # FAN-IN: All producers → single aggregator
   flow.connect("producer1", "item", "aggregator", "items")
   flow.connect("producer2", "item", "aggregator", "items")
   flow.connect("producer3", "item", "aggregator", "items")

   FlowRegistry.get_instance().register_by_name("multi_producer_aggregator", flow)

   with Runtime(thread_pool_size=4) as runtime:
       runtime.exec("multi_producer_aggregator")

       # Trigger all producers multiple times
       for _ in range(10):
           for producer_id in ["producer1", "producer2", "producer3"]:
               runtime.post("multi_producer_aggregator", producer_id, "trigger", {})

       runtime.wait_until_all_jobs_finished(timeout=10.0)

**Expected Output**:

.. code-block:: text

   Producer 1: Generated 42
   Producer 2: Generated 17
   Producer 3: Generated 89
   Producer 1: Generated 55
   Aggregator: Processing batch of 5 items
     Values: [42, 17, 89, 55]
     Sum: 203, Average: 50.8
     Sources: ['producer1', 'producer2', 'producer3']

   Producer 2: Generated 33
   Producer 3: Generated 91
   ...

Using batch_size_policy for Aggregation
----------------------------------------

The ``batch_size_policy`` is perfect for fan-in aggregation:

.. code-block:: python

   from routilux.activation_policies import batch_size_policy

   class BatchCollector(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")
           self.add_event("batch", ["items", "batch_size"])

           def collect(slot_data, policy_message, worker_state):
               items = slot_data.get("items", [])
               print(f"Collected batch of {len(items)} items")
               self.emit("batch", items=items, batch_size=len(items))

           self.set_logic(collect)
           # Wait for exactly 10 items
           self.set_activation_policy(batch_size_policy(10))

.. note:: **How batch_size_policy Works**

   1. Monitors slot queue size
   2. When queue reaches specified size (10), activates routine
   3. Consumes all items from the slot
   4. Passes items to logic function

   This is ideal for:
   - Batching database writes
   - Chunking API requests
   - Collecting metrics

Aggregation Patterns
--------------------

**Pattern 1: Summation**

.. code-block:: python

   class SumAggregator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("numbers")
           self.add_event("total", ["sum"])

           def sum_logic(slot_data, policy_message, worker_state):
               items = slot_data.get("numbers", [])
               total = sum(item.get("value", 0) for item in items)
               print(f"Sum: {total}")
               self.emit("total", sum=total)

           self.set_logic(sum_logic)
           self.set_activation_policy(batch_size_policy(10))

**Pattern 2: List Collection**

.. code-block:: python

   class ListCollector(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")
           self.add_event("collected", ["items", "count"])

           def collect_logic(slot_data, policy_message, worker_state):
               items = slot_data.get("items", [])
               # Just collect all items
               result = [item.get("data") for item in items]
               print(f"Collected {len(result)} items")
               self.emit("collected", items=result, count=len(result))

           self.set_logic(collect_logic)
           self.set_activation_policy(batch_size_policy(20))

**Pattern 3: Unique Collection**

.. code-block:: python

   class UniqueCollector(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")

           def unique_logic(slot_data, policy_message, worker_state):
               items = slot_data.get("items", [])
               # Collect unique values
               unique = set(item.get("value") for item in items)
               print(f"Unique values: {sorted(unique)}")

               # Track in worker state
               state = worker_state.get_routine_state("collector") or {}
               all_unique = state.get("unique_set", set())
               all_unique.update(unique)
               worker_state.update_routine_state("collector", {
                   "unique_set": all_unique
               })

           self.set_logic(unique_logic)
           self.set_activation_policy(batch_size_policy(10))

**Pattern 4: Key-Grouped Aggregation**

.. code-block:: python

   class GroupedAggregator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("items")
           self.add_event("grouped", ["groups"])

           def group_logic(slot_data, policy_message, worker_state):
               items = slot_data.get("items", [])
               # Group by key
               groups = {}
               for item in items:
                   key = item.get("category", "unknown")
                   if key not in groups:
                       groups[key] = []
                   groups[key].append(item.get("value"))

               # Calculate per-group statistics
               for group_name, values in groups.items():
                   total = sum(values)
                   avg = total / len(values) if values else 0
                   print(f"Group '{group_name}': count={len(values)}, sum={total}, avg={avg:.1f}")

               self.emit("grouped", groups=list(groups.keys()))

           self.set_logic(group_logic)
           self.set_activation_policy(batch_size_policy(15))

Source Identification in Fan-In
--------------------------------

When aggregating from multiple sources, identify each source:

.. code-block:: python
   :linenos:

   class TaggedProducer(Routine):
       def __init__(self, region):
           super().__init__()
           self.add_slot("trigger")
           self.add_event("metric", ["region", "metric_name", "value"])
           self.set_config(region=region)

           def produce(slot_data, policy_message, worker_state):
               region = self.get_config("region")
               import random, time
               metric = {
                   "region": region,
                   "metric_name": "cpu_usage",
                   "value": random.random() * 100,
                   "timestamp": time.time()
               }
               self.emit("metric", **metric)

           self.set_logic(produce)
           self.set_activation_policy(immediate_policy())

   class RegionalAggregator(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("metrics")
           self.add_event("summary", ["by_region"])

           def aggregate(slot_data, policy_message, worker_state):
               items = slot_data.get("metrics", [])

               # Group by region
               by_region = {}
               for item in items:
                   region = item.get("region", "unknown")
                   if region not in by_region:
                       by_region[region] = {"values": [], "count": 0}
                   by_region[region]["values"].append(item.get("value", 0))
                   by_region[region]["count"] += 1

               # Calculate per-region stats
               for region, data in by_region.items():
                   values = data["values"]
                   avg = sum(values) / len(values) if values else 0
                   print(f"Region {region}: {data['count']} metrics, avg={avg:.1f}%")

               self.emit("summary", by_region=by_region)

           self.set_logic(aggregate)
           self.set_activation_policy(batch_size_policy(10))

   # Build regional monitoring flow
   flow = Flow("regional_monitoring")

   regions = ["us-east", "us-west", "eu-west", "ap-southeast"]

   for region in regions:
       flow.add_routine(TaggedProducer(region), f"producer_{region}")

   flow.add_routine(RegionalAggregator(), "aggregator")

   # Fan-in: All regional producers → single aggregator
   for region in regions:
       flow.connect(f"producer_{region}", "metric", "aggregator", "metrics")

   FlowRegistry.get_instance().register_by_name("regional_monitoring", flow)

Complete Example: Map-Reduce Pattern
-------------------------------------

A classic map-reduce uses fan-in for the reduce phase:

.. code-block:: python
   :linenos:
   :name: connections_many_to_one_mapreduce

   from routilux import Routine, Flow, Runtime
   from routilux.activation_policies import immediate_policy, batch_size_policy
   from routilux.monitoring.flow_registry import FlowRegistry
   import string

   # Map phase: Count words in documents
   class DocumentMapper(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("document")
           self.add_event("word_counts", ["doc_id", "counts"])

           def map_logic(slot_data, policy_message, worker_state):
               doc_list = slot_data.get("document", [])
               if doc_list:
                   doc = doc_list[0]
                   doc_id = doc.get("doc_id")
                   text = doc.get("text", "")

                   # Count words (simple split)
                   words = text.lower().split()
                   # Remove punctuation
                   words = [word.strip(string.punctuation) for word in words]
                   # Count occurrences
                   counts = {}
                   for word in words:
                       if word:
                           counts[word] = counts.get(word, 0) + 1

                   print(f"Mapper: Doc {doc_id} has {len(counts)} unique words")
                   self.emit("word_counts", doc_id=doc_id, counts=counts)

           self.set_logic(map_logic)
           self.set_activation_policy(immediate_policy())

   # Shuffle phase: Group words by key
   class WordShuffler(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("word_counts")
           self.add_event("grouped", ["word", "doc_counts"])

           def shuffle_logic(slot_data, policy_message, worker_state):
               items = slot_data.get("word_counts", [])

               # Invert: word -> list of (doc_id, count)
               word_to_docs = {}
               for item in items:
                   doc_id = item.get("doc_id")
                   counts = item.get("counts", {})

                   for word, count in counts.items():
                       if word not in word_to_docs:
                           word_to_docs[word] = []
                       word_to_docs[word].append({"doc_id": doc_id, "count": count})

               # Emit grouped data
               for word, doc_counts in word_to_docs.items():
                   self.emit("grouped", word=word, doc_counts=doc_counts)

           self.set_logic(shuffle_logic)
           self.set_activation_policy(batch_size_policy(3))

   # Reduce phase: Sum counts per word
   class WordReducer(Routine):
       def __init__(self):
           super().__init__()
           self.add_slot("grouped")

           def reduce_logic(slot_data, policy_message, worker_state):
               items = slot_data.get("grouped", [])
               if items:
                   item = items[0]
                   word = item.get("word")
                   doc_counts = item.get("doc_counts", [])

                   # Sum all counts for this word
                   total = sum(d.get("count", 0) for d in doc_counts)
                   print(f"Reducer: '{word}' appears {total} times across {len(doc_counts)} docs")

           self.set_logic(reduce_logic)
           self.set_activation_policy(immediate_policy())

   # Build map-reduce flow
   flow = Flow("word_count_mapreduce")

   # Add mappers
   for i in range(3):
       flow.add_routine(DocumentMapper(), f"mapper_{i}")

   # Add shuffler and reducer
   flow.add_routine(WordShuffler(), "shuffler")
   flow.add_routine(WordReducer(), "reducer")

   # Fan-in: All mappers → shuffler
   for i in range(3):
       flow.connect(f"mapper_{i}", "word_counts", "shuffler", "word_counts")

   # Connect shuffler to reducer
   flow.connect("shuffler", "grouped", "reducer", "grouped")

   FlowRegistry.get_instance().register_by_name("word_count_mapreduce", flow)

   # Sample documents
   documents = [
       {"doc_id": 1, "text": "the quick brown fox jumps over the lazy dog"},
       {"doc_id": 2, "text": "the lazy dog sleeps while the fox jumps"},
       {"doc_id": 3, "text": "quick brown foxes and lazy dogs are friends"},
   ]

   with Runtime(thread_pool_size=6) as runtime:
       runtime.exec("word_count_mapreduce")

       # Send documents to mappers
       for i, doc in enumerate(documents):
           runtime.post("word_count_mapreduce", f"mapper_{i}", "document", doc)

       runtime.wait_until_all_jobs_finished(timeout=10.0)

**Expected Output**:

.. code-block:: text

   Mapper: Doc 1 has 8 unique words
   Mapper: Doc 2 has 7 unique words
   Mapper: Doc 3 has 9 unique words
   Reducer: 'the' appears 4 times across 2 docs
   Reducer: 'quick' appears 2 times across 2 docs
   Reducer: 'brown' appears 2 times across 2 docs
   ...

Considerations and Pitfalls
----------------------------

.. warning:: **Pitfall 1: Losing Source Information**

   Without tagging, you can't identify data sources:

   .. code-block:: python

      # WRONG - No source identification
      self.emit("data", value=42)  # Where did this come from?

      # RIGHT - Include source
      self.emit("data", source="producer_a", value=42)

.. warning:: **Pitfall 2: Assuming Arrival Order**

   Slots maintain FIFO order, but concurrent sends may interleave:

   .. code-block:: python

      # Don't assume all from A come before all from B
      # Order depends on timing and concurrency

   **Solution**: Use timestamps or sequence numbers for ordering:

   .. code-block:: python

      import time
      self.emit("event", data=value, timestamp=time.time(), seq=counter)

.. warning:: **Pitfall 3: Large Batch Sizes**

   Too-large batch sizes cause memory issues:

   .. code-block:: python

      # Potentially problematic
      self.set_activation_policy(batch_size_policy(10000))

   **Solution**: Use reasonable batch sizes (10-1000 typical):

   .. code-block:: python

      # Better - Tune based on your data size
      self.set_activation_policy(batch_size_policy(100))

.. warning:: **Pitfall 4: Unbounded Queues**

   Without batch_size_policy, queues grow unbounded:

   .. code-block:: python

      # WRONG - Queue grows forever
      self.set_activation_policy(immediate_policy())  # Processes immediately
      # But if consumer is slow, queue still grows!

   **Solution**: Use appropriate queue limits and batch processing:

   .. code-block:: python

      # Right - Bounded queue + batch processing
      self.add_slot("items", max_queue_length=1000)
      self.set_activation_policy(batch_size_policy(50))

Next Steps
----------

Learn about combining fan-out and fan-in:

- :doc:`complex_patterns` - Diamond, branching, and combined patterns
- :doc:`../data_flow/parameter_mapping` - Advanced data routing
- :doc:`../activation/batch_size` - Detailed batch processing

.. seealso::

   :doc:`../../cookbook/data_processing_pipeline`
      Complete data processing pipeline patterns

   :doc:`../../api_reference/activation_policies`
      Complete activation policy reference
