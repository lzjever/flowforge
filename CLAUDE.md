# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Routilux is an event-driven workflow orchestration framework for Python 3.8+. It provides flexible connection management, state tracking, and execution control for complex data pipelines and workflows.

**Core Architecture**: Runtime-based execution with event-driven communication between Routines (units of work) through Slots (inputs) and Events (outputs).

## Essential Commands

### Development Setup
```bash
make dev-install    # Install package + all dependencies (recommended)
make setup-venv     # Install dependencies only (for CI/CD, no package)
make install        # Install package only
```

### Testing
```bash
make test           # Run all tests
make test-cov       # Run with coverage report
make test-unit      # Unit tests only (exclude integration)
make test-integration # Integration tests only
make test-api       # API endpoint tests
```

### Code Quality
```bash
make lint           # Ruff linting
make format         # Ruff formatting
make format-check   # Check formatting without changes
make type-check     # MyPy type checking
make check          # Run all checks (lint + format-check + test)
```

### Building & Publishing
```bash
make build          # Build source and wheel distributions
make check-package  # Verify package before upload
make upload         # Upload to PyPI (requires PYPI_TOKEN)
make upload-test    # Upload to TestPyPI (requires TEST_PYPI_TOKEN)
```

### Documentation
```bash
make docs           # Build Sphinx documentation
make html           # Build HTML docs
```

### Package Manager
- **Primary**: `uv` (Rust-based, fast) - automatically detected and used if available
- **Fallback**: `pip` if `uv` is not installed
- To install `uv`: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Architecture Overview

### Core Components

1. **Runtime** (`routilux/runtime.py`): Centralized execution manager with shared thread pool
   - Manages all flow executions
   - Thread-safe job registry
   - Non-blocking execution (`exec()` returns immediately)
   - Event routing to connected slots

2. **Flow** (`routilux/flow/`): Workflow definition container
   - Holds routines and their connections
   - Manages flow-level configuration (error handlers)
   - Registered in FlowRegistry for Runtime access

3. **Routine** (`routilux/routine.py`): Unit of work
   - Defines **Slots** (input queues)
   - Defines **Events** (output emitters)
   - Has **activation policy** (when to execute)
   - Has **logic function** (what to execute)

4. **Slot** (`routilux/slot.py`): Input queue for receiving data
   - Thread-safe queue with configurable capacity
   - Routes data from connected events

5. **Event** (`routilux/event.py`): Output mechanism for transmitting data
   - Non-blocking emission
   - Broadcasts to multiple connected slots

6. **JobState** (`routilux/job_state.py`): Execution state tracking
   - Isolated from routine instances
   - Tracks execution status per routine
   - Supports serialization for workflow resumption

### Execution Model

- **Activation Policies** (`routilux/activation_policies.py`): Declarative control over when routines execute
  - `immediate_policy()`: Execute immediately when any slot receives data
  - `all_slots_ready_policy()`: Execute when all slots have at least one item
  - `batch_size_policy(n)`: Execute when all slots have at least n items
  - `time_interval_policy(seconds)`: Execute at most once per interval
  - `custom_policy(function)`: Define your own logic

- **Unified Task Queue**: Both sequential and concurrent modes use queue-based execution
- **Thread Safety**: All operations are thread-safe by design using RLocks
- **ContextVars**: Used for thread-local job_state access

### Package Structure

```
routilux/
├── analysis/           # AST-based code analysis and visualization
├── api/                # FastAPI web interface (optional dependency)
├── builtin_routines/   # Built-in routine implementations
├── dsl/                # Domain-specific language for config files
├── factory/            # Object factory pattern for instantiation
├── flow/               # Flow management and builder
├── monitoring/         # Debugging & monitoring (zero-overhead when disabled)
├── testing/            # Testing utilities (RoutineTester)
├── activation_policies.py  # Policy implementations
├── connection.py       # Event-to-slot wiring
├── error_handler.py    # Error handling strategies
├── event.py            # Event emission
├── job_executor.py     # Per-job execution context
├── job_manager.py      # Global job management
├── job_state.py        # Execution state tracking
├── output_handler.py   # Output handling strategies
├── routine.py          # Routine base class
├── runtime.py          # Central execution manager
├── slot.py             # Input queues
├── status.py           # Status enums
└── __init__.py         # Public API exports
```

## Critical Constraints

### DO NOT Accept Constructor Parameters

Routines MUST have a parameterless constructor for serialization support:

