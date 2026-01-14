# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Routilux** is an event-driven workflow orchestration framework for Python (3.8-3.14) that provides flexible workflow building with state management, error handling, and execution tracking. It's part of the Agentsmith open-source ecosystem (along with Varlord, Serilux, and Lexilux).

### Core Architecture

Routilux uses an **event queue architecture** (v0.9.0+) with these key concepts:

- **Routine**: Base class for workflow nodes with Slots (inputs) and Events (outputs)
- **Flow**: Container managing multiple Routines, connecting Events to Slots
- **JobState**: Execution state tracking, completely decoupled from Flow
- **Connection**: Many-to-many relationships between Events and Slots
- **Event Queue**: Unified execution model for sequential and concurrent modes

**Critical architectural change (v0.9.0)**:
- `emit()` is **always non-blocking** - returns immediately after enqueuing tasks
- Flow and JobState are **completely decoupled** - Flow no longer stores execution state
- Each `Flow.execute()` call returns an independent JobState that you must manage
- Automatic flow detection - `emit()` retrieves flow from routine context

### Project Structure

```
routilux/
├── routilux/              # Main package
│   ├── routine.py         # Routine base class
│   ├── flow/              # Flow management subsystem
│   │   ├── flow.py        # Main Flow class
│   │   ├── execution.py   # Sequential/concurrent execution
│   │   ├── event_loop.py  # Event loop and task queue
│   │   ├── state_management.py  # Pause/resume/cancel
│   │   └── task.py        # TaskPriority, SlotActivationTask
│   ├── event.py           # Event (output) mechanism
│   ├── slot.py            # Slot (input) mechanism
│   ├── connection.py      # Connection management
│   ├── error_handler.py   # Error handling strategies
│   ├── job_state.py       # Execution state tracking
│   ├── execution_tracker.py # Performance metrics
│   ├── api/               # FastAPI server (monitoring/debugging)
│   ├── dsl/               # YAML/JSON DSL loader
│   ├── monitoring/        # Debug/breakpoint system
│   └── testing/           # Testing utilities
├── tests/                 # Core test suite
├── examples/              # Usage examples (12 demos)
├── docs/                  # Sphinx documentation
└── pyproject.toml         # Project configuration
```

## Development Commands

### Setup

```bash
# Recommended: For active development
make dev-install           # Install package + all dependencies using uv

# Alternative: Dependencies only (for CI/CD or code review)
make setup-venv            # Install dependencies only (no package)
make install               # Install package after setup-venv
```

