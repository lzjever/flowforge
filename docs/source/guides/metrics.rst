Metrics and Monitoring
======================

Routilux provides Prometheus-compatible metrics export for production monitoring
of flow and routine execution.

Overview
--------

The metrics module provides four metric types:

- **Counter**: A monotonically increasing counter (e.g., total executions)
- **Gauge**: A value that can go up or down (e.g., active jobs)
- **Histogram**: Tracks count, sum, and bucket distributions (e.g., duration)
- **MetricTimer**: Context manager for timing operations

All metrics are thread-safe and can be exported in Prometheus text format.

Basic Usage
-----------

Creating Metrics
~~~~~~~~~~~~~~~~

Use a ``MetricsCollector`` to create and manage metrics:

.. code-block:: python

    from routilux import MetricsCollector, Counter, Gauge, Histogram

    collector = MetricsCollector()

    # Create a counter for tracking total executions
    executions = collector.counter("flow_executions_total", "Total flow executions")
    executions.inc()
    executions.inc(5)  # Increment by custom amount

    # Create a gauge for tracking active jobs
    active_jobs = collector.gauge("active_jobs", "Number of active jobs")
    active_jobs.set(10)
    active_jobs.inc(2)   # Increment
    active_jobs.dec(1)   # Decrement

    # Create a histogram for tracking duration
    duration = collector.histogram("flow_duration_seconds", "Flow execution duration")
    duration.observe(0.5)
    duration.observe(1.2)
    duration.observe(0.8)

Using MetricTimer
~~~~~~~~~~~~~~~~~

The ``MetricTimer`` context manager simplifies timing operations:

.. code-block:: python

    from routilux import MetricsCollector, MetricTimer

    collector = MetricsCollector()
    duration_histogram = collector.histogram("operation_duration_seconds", "Operation duration")

    with MetricTimer(duration_histogram):
        # Your code here
        result = some_operation()

    # Duration is automatically recorded to the histogram

Labeled Metrics
~~~~~~~~~~~~~~~

Metrics can have labels for multi-dimensional tracking:

.. code-block:: python

    from routilux import MetricsCollector

    collector = MetricsCollector()

    # Create labeled metrics
    success_counter = collector.counter(
        "routine_executions_total",
        "Total routine executions",
        labels={"status": "success"}
    )
    failure_counter = collector.counter(
        "routine_executions_total",
        "Total routine executions",
        labels={"status": "failure"}
    )

    success_counter.inc()
    failure_counter.inc()

Exporting Metrics
-----------------

Prometheus Format
~~~~~~~~~~~~~~~~~

Export all metrics in Prometheus text format:

.. code-block:: python

    from routilux import MetricsCollector

    collector = MetricsCollector()

    # Add some metrics...
    counter = collector.counter("requests_total", "Total requests")
    counter.inc(42)

    gauge = collector.gauge("temperature", "Current temperature")
    gauge.set(23.5)

    histogram = collector.histogram("response_time_seconds", "Response time")
    histogram.observe(0.1)
    histogram.observe(0.2)

    # Export to Prometheus format
    prometheus_output = collector.export_prometheus()
    print(prometheus_output)

Output example:

.. code-block:: text

    # HELP requests_total Total requests
    # TYPE requests_total counter
    requests_total 42

    # HELP temperature Current temperature
    # TYPE temperature gauge
    temperature 23.5

    # HELP response_time_seconds Response time
    # TYPE response_time_seconds histogram
    response_time_seconds_bucket{le="0.005"} 0
    response_time_seconds_bucket{le="0.01"} 0
    response_time_seconds_bucket{le="0.025"} 0
    response_time_seconds_bucket{le="0.05"} 0
    response_time_seconds_bucket{le="0.1"} 1
    response_time_seconds_bucket{le="0.25"} 2
    response_time_seconds_bucket{le="0.5"} 2
    response_time_seconds_bucket{le="1.0"} 2
    response_time_seconds_bucket{le="2.5"} 2
    response_time_seconds_bucket{le="5.0"} 2
    response_time_seconds_bucket{le="10.0"} 2
    response_time_seconds_bucket{le="+Inf"} 2
    response_time_seconds_sum 0.3
    response_time_seconds_count 2

