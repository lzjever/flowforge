# Routilux Workflow CLI Design

**Date:** 2026-02-09
**Author:** Design exploration via brainstorming
**Status:** Approved for implementation

## Overview

A comprehensive workflow CLI application for the routilux library that supports:
- Standalone CLI mode for local workflow execution
- HTTP server mode for routilux-overseer integration
- Automatic discovery and registration of user-defined routines
- DSL loading and validation (JSON/YAML)

## Architecture

### Core Components

```
routilux/
├── cli/
│   ├── __init__.py
│   ├── main.py           # CLI entry point using click
│   ├── discovery.py      # Routine auto-discovery system
│   ├── decorators.py     # @register_routine decorator
│   ├── server_wrapper.py # Server integration wrapper
│   └── commands/
│       ├── __init__.py
│       ├── run.py        # routilux run
│       ├── server.py     # routilux server
│       ├── list.py       # routilux list
│       ├── validate.py   # routilux validate
│       └── init.py       # routilux init
```

### Design Principles

1. **Dual Mode** - Can run as standalone CLI or HTTP server mode
2. **Auto-Discovery** - Finds and registers routines from specified directories automatically
3. **Factory Integration** - All discovered routines are registered with `ObjectFactory` for DSL loading
4. **Minimal Dependencies** - Uses only `click` for CLI, existing FastAPI server for HTTP

## Routine Discovery System

### Discovery Process

1. **Scan Directories** - Recursively scans configured directories for `.py` files
2. **Import Modules** - Safely imports each module using `importlib`
3. **Register Routines** - Finds routines through two mechanisms:
   - **Decorator-based**: Functions/classes decorated with `@register_routine("name")`
   - **Class-based**: Classes that inherit from `Routine` base class
4. **Factory Integration** - All discovered routines are auto-registered with `ObjectFactory`

### @register_routine Decorator

```python
@register_routine("my_processor", category="processing", tags=["fast"])
def my_processor_logic(data):
    return process(data)
```

This decorator:
- Creates a dynamic `Routine` subclass
- Wraps the function as the routine's logic
- Registers it with `ObjectFactory` using the provided name
- Supports optional metadata (category, tags, description)

### Class-based Registration

```python
class CustomProcessor(Routine):
    factory_name = "custom_processor"  # Optional
```

Classes are auto-registered using their class name (or factory_name if specified).

### Error Handling

- Invalid modules are skipped with warnings
- Duplicate registrations raise clear errors
- Import errors are logged but don't stop discovery

### Default Directories

- `./routines/` (project local)
- `~/.routilux/routines/` (user global)
- CLI flags `--routines-dir` can override/add more

## CLI Command Structure

### Main Entry Point

```
routilux [OPTIONS] COMMAND [ARGS]...
```

### Core Commands

#### 1. routilux run - Execute a workflow

```
routilux run --workflow flow.yaml [--routines-dir DIR...] [--param KEY=VALUE...]
```

- Loads DSL file (JSON/YAML)
- Discovers routines from directories
- Executes flow and waits for completion
- Outputs results to stdout or file

#### 2. routilux server - Start HTTP server

```
routilux server start [--host HOST] [--port PORT] [--routines-dir DIR...]
```

- Starts FastAPI server with WebSocket support
- Registers routines from specified directories
- Provides REST + WebSocket endpoints

#### 3. routilux list - List available resources

```
routilux list routines [--category CAT] [--routines-dir DIR...]
routilux list flows [--dir DIR]
```

- Lists discovered routines by factory name
- Lists available DSL files

#### 4. routilux validate - Validate workflows

```
routilux validate --workflow flow.yaml [--routines-dir DIR...]
```

- Checks DSL syntax
- Verifies all routines are registered
- Validates connections

#### 5. routilux init - Initialize project structure

```
routilux init [--name PROJECT]
```

- Creates `routines/` directory
- Adds example routine
- Creates example workflow DSL

### Global Options

- `--routines-dir` - Additional directories to scan (can be specified multiple times)
- `--config` - Path to config file (optional, for advanced settings)
- `--verbose` / `-v` - Enable verbose output
- `--quiet` / `-q` - Minimal output

## HTTP Server Integration

### Server Startup

```
routilux server start [--host 0.0.0.0] [--port 8080] [--routines-dir DIR...]
```

### Existing Endpoints (Already Available)

- `POST /api/v1/execute` - One-shot flow execution
- `GET /api/v1/flows` - List flows
- `POST /api/v1/flows` - Create flow from DSL
- `GET /api/v1/factory/objects` - List registered routines
- `WS /api/v1/ws/jobs/{job_id}/monitor` - Real-time job monitoring
- `WS /api/v1/websocket` - Generic WebSocket for multi-job monitoring

### New CLI-Specific Endpoints (to add)

- `GET /api/v1/discovery` - Return discovery status (directories scanned, routines found)
- `POST /api/v1/dsl/file` - Load DSL from file path (vs body)

### Integration Flow

1. CLI discovers routines from directories
2. Registers all routines with `ObjectFactory`
3. Sets environment variable `ROUTILUX_ROUTINES_DIRS`
4. Starts uvicorn with `routilux.server.main:app`

## Package Structure and Installation

### Directory Structure

