# Routilux

[![PyPI version](https://badge.fury.io/py/routilux.svg)](https://badge.fury.io/py/routilux)
[![Python versions](https://img.shields.io/pypi/pyversions/routilux.svg)](https://pypi.org/project/routilux/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Routilux** is an event-driven workflow orchestration framework for Python. It provides flexible workflow execution with connection management, state tracking, and real-time monitoring capabilities.

## Features

- **Event-Driven Architecture**: Routines communicate via events (output) and slots (input)
- **Flexible State Management**: Worker-level persistent state and job-level temporary state
- **Zero-Overhead Monitoring**: Optional monitoring with no performance impact when disabled
- **Activation Policies**: Control when routines execute (immediate, batch, time-based, custom)
- **Thread-Safe Execution**: Built-in thread pool management with automatic event routing
- **Serialization**: Full support for flow serialization and distribution
- **Debugging**: Built-in breakpoint support and interactive debugging
- **HTTP API**: Optional FastAPI-based REST API for remote management

## Installation

```bash
pip install routilux
```

## Quick Start

```python
from routilux import Routine, Flow, Runtime, FlowBuilder
from routilux.activation_policies import immediate_policy

# Define a simple routine
class HelloWorld(Routine):
    def __init__(self):
        super().__init__()
        self.add_slot("trigger")
        self.add_event("greeting")
        self.set_activation_policy(immediate_policy())

        def say_hello(trigger_data, **kwargs):
            print("Hello, World!")
            self.emit("greeting", message="Hello, World!")

        self.set_logic(say_hello)

# Build the flow
flow = (FlowBuilder("hello_flow")
    .add_routine(HelloWorld(), "greeter")
    .build())

# Execute the flow
with Runtime(thread_pool_size=2) as runtime:
    runtime.exec("hello_flow")
    runtime.post("hello_flow", "greeter", "trigger", {})
    runtime.wait_until_all_jobs_finished(timeout=5.0)
```

## Key Concepts

### Routines

Routines are the building blocks of workflows. Each routine:
- Defines input **slots** (data receivers)
- Defines output **events** (data emitters)
- Contains **logic** functions for processing
- Must NOT accept constructor parameters (for serialization)

### Flows

Flows orchestrate multiple routines:
- Contain routines with unique IDs
- Define connections between events and slots
- Manage execution lifecycle

### Runtime

The Runtime executes flows:
- Manages thread pools
- Routes events between routines
- Tracks WorkerState (persistent) and JobContext (temporary)

## Documentation

- [Documentation](https://routilux.readthedocs.io/)
- [API Reference](https://routilux.readthedocs.io/en/latest/api_reference.html)
- [Examples](https://routilux.readthedocs.io/en/latest/examples.html)

## Development

```bash
# Clone the repository
git clone https://github.com/lzjever/routilux.git
cd routilux

# Install in development mode
pip install -e ".[dev]"

# Run tests
make test

# Run linting
make lint

# Build documentation
make docs
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