**Note**: This project uses [uv](https://github.com/astral-sh/uv) for fast dependency management. All Makefile commands automatically use `uv` if available, otherwise fall back to `pip`.

### Testing

```bash
make test                  # Run all tests
make test-cov              # Run with coverage report
make test-integration      # Run integration tests (requires external services)

# Direct pytest usage
pytest tests/              # Run all tests
```

**Test markers**: `unit`, `integration`, `slow`, `persistence`, `resume`
- Integration tests are excluded by default

### Code Quality

```bash
make lint                  # Run ruff linting
make format                # Format code with ruff
make format-check          # Check formatting without modifying
make check                 # Run all checks (lint + format-check + test)
```

**Ruff configuration**:
- Line length: 100 characters
- Target version: Python 3.8+
- Lint rules: E, F, I, N, W, UP

### Building & Publishing

```bash
make build                 # Build source and wheel distributions
make check-package         # Validate package with twine
make upload                # Upload to PyPI (requires PYPI_TOKEN)
make upload-test           # Upload to TestPyPI (requires TEST_PYPI_TOKEN)
```

### Documentation

```bash
make docs                  # Build HTML documentation (Sphinx)
cd docs && make html       # Direct sphinx build
```

### Cleanup

```bash
make clean                 # Remove build artifacts
make clean-docs            # Clean documentation build
```

## Critical Architectural Constraints

### State Management Rule (CRITICAL)

**Routines MUST NOT modify instance variables during execution.**

```python
# ✅ CORRECT: Store execution state in JobState
flow = self.get_execution_context().flow
job_state = self.get_execution_context().job_state
job_state.update_routine_state(routine_id, {"status": "completed"})

# ❌ WRONG: Modify instance variables
self.counter += 1  # Breaks concurrent execution!
```

**Why?** The same routine instance can be used by multiple concurrent executions. Instance variables would cause data corruption between executions. All execution state must be stored in JobState.

### Non-Blocking emit()

```python
# emit() is now non-blocking (v0.9.0+)
self.emit("output", data="value")  # Returns immediately

# Flow is automatically detected from routine context
# No need to pass flow parameter in most cases
```

### Flow/JobState Decoupling

```python
# Each execute() returns an independent JobState
job_state = flow.execute(entry_routine_id, entry_params={...})

# Flow does NOT store execution state
# flow.job_state does NOT exist (removed in v0.9.0)

# Pause/resume/cancel require JobState as first argument
flow.pause(job_state)
flow.resume(job_state)
flow.cancel(job_state)
```

### Serialization Requirements

All data must be serializable for persistence/resume:
- Use JSON-compatible types (str, int, float, bool, list, dict, None)
- Avoid callables, file handles, or complex objects
- Use serilux for complex object serialization if needed

## Key Patterns

### Error Handling Strategies

```python
from routilux import ErrorHandler, ErrorStrategy

# STOP: Immediate halt (default)
handler = ErrorHandler(ErrorStrategy.STOP)

# CONTINUE: Log and continue
handler = ErrorHandler(ErrorStrategy.CONTINUE)

# RETRY: Retry with exponential backoff
handler = ErrorHandler(
    ErrorStrategy.RETRY,
    max_retries=3,
    retry_delay=1.0,
    backoff_multiplier=2.0
)

# SKIP: Skip failed routine
handler = ErrorHandler(ErrorStrategy.SKIP)

# Priority: Routine-level > Flow-level > Default (STOP)
routine.set_error_handler(handler)  # Highest priority
flow.set_error_handler(handler)    # Medium priority
```

### Slot Data Merging

```python
# Override: New data replaces old (default)
slot = routine.define_slot("input", handler=process, merge_strategy="override")

# Append: Accumulate values in lists
slot = routine.define_slot("input", handler=aggregate, merge_strategy="append")

# Custom: User-defined merge function
def custom_merge(old, new):
    return {**old, **new, "timestamp": time.time()}

slot = routine.define_slot("input", handler=process, merge_strategy=custom_merge)
```

### DSL Usage

```python
from routilux.dsl import load_flow_from_spec
import yaml

# Load from YAML file
with open("flow.yaml") as f:
    spec = yaml.safe_load(f)
flow = load_flow_from_spec(spec)

# YAML format:
# flow_id: example_flow
# routines:
#   processor:
#     class: mymodule.MyProcessor
#     config:
#       transform_func: "lambda x: x * 2"
# connections:
#   - from: processor.output
#     to: validator.input
```

### Execution Strategies

```python
# Sequential mode (default): max_workers=1
flow = Flow()

# Concurrent mode: max_workers>1
flow.set_execution_strategy("concurrent", max_workers=4)

# Both use the SAME unified event queue
# Only worker count differs
# Tasks processed fairly in queue order
```

## API Server (Monitoring & Debugging)

FastAPI-based REST API + WebSocket server in `/home/percy/works/mygithub/routilux/routilux/api/`:

**REST Endpoints**:
- `/api/flows` - Flow CRUD operations
- `/api/jobs` - Job execution and monitoring
- `/api/jobs/{job_id}/breakpoints` - Breakpoint management
- `/api/jobs/{job_id}/debug` - Debug controls (step over/into, variables)
- `/api/jobs/{job_id}/metrics` - Execution metrics

**WebSockets**:
- `/api/ws/jobs/{job_id}/monitor` - Real-time monitoring
- `/api/ws/jobs/{job_id}/debug` - Debug events

## Common Pitfalls

1. **Modifying instance variables in routines**: Always use JobState for execution state
2. **Assuming emit() blocks**: emit() is non-blocking, returns immediately
3. **Accessing flow.job_state**: This field was removed in v0.9.0
4. **Sharing state between executions**: Each execute() is independent, use aggregation patterns
5. **Non-serializable data**: All data must be JSON-serializable for persistence
6. **Retry strategy with broad exceptions**: RETRY only works for specific exception types
7. **Slot merge in concurrent mode**: Slot merging is not atomic in concurrent mode

## Dependencies

### Core Dependencies
- **serilux** (>=0.3.1): Serialization framework for Routilux objects
- **pyyaml** (>=6.0): YAML DSL support

### Optional Dependencies
- **api** extra: FastAPI, uvicorn, websockets, pydantic, httpx
- **dev** extra: pytest, pytest-cov, ruff, mypy, sphinx

## Related Projects

- **Varlord**: Configuration management library
- **Serilux**: Serialization framework
- **Lexilux**: Unified LLM API client library

All part of the Agentsmith open-source ecosystem.

## File Locations

- Main package: `/home/percy/works/mygithub/routilux/routilux/`
- Core tests: `/home/percy/works/mygithub/routilux/tests/`
- Examples: `/home/percy/works/mygithub/routilux/examples/`
- API server: `/home/percy/works/mygithub/routilux/routilux/api/`
- Documentation: `/home/percy/works/mygithub/routilux/docs/`