```
routilux/
├── cli/
│   ├── __init__.py
│   ├── main.py           # CLI entry point using click
│   ├── discovery.py      # Routine auto-discovery system
│   ├── decorators.py     # @register_routine decorator
│   ├── server_wrapper.py # Server integration wrapper
│   └── commands/
│       ├── __init__.py
│       ├── run.py        # routilux run
│       ├── server.py     # routilux server
│       ├── list.py       # routilux list
│       ├── validate.py   # routilux validate
│       └── init.py       # routilux init
```

### pyproject.toml Configuration

```toml
[project.optional-dependencies]
cli = [
    "click>=8.0",
]

[project.scripts]
routilux = "routilux.cli.main:cli"
```

### Installation

```bash
# Install with CLI support
pip install routilux[cli]

# Or install from source
pip install -e ".[cli]"
```

## Error Handling and Logging

### Error Handling Strategy

1. **User-Facing Errors** - Clear, actionable messages
   - Invalid DSL: "Line 5: Unknown routine 'unknown_processor'. Available: [list]"
   - Missing routines: "Routine 'my_processor' not found. Did you mean 'my_processor_v2'?"
   - Connection errors: "Cannot connect to source.output -> target.input (slot not found)"

2. **Discovery Errors** - Graceful degradation
   - Invalid module: Skip with warning "Skipping my_module.py: ImportError"
   - Duplicate registration: Error with clear message "Routine 'process' already registered"
   - Syntax errors: Show file path and line number

3. **Server Errors** - HTTP status codes
   - 400: Bad request (invalid DSL, validation errors)
   - 404: Not found (flow/routine doesn't exist)
   - 409: Conflict (duplicate flow_id)
   - 500: Internal error (unexpected exceptions)

### Logging

- **CLI mode**: Console output with levels (INFO, WARNING, ERROR)
- **Server mode**: Structured logging via existing audit system
- **Verbose mode** (`-v`): Detailed debug information
- **Quiet mode** (`-q`): Minimal output (only errors)

## Testing Strategy

### Testing Levels

1. **Unit Tests** - Individual components
   - `test_discovery.py` - Routine discovery system
   - `test_decorators.py` - @register_routine decorator
   - `test_factory_integration.py` - ObjectFactory registration

2. **Integration Tests** - Component interaction
   - `test_cli_integration.py` - End-to-end CLI commands
   - `test_server_integration.py` - CLI + server interaction
   - `test_dsl_loading.py` - DSL loading with discovered routines

3. **E2E Tests** - Full workflow
   - `test_e2e_workflow.py` - Complete workflow execution
   - Test with routilux-overseer when available

### Test Fixtures

- Sample routines in `tests/fixtures/routines/`
- Sample DSL files in `tests/fixtures/dsl/`
- Mock factory for isolated testing

### Coverage Goals

- Core discovery logic: 90%+
- CLI commands: 80%+
- Error paths: 100%

## Configuration and Extensibility

### Configuration Sources (in order of precedence)

1. **CLI Arguments** - Highest priority
   - `--routines-dir DIR` - Additional directories to scan
   - `--config FILE` - Path to config file
   - `--host HOST` / `--port PORT` - Server settings

2. **Config File** (optional)
   - `routilux.toml` or `.routilux.toml` in project root
   - `~/.routilux/config.toml` for global settings

3. **Environment Variables**
   - `ROUTILUX_ROUTINES_DIRS` - Colon-separated directories
   - `ROUTILUX_API_KEY` - API key for server authentication
   - `ROUTILUX_LOG_LEVEL` - Logging level

### Example Config File

```toml
# routilux.toml
[routines]
directories = ["./custom_routines", "./lib/routines"]

[server]
host = "0.0.0.0"
port = 8080

[discovery]
auto_reload = true
ignore_patterns = ["*_test.py", "test_*.py"]
```

### Extensibility Points

1. **Custom Routine Loaders** - Plugin system for loading routines from non-Python sources
2. **Custom DSL Parsers** - Support for additional DSL formats
3. **Custom Validators** - Plugin validation rules for workflows

## Implementation Roadmap

### Phase 1: Core CLI Infrastructure
- Set up `routilux/cli/` package structure
- Implement `main.py` with click framework
- Implement basic command routing

### Phase 2: Discovery System
- Implement `discovery.py` with directory scanning
- Implement `decorators.py` with @register_routine
- Add factory integration

### Phase 3: Core Commands
- Implement `routilux run` command
- Implement `routilux list` command
- Implement `routilux validate` command
- Implement `routilux init` command

### Phase 4: Server Integration
- Implement `routilux server start` command
- Implement server wrapper
- Add CLI-specific endpoints

### Phase 5: Testing and Documentation
- Write unit tests for discovery
- Write integration tests for CLI
- Write E2E tests
- Document CLI usage

## Key Design Decisions

1. **Click Framework** - Chosen for its widespread use, excellent documentation, and Python-first design
2. **Decorator + Class Registration** - Supports both simple and complex use cases
3. **Default Directories + CLI Override** - Balances ease of use with flexibility
4. **Reuse Existing Server** - Minimal changes to existing FastAPI server, wraps with CLI
5. **Factory-Only DSL** - All routines must be registered in factory for security and portability