```python
# ❌ WRONG - Will break serialization
class MyRoutine(Routine):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

# ✅ CORRECT - Use _config dictionary
class MyRoutine(Routine):
    def __init__(self):
        super().__init__()
        self.set_config(name="my_routine", timeout=30)
```

### DO NOT Modify Instance Variables During Execution

The same routine object can execute concurrently in multiple threads. All execution state MUST be stored in JobState:

```python
# ❌ WRONG - Breaks execution isolation
def logic(slot_data, policy_message, job_state):
    self.counter += 1  # Data race!

# ✅ CORRECT - Use JobState
def logic(slot_data, policy_message, job_state):
    counter = job_state.get_routine_state(routine_id, {}).get("count", 0)
    job_state.update_routine_state(routine_id, {"count": counter + 1})
```

**State Management Rules**:
- `_config`: Read-only configuration (set during initialization, read during execution)
- `JobState`: All mutable execution state (per-execution isolation)
- `job_state.shared_data`: Cross-routine shared data
- `job_state.shared_log`: Shared execution log

## Code Style

- **Line Length**: 100 characters
- **Quotes**: Double quotes
- **Formatter/Linter**: Ruff (replaces flake8 + black)
- **Type Checker**: MyPy (optional, not enforced)
- **Python Version**: 3.8+ (supports up to 3.14)

Ruff rules enabled: `E`, `F`, `I`, `N`, `W`, `UP`

## Testing

- **Framework**: pytest
- **Markers**: `@integration` for integration tests, `@timeout` for timeout
- **Test Directory**: `tests/`
- **Coverage**: `pytest-cov` with HTML output

Run single test: `pytest tests/test_specific_file.py::test_function_name -v`

## Key Patterns

### Defining a Routine

```python
from routilux import Routine
from routilux.activation_policies import immediate_policy

class MyRoutine(Routine):
    def __init__(self):
        super().__init__()
        # Define inputs
        self.input = self.define_slot("input")
        # Define outputs with schema
        self.output = self.define_event("output", ["result"])
        # Set logic function
        self.set_logic(self._logic)
        # Set activation policy
        self.set_activation_policy(immediate_policy())
        # Set configuration (read-only)
        self.set_config(name="my_routine")

    def _logic(self, slot_data, policy_message, job_state):
        # slot_data: dict mapping slot names to list of data items
        # policy_message: policy-specific metadata
        # job_state: current JobState for this execution
        data = slot_data["input"][0] if slot_data.get("input") else None
        # Emit output (non-blocking)
        self.emit("output", result=processed_data)
```

### Flow Setup with Runtime

```python
from routilux import Flow, Runtime
from routilux.monitoring.flow_registry import FlowRegistry

# Create flow
flow = Flow(flow_id="my_pipeline")
flow.add_routine(source_routine, "source")
flow.add_routine(processor_routine, "processor")
flow.connect("source", "output", "processor", "input")

# Register for Runtime access
registry = FlowRegistry.get_instance()
registry.register_by_name("my_pipeline", flow)

# Execute
runtime = Runtime(thread_pool_size=10)
job_state = runtime.exec("my_pipeline", entry_params={"data": "hello"})
runtime.wait_until_all_jobs_finished(timeout=5.0)
runtime.shutdown(wait=True)
```

### Error Handling

Error strategies: `STOP`, `CONTINUE`, `RETRY`, `SKIP`

```python
from routilux import ErrorHandler, ErrorStrategy

flow.set_error_handler(
    ErrorHandler(
        strategy=ErrorStrategy.RETRY,
        max_retries=3,
        retry_delay=1.0
    )
)
```

## Serialization

The framework uses `serilux` for serialization. Routines are serializable if they follow the parameterless constructor constraint. JobState can be saved/resumed:

```python
job_state.save("state.json")
saved_state = JobState.load("state.json")
runtime.exec("my_flow", job_state=saved_state)
```

## Related Projects

- **[Varlord](https://github.com/lzjever/varlord)**: Configuration management
- **[Serilux](https://github.com/lzjever/serilux)**: Serialization framework
- **[Lexilux](https://github.com/lzjever/lexilux)**: LLM API client

## Optional Features

### API Server
FastAPI-based web interface (requires `[api]` extra):
```bash
pip install routilux[api]
```

### Monitoring
Zero-overhead monitoring when disabled. Enable via:
```python
from routilux.monitoring import enable_monitoring
enable_monitoring()
```
