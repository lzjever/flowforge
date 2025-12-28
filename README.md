# FlowForge

Event-driven workflow orchestration framework with flexible connection, state management, and workflow orchestration capabilities.

## Features

* **Slots and Events Mechanism**: Clear distinction between input slots and output events
* **Many-to-Many Connections**: Flexible connection relationships between routines
* **State Management**: Unified `stats()` method for tracking routine state
* **Flow Manager**: Workflow orchestration, persistence, and recovery
* **JobState Management**: Execution state recording and recovery functionality
* **Error Handling**: Multiple error handling strategies (STOP, CONTINUE, RETRY, SKIP)
* **Execution Tracking**: Comprehensive execution tracking and performance monitoring
* **Serialization Support**: Full serialization/deserialization support for persistence

## Installation

### For Development (Recommended)

```bash
# Install package in editable mode with development dependencies
pip install -e ".[dev]"

# Or using Makefile
make dev-install
```

This installs the package in "editable" mode, meaning:
- Changes to source code are immediately available
- No need to reinstall after code changes
- All imports work correctly without `sys.path` manipulation

### For Production

```bash
pip install -e .
```

Or install from PyPI (when published):

```bash
pip install flowforge
```

Or install from a built package:

```bash
pip install dist/flowforge-*.whl
```

## Quick Start

### Creating a Routine

```python
from flowforge import Routine

class DataProcessor(Routine):
    def __init__(self):
        super().__init__()
        self.input_slot = self.define_slot("input", handler=self.process_data)
        self.output_event = self.define_event("output", ["result"])
    
    def process_data(self, data: str):
        result = f"Processed: {data}"
        self._stats["processed_count"] = self._stats.get("processed_count", 0) + 1
        self.emit("output", result=result)
```

### Creating and Connecting a Flow

```python
from flowforge import Flow

flow = Flow(flow_id="my_flow")

processor1 = DataProcessor()
processor2 = DataProcessor()

id1 = flow.add_routine(processor1, "processor1")
id2 = flow.add_routine(processor2, "processor2")

flow.connect(id1, "output", id2, "input")
```

### Executing a Flow

```python
job_state = flow.execute(id1, entry_params={"data": "test"})
print(job_state.status)  # "completed"
print(processor1.stats())  # {"processed_count": 1}
```

## Documentation

Full documentation is available at:

* **Online**: [Read the Docs](https://flowforge.readthedocs.io) (when published)
* **Local**: Build with `cd docs && make html`

### Documentation Structure

* **Introduction**: Overview and key concepts
* **Installation**: Installation instructions
* **Quick Start**: Getting started guide
* **User Guide**: Detailed usage instructions
  * Working with Routines
  * Working with Flows
  * Connections
  * State Management
  * Error Handling
  * Serialization
* **API Reference**: Complete API documentation
* **Examples**: Practical code examples
* **Design**: Design documentation and architecture
* **Features**: Feature overview
* **Testing**: Testing information

## Examples

See the `examples/` directory for practical examples:

* `basic_example.py` - Basic routine and flow usage
* `data_processing.py` - Multi-stage data processing pipeline
* `error_handling_example.py` - Error handling strategies
* `state_management_example.py` - State management and tracking

Run examples:

```bash
python examples/basic_example.py
```

## Project Structure

```
flowforge/
├── flowforge/          # Main package
│   ├── routine.py          # Routine base class
│   ├── flow.py             # Flow manager
│   ├── job_state.py        # JobState management
│   ├── connection.py       # Connection management
│   ├── event.py            # Event class
│   ├── slot.py             # Slot class
│   ├── error_handler.py    # Error handler
│   └── execution_tracker.py # Execution tracker
├── tests/                  # Test cases
├── examples/               # Usage examples
├── docs/                    # Sphinx documentation
└── README.md               # This file
```

## Testing

Run tests:

```bash
# All tests
pytest tests/

# With coverage
pytest --cov=flowforge --cov-report=html tests/
```

## Development

### Building Documentation

```bash
pip install -e ".[docs]"
cd docs && make html
```

### Code Formatting

```bash
black flowforge/
flake8 flowforge/
```

## License

FlowForge is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

Copyright (c) 2024 FlowForge Team

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Links

* **Documentation**: See `docs/` directory
* **Examples**: See `examples/` directory
* **Tests**: See `tests/` directory