Integration with Flow
---------------------

Flow objects have a ``metrics_collector`` attribute that can be set to track
execution metrics:

.. code-block:: python

    from routilux import Flow, MetricsCollector

    # Create flow and metrics collector
    flow = Flow()
    collector = MetricsCollector()

    # Enable metrics collection
    flow.metrics_collector = collector

    # Execute flows normally...
    job_state = flow.execute(entry_id, entry_params={"data": "test"})
    flow.wait_for_completion(job_state)

    # Access collected metrics
    output = collector.export_prometheus()

Custom Histogram Buckets
-------------------------

You can customize histogram bucket boundaries:

.. code-block:: python

    from routilux import MetricsCollector

    collector = MetricsCollector()

    # Custom buckets in seconds
    custom_buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]

    histogram = collector.histogram(
        "custom_duration_seconds",
        "Custom duration with custom buckets",
        buckets=custom_buckets
    )

Best Practices
--------------

1. **Use descriptive metric names**: Follow Prometheus naming conventions
   (e.g., ``_total`` for counters, ``_seconds`` for durations)

2. **Add help text**: Provide clear descriptions for all metrics

3. **Use labels judiciously**: Avoid high-cardinality labels that can explode
   metric count

4. **Thread safety**: All metrics are thread-safe and can be used in concurrent
   executions

5. **Metric lifecycle**: Metrics in a collector persist for the lifetime of
   the collector object

Production Deployment
---------------------

To expose metrics in a production environment:

1. Set up an HTTP endpoint (e.g., using Flask, FastAPI, or Prometheus client library)

2. Export metrics on ``/metrics`` endpoint

3. Configure Prometheus to scrape the endpoint

Example using Flask:

.. code-block:: python

    from flask import Flask
    from routilux import Flow, MetricsCollector

    app = Flask(__name__)
    flow = Flow()
    collector = MetricsCollector()
    flow.metrics_collector = collector

    @app.route("/metrics")
    def metrics():
        return collector.export_prometheus(), 200, {"Content-Type": "text/plain"}

API Reference
-------------

MetricsCollector
~~~~~~~~~~~~~~~~

.. class:: MetricsCollector()

    Registry for collecting and exporting metrics.

    .. method:: counter(name: str, description: str, labels: dict[str, str] | None = None) -> Counter

        Get or create a counter metric.

    .. method:: gauge(name: str, description: str, labels: dict[str, str] | None = None) -> Gauge

        Get or create a gauge metric.

    .. method:: histogram(name: str, description: str, labels: dict[str, str] | None = None, buckets: list[float] | None = None) -> Histogram

        Get or create a histogram metric.

    .. method:: export_prometheus() -> str

        Export all metrics in Prometheus text format.

Counter
~~~~~~~

.. class:: Counter(name: str, description: str, labels: dict[str, str] | None = None)

    A monotonically increasing counter.

    .. method:: inc(amount: float = 1) -> None

        Increment the counter by the given amount (must be positive).

    .. attribute:: value

        Current counter value (read-only).

Gauge
~~~~~

.. class:: Gauge(name: str, description: str, labels: dict[str, str] | None = None)

    A gauge that can go up or down.

    .. method:: set(value: float) -> None

        Set the gauge to the given value.

    .. method:: inc(amount: float = 1) -> None

        Increment the gauge by the given amount.

    .. method:: dec(amount: float = 1) -> None

        Decrement the gauge by the given amount.

    .. attribute:: value

        Current gauge value (read-only).

Histogram
~~~~~~~~~

.. class:: Histogram(name: str, description: str, labels: dict[str, str] | None = None, buckets: list[float] | None = None)

    A histogram that tracks count, sum, and bucket distributions.

    .. method:: observe(value: float) -> None

        Record an observation.

    .. attribute:: count

        Total number of observations (read-only).

    .. attribute:: sum

        Sum of all observations (read-only).

MetricTimer
~~~~~~~~~~~

.. class:: MetricTimer(histogram: Histogram)

    Context manager for timing operations.

    Usage:

    .. code-block:: python

        with MetricTimer(histogram):
            # Your code here
            pass
