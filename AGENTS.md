# AGENTS.md - Code Style and Development Guidelines

This file provides guidelines for agentic coding assistants working on the Routilux codebase.

## Build, Lint, and Test Commands

### Primary Commands
- `make test` / `pytest tests/ -v` - Run all tests (excludes integration tests by default)
- `pytest tests/test_routine.py` - Run specific test file
- `pytest tests/test_routine.py::TestRoutineBasic::test_create_routine` - Run single test function
- `pytest tests/ -v -m integration` - Run integration tests only
- `pytest tests/ -v -m "not integration"` - Run unit tests only (excludes integration)
- `pytest tests/ -v -m api` - Run API endpoint tests
- `pytest tests/ -v -m slow` - Run slow tests
- `pytest tests/ -v -m "not slow"` - Skip slow tests
- `make test-cov` / `pytest tests/ --cov=routilux --cov-report=html --cov-report=term` - Run with coverage
- `make lint` / `ruff check routilux/ tests/ examples/ --output-format=concise` - Run linting
- `make format` / `ruff format routilux/ tests/ examples/` - Format code
- `make format-check` / `ruff format --check routilux/ tests/ examples/` - Check formatting
- `make type-check` / `mypy routilux/` - Run mypy type checking
- `make check` - Run all checks (lint + format-check + test)

### Dependency Management
- `make dev-install` - Install package with all dev dependencies (recommended for active dev)
- `make setup-venv` - Create venv and install dependencies only (for CI/CD, not package install)
- Uses `uv` if available, otherwise `pip`

### Pre-commit Hooks
- `make pre-commit-install` - Install pre-commit hooks
- `make pre-commit-run` - Run pre-commit manually
- Pre-commit runs: ruff-check, ruff-format, trailing-whitespace, end-of-file-fixer, check-yaml, check-toml

## Code Style Guidelines

### Imports
- **Always start with**: `from __future__ import annotations`
- Order: standard library, third-party, local
- Use `TYPE_CHECKING` for forward references:
  ```python
  from __future__ import annotations
  import threading
  from typing import TYPE_CHECKING, Any

  if TYPE_CHECKING:
      from routilux.flow import Flow
      from routilux.routine import Routine

  from serilux import Serializable, register_serializable
  ```

### Type Annotations
- Python 3.8+ syntax: `str | None` instead of `Optional[str]`
- Generic syntax: `list[str]`, `dict[str, Any]` instead of `List[str]`, `Dict[str, Any]`
- Type hints required for all function parameters and return values
- Use `TYPE_CHECKING` imports to avoid circular dependencies
- All classes must import from `typing.TYPE_CHECKING` when referencing other classes

### Formatting (Ruff)
- Line length: 100 characters
- Quote style: double quotes
- Indent style: spaces
- Configuration in `pyproject.toml`: `[tool.ruff]`

### Naming Conventions
- Classes: `PascalCase` (e.g., `Routine`, `Event`, `Flow`)
- Functions/methods: `snake_case` (e.g., `execute`, `add_routine`)
- Constants (module-level): `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`)
- Private members: `_leading_underscore` (e.g., `_config`, `_id`, `_events`)
- Protected members: `_leading_underscore` (same as private)

### Docstrings
- Use triple quotes `"""` for all docstrings
- Google style: concise description, detailed Args section, Examples when useful
- Module docstring: Describe the module's purpose
- Class docstring: Describe class purpose and key responsibilities
- Method docstring: Args, Returns, Raises (if applicable)

### Logging
- Use standard library `logging` module
- Module-level logger: `logger = logging.getLogger(__name__)`
- Place logger at module top after imports
- Use appropriate log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Error Handling
- Custom exceptions inherit from `Exception`
- Define custom exceptions at module top level
- Use `ErrorHandler` class with `ErrorStrategy` enum for workflow errors
- Error strategies: `STOP`, `CONTINUE`, `RETRY`, `SKIP`
- Include meaningful error messages
- Always handle exceptions at appropriate abstraction level

### Serialization
- Use `serilux` library for all serializable classes
- Decorate serializable classes with `@register_serializable`
- Inherit from `Serializable` base class
- Implement `add_serializable_fields()` in `__init__`
- Override `serialize()` and `deserialize()` for custom handling (e.g., datetime)
- Example:
  ```python
  @register_serializable
  class MySerializble(Serializable):
      def __init__(self):
          super().__init__()
          self.field1: str = ""
          self.field2: int = 0
          self.add_serializable_fields(["field1", "field2"])
  ```

### Threading and Concurrency
- Use `threading.Lock()` for thread-safe operations
- Use `contextvars.ContextVar` for thread-local context (e.g., `_current_job_state`)
- Routine execution state MUST NOT modify instance variables
- All execution-specific state must be stored in `JobState` (not in Routine)
- Routines can READ from `_config` dictionary, but WRITE to `JobState`

### Routine-Specific Constraints
- **CRITICAL**: Routines MUST NOT accept constructor parameters (except `self`)
- All configuration must be stored in `_config` dictionary via `set_config()`
- During execution, routines MUST NOT modify instance variables
- Use `job_state.update_routine_state()` for execution-specific state
- Use `JobState.shared_data` for sharing data between routines
- Use `JobState.shared_log` for logging
- Use `self.emit()` or `self.send_output()` for sending data

### Testing (pytest)
- Test files: `tests/test_*.py`
- Test classes: `Test*` (PascalCase)
- Test functions: `test_*` (snake_case)
- Use markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.api`, `@pytest.mark.slow`
- Default test run excludes integration tests (see `pytest.ini`)
- Use descriptive docstrings for test functions
- Follow AAA pattern: Arrange, Act, Assert

### Test Markers
- `unit` - Unit tests (no external dependencies)
- `integration` - Integration tests (require external services)
- `api` - API endpoint tests
- `slow` - Slow-running tests
- `persistence` - Persistence/serialization tests
- `resume` - Resume functionality tests
- `asyncio` - Async tests
- `websocket` - WebSocket tests
- `debug` - Debug-specific tests

## Project Structure
- `routilux/` - Main package code
- `routilux/flow/` - Flow management subpackage
- `routilux/api/` - API endpoints (FastAPI)
- `routilux/monitoring/` - Monitoring and debugging tools
- `routilux/analysis/` - Workflow analysis tools
- `routilux/dsl/` - DSL definition language
- `tests/` - Test suite
- `examples/` - Usage examples
- `docs/` - Sphinx documentation

## Key Dependencies
- `serilux>=0.3.1` - Serialization library
- `pyyaml>=6.0` - YAML parsing
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `ruff>=0.1.0` - Linter and formatter
- `mypy>=0.991` - Type checker

## Type Checking Configuration
- Python version: 3.8
- `warn_return_any = true`
- `warn_unused_configs = true`
- `disallow_untyped_defs = false` (will be enabled in future)
- `check_untyped_defs = true`
- `ignore_missing_imports = true`

## Important Notes
- Always format code before committing: `make format`
- Always run tests before committing: `make test`
- Always run type checking: `make type-check` (warns, doesn't block)
- Coverage target: 60% minimum
- Never suppress type errors with `# type: ignore` unless absolutely necessary
- Never use `any` or `object` as type hints
- Never leave code in broken state after making changes
