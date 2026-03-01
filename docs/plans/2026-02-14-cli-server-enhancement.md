# CLI Server Enhancement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enhance CLI server to auto-register built-in routines, load flows from directory at startup with hot reload, and add job management CLI commands.

**Architecture:** Extend server_wrapper.py to register built-in routines and load flows at startup. Add watchdog-based hot reload for flow files. Create new job command group for CLI job submission (local and remote modes).

**Tech Stack:** Click (CLI), FastAPI (server), watchdog (hot reload), PyYAML (DSL parsing)

---

## Task 1: Add `register_all_builtins()` Function

**Files:**
- Modify: `routilux/builtin_routines/__init__.py`
- Test: `tests/builtin_routines/test_registration.py`

**Step 1: Write the failing test**

```python
# tests/builtin_routines/test_registration.py
"""Tests for built-in routine registration."""

import pytest


def test_register_all_builtins_registers_all_routines():
    """Test that register_all_builtins registers all built-in routines."""
    from routilux.tools.factory.factory import ObjectFactory
    from routilux.builtin_routines import register_all_builtins

    factory = ObjectFactory()
    register_all_builtins(factory)

    # Check that all expected routines are registered
    expected = [
        "Mapper", "Filter", "SchemaValidator",
        "ConditionalRouter", "Aggregator", "Splitter", "Batcher", "Debouncer",
        "ResultExtractor", "RetryHandler",
    ]

    available = [r["name"] for r in factory.list_available()]
    for name in expected:
        assert name in available, f"Expected {name} to be registered"


def test_register_all_builtins_can_create_instances():
    """Test that registered routines can be instantiated."""
    from routilux.tools.factory.factory import ObjectFactory
    from routilux.builtin_routines import register_all_builtins

    factory = ObjectFactory()
    register_all_builtins(factory)

    # Should be able to create a Mapper instance
    mapper = factory.create("Mapper")
    assert mapper is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/builtin_routines/test_registration.py -v`
Expected: FAIL with "cannot import name 'register_all_builtins'"

**Step 3: Write minimal implementation**

```python
# Add to routilux/builtin_routines/__init__.py (at the end)

def register_all_builtins(factory) -> None:
    """Register all built-in routines with the given factory.

    Args:
        factory: ObjectFactory instance to register routines with
    """
    # Data processing
    factory.register("Mapper", Mapper)
    factory.register("Filter", Filter)
    factory.register("SchemaValidator", SchemaValidator)
    factory.register("DataTransformer", DataTransformer)
    factory.register("DataValidator", DataValidator)

    # Control flow
    factory.register("ConditionalRouter", ConditionalRouter)
    factory.register("Aggregator", Aggregator)
    factory.register("Splitter", Splitter)
    factory.register("Batcher", Batcher)
    factory.register("Debouncer", Debouncer)

    # Text processing
    factory.register("ResultExtractor", ResultExtractor)

    # Reliability
    factory.register("RetryHandler", RetryHandler)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/builtin_routines/test_registration.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add routilux/builtin_routines/__init__.py tests/builtin_routines/test_registration.py
git commit -m "feat: add register_all_builtins() for automatic routine registration"
```

---

## Task 2: Add Flow Loading Function with Conflict Detection

**Files:**
- Modify: `routilux/cli/server_wrapper.py`
- Test: `tests/cli/test_flow_loader.py`

**Step 1: Write the failing test**

```python
# tests/cli/test_flow_loader.py
"""Tests for flow loading functionality."""

import tempfile
from pathlib import Path

import pytest
import yaml


def test_load_flows_from_directory():
    """Test loading flows from a directory."""
    from routilux.cli.server_wrapper import load_flows_from_directory
    from routilux.tools.factory.factory import ObjectFactory
    from routilux.builtin_routines import register_all_builtins

    factory = ObjectFactory()
    register_all_builtins(factory)

    with tempfile.TemporaryDirectory() as tmpdir:
        flows_dir = Path(tmpdir)

        # Create a simple flow
        flow_data = {
            "flow_id": "test_flow",
            "routines": {
                "mapper": {"class": "Mapper"}
            },
            "connections": []
        }
        (flows_dir / "test.yaml").write_text(yaml.dump(flow_data))

        flows = load_flows_from_directory(flows_dir, factory)

        assert "test_flow" in flows
        assert flows["test_flow"].flow_id == "test_flow"


def test_load_flows_detects_duplicate_flow_id():
    """Test that duplicate flow_ids cause an error."""
    from routilux.cli.server_wrapper import load_flows_from_directory
    from routilux.tools.factory.factory import ObjectFactory
    from routilux.builtin_routines import register_all_builtins

    factory = ObjectFactory()
    register_all_builtins(factory)

    with tempfile.TemporaryDirectory() as tmpdir:
        flows_dir = Path(tmpdir)

        # Create two flows with same flow_id
        flow_data = {
            "flow_id": "duplicate_flow",
            "routines": {"m1": {"class": "Mapper"}},
            "connections": []
        }
        (flows_dir / "flow1.yaml").write_text(yaml.dump(flow_data))
        (flows_dir / "flow2.yaml").write_text(yaml.dump(flow_data))

        with pytest.raises(ValueError, match="Duplicate flow_id"):
            load_flows_from_directory(flows_dir, factory)


def test_load_flows_empty_directory():
    """Test loading from empty directory returns empty dict."""
    from routilux.cli.server_wrapper import load_flows_from_directory
    from routilux.tools.factory.factory import ObjectFactory

    factory = ObjectFactory()

    with tempfile.TemporaryDirectory() as tmpdir:
        flows = load_flows_from_directory(Path(tmpdir), factory)
        assert flows == {}
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/cli/test_flow_loader.py -v`
Expected: FAIL with "cannot import name 'load_flows_from_directory'"

**Step 3: Write minimal implementation**

```python
# Add to routilux/cli/server_wrapper.py (before start_server function)

import yaml
from typing import Dict

from routilux.core.flow import Flow


def load_flows_from_directory(flows_dir: Path, factory) -> Dict[str, Flow]:
    """Load all flows from a directory.

    Args:
        flows_dir: Directory containing flow DSL files (.yaml, .json)
        factory: ObjectFactory for loading flows

    Returns:
        Dictionary mapping flow_id to Flow instance

    Raises:
        ValueError: If duplicate flow_id is detected
    """
    flows: Dict[str, Flow] = {}
    flows_path = Path(flows_dir)

    if not flows_path.exists():
        return flows

    for dsl_file in flows_path.glob("*.yaml"):
        try:
            dsl_content = dsl_file.read_text()
            dsl_dict = yaml.safe_load(dsl_content)

            flow = factory.load_flow_from_dsl(dsl_dict)

            if flow.flow_id in flows:
                raise ValueError(
                    f"Duplicate flow_id '{flow.flow_id}' in {dsl_file} "
                    f"(already defined in another file)"
                )

            flows[flow.flow_id] = flow
            print(f"Loaded flow: {flow.flow_id} from {dsl_file.name}")

        except yaml.YAMLError as e:
            print(f"Warning: Failed to parse {dsl_file}: {e}")
        except Exception as e:
            print(f"Warning: Failed to load flow from {dsl_file}: {e}")

    # Also check .json files
    for dsl_file in flows_path.glob("*.json"):
        try:
            dsl_content = dsl_file.read_text()
            import json
            dsl_dict = json.loads(dsl_content)

            flow = factory.load_flow_from_dsl(dsl_dict)

            if flow.flow_id in flows:
                raise ValueError(
                    f"Duplicate flow_id '{flow.flow_id}' in {dsl_file} "
                    f"(already defined in another file)"
                )

            flows[flow.flow_id] = flow
            print(f"Loaded flow: {flow.flow_id} from {dsl_file.name}")

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse {dsl_file}: {e}")
        except Exception as e:
            print(f"Warning: Failed to load flow from {dsl_file}: {e}")

    return flows
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/cli/test_flow_loader.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add routilux/cli/server_wrapper.py tests/cli/test_flow_loader.py
git commit -m "feat: add load_flows_from_directory with conflict detection"
```

---

## Task 3: Add --flows-dir Option to Server Command

**Files:**
- Modify: `routilux/cli/commands/server.py`
- Modify: `routilux/cli/server_wrapper.py`
- Test: `tests/cli/commands/test_server_flows.py`

**Step 1: Write the failing test**

```python
# tests/cli/commands/test_server_flows.py
"""Tests for server --flows-dir option."""

import tempfile
from pathlib import Path

import yaml
from click.testing import CliRunner


def test_server_start_with_flows_dir():
    """Test that --flows-dir option is accepted."""
    from routilux.cli.main import cli

    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        flows_dir = Path(tmpdir)

        # Create a simple flow
        flow_data = {
            "flow_id": "test_flow",
            "routines": {"m": {"class": "Mapper"}},
            "connections": []
        }
        (flows_dir / "test.yaml").write_text(yaml.dump(flow_data))

        # Just check help shows the option
        result = runner.invoke(cli, ["server", "start", "--help"])

        assert result.exit_code == 0
        assert "--flows-dir" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/cli/commands/test_server_flows.py -v`
Expected: FAIL with "--flows-dir" not in output

**Step 3: Write minimal implementation**

```python
# Modify routilux/cli/commands/server.py

# Add this option to the start command (after --routines-dir option):
@click.option(
    "--flows-dir",
    type=click.Path(exists=True, path_type=Path),
    help="Directory containing flow DSL files to load at startup",
)

# Update the start function signature:
def start(ctx, host, port, routines_dir, flows_dir, reload, log_level):

# Add flows_dir to the start_server call:
start_server(
    host=host,
    port=port,
    routines_dirs=routines_dirs if routines_dirs else None,
    flows_dir=flows_dir,  # Add this
    reload=reload,
    log_level=log_level,
)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/cli/commands/test_server_flows.py::test_server_start_with_flows_dir -v`
Expected: PASS

**Step 5: Commit**

```bash
git add routilux/cli/commands/server.py tests/cli/commands/test_server_flows.py
git commit -m "feat: add --flows-dir option to server start command"
```

---

## Task 4: Integrate Flow Loading into Server Startup

**Files:**
- Modify: `routilux/cli/server_wrapper.py`

**Step 1: Update start_server function**

```python
# Modify routilux/cli/server_wrapper.py start_server function

def start_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    routines_dirs: Optional[List[Path]] = None,
    flows_dir: Optional[Path] = None,  # Add this parameter
    reload: bool = False,
    log_level: str = "info",
):
    """Start the routilux HTTP server."""
    # Register built-in routines first
    from routilux.builtin_routines import register_all_builtins
    factory = discover_routines([], on_error="warn")  # Get factory
    register_all_builtins(factory)
    print("Registered built-in routines")

    # Gather routines directories
    all_dirs = list(routines_dirs or [])
    all_dirs.extend(get_default_routines_dirs())

    # Discover custom routines
    if all_dirs:
        print(f"Discovering routines from: {all_dirs}")
        factory = discover_routines(all_dirs, on_error="warn")
        routines = factory.list_available()
        print(f"Registered {len(routines)} routines")

    # Load flows from directory
    if flows_dir:
        print(f"Loading flows from: {flows_dir}")
        flows = load_flows_from_directory(flows_dir, factory)
        print(f"Loaded {len(flows)} flows")

        # Register flows with monitoring storage
        from routilux.monitoring.storage import flow_store
        for flow_id, flow in flows.items():
            flow_store.add(flow)

    # ... rest of function unchanged
```

**Step 2: Run tests to verify**

Run: `pytest tests/cli/test_flow_loader.py tests/cli/commands/test_server_flows.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add routilux/cli/server_wrapper.py
git commit -m "feat: integrate built-in routines and flow loading into server startup"
```

---

## Task 5: Add Hot Reload for Flows

**Files:**
- Modify: `routilux/cli/server_wrapper.py`
- Modify: `pyproject.toml` (add watchdog dependency)

**Step 1: Add watchdog to dependencies**

```toml
# In pyproject.toml, add to server dependencies:
server = [
    "uvicorn>=0.20.0",
    "fastapi>=0.100.0",
    "websockets>=10.0",
    "slowapi>=0.1.9",
    "watchdog>=3.0.0",  # Add this
]
```

**Step 2: Add hot reload implementation**

```python
# Add to routilux/cli/server_wrapper.py

import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent


class FlowReloadHandler(FileSystemEventHandler):
    """Handler for flow file changes."""

    def __init__(self, flows_dir: Path, factory, flow_store):
        self.flows_dir = flows_dir
        self.factory = factory
        self.flow_store = flow_store

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(('.yaml', '.json')):
            print(f"Flow file modified: {event.src_path}, reloading...")
            self._reload_flow(Path(event.src_path))

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith(('.yaml', '.json')):
            print(f"Flow file created: {event.src_path}, loading...")
            self._reload_flow(Path(event.src_path))

    def _reload_flow(self, flow_file: Path):
        try:
            dsl_content = flow_file.read_text()
            if flow_file.suffix == '.yaml':
                dsl_dict = yaml.safe_load(dsl_content)
            else:
                import json
                dsl_dict = json.loads(dsl_content)

            flow = self.factory.load_flow_from_dsl(dsl_dict)

            # Update or add the flow
            self.flow_store.add(flow)
            print(f"Reloaded flow: {flow.flow_id}")

        except Exception as e:
            print(f"Error reloading flow from {flow_file}: {e}")


def start_flow_watcher(flows_dir: Path, factory, flow_store) -> Observer:
    """Start watching flow directory for changes."""
    observer = Observer()
    handler = FlowReloadHandler(flows_dir, factory, flow_store)
    observer.schedule(handler, str(flows_dir), recursive=False)
    observer.start()
    print(f"Watching for flow changes in: {flows_dir}")
    return observer
```

**Step 3: Update start_server to use watcher**

```python
# Add at the end of start_server, before uvicorn.run:

    # Start flow watcher if flows_dir is specified
    observer = None
    if flows_dir:
        from routilux.monitoring.storage import flow_store
        observer = start_flow_watcher(flows_dir, factory, flow_store)

    try:
        uvicorn.run(...)
    finally:
        if observer:
            observer.stop()
            observer.join()
```

**Step 4: Commit**

```bash
git add routilux/cli/server_wrapper.py pyproject.toml
git commit -m "feat: add hot reload for flow files using watchdog"
```

---

## Task 6: Create Job CLI Command Group

**Files:**
- Create: `routilux/cli/commands/job.py`
- Modify: `routilux/cli/main.py`
- Test: `tests/cli/commands/test_job.py`

**Step 1: Write the failing test**

```python
# tests/cli/commands/test_job.py
"""Tests for job CLI commands."""

from click.testing import CliRunner


def test_job_command_group_exists():
    """Test that job command group exists."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["job", "--help"])

    assert result.exit_code == 0
    assert "submit" in result.output


def test_job_submit_help():
    """Test job submit help."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["job", "submit", "--help"])

    assert result.exit_code == 0
    assert "--flow" in result.output
    assert "--routine" in result.output
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/cli/commands/test_job.py -v`
Expected: FAIL with "No such command: job"

**Step 3: Write the job command implementation**

```python
# routilux/cli/commands/job.py
"""Job management CLI commands."""

import json

import click


@click.group()
def job():
    """Manage workflow jobs.

    \b
    Examples:
        # Submit a job locally
        $ routilux job submit --flow myflow --routine processor --data '{"x": 1}'

        # Submit to remote server
        $ routilux job submit --server http://localhost:8080 --flow myflow ...

        # Check job status
        $ routilux job status <job_id>

        # List jobs
        $ routilux job list --flow myflow
    """
    pass


@job.command("submit")
@click.option("--flow", "-f", required=True, help="Flow ID or name")
@click.option("--routine", "-r", required=True, help="Entry routine ID")
@click.option("--slot", "-s", default="input", help="Input slot name (default: input)")
@click.option("--data", "-d", required=True, help="Input data as JSON string")
@click.option("--server", help="Server URL for remote mode (e.g., http://localhost:8080)")
@click.option("--wait", is_flag=True, help="Wait for job completion")
@click.option("--timeout", default=60.0, type=float, help="Timeout in seconds")
@click.pass_context
def submit(ctx, flow, routine, slot, data, server, wait, timeout):
    """Submit a job to a flow.

    \b
    Examples:
        # Local mode (default)
        $ routilux job submit --flow myflow --routine proc --data '{"x": 1}'

        # Remote mode
        $ routilux job submit --server http://localhost:8080 --flow myflow --routine proc --data '{}'
    """
    quiet = ctx.obj.get("quiet", False)

    try:
        input_data = json.loads(data)
    except json.JSONDecodeError as e:
        raise click.BadParameter(f"Invalid JSON data: {e}", param_hint="--data")

    if server:
        # Remote mode - use HTTP API
        result = _submit_remote(server, flow, routine, slot, input_data, wait, timeout)
    else:
        # Local mode - use Runtime directly
        result = _submit_local(flow, routine, slot, input_data, wait, timeout)

    if not quiet:
        click.echo(json.dumps(result, indent=2))


def _submit_local(flow_id: str, routine_id: str, slot_name: str, data: dict, wait: bool, timeout: float) -> dict:
    """Submit job locally using Runtime."""
    from routilux.core.runtime import Runtime
    from routilux.monitoring.registry import FlowRegistry

    # Get the flow
    flow_registry = FlowRegistry.get_instance()
    flow = flow_registry.get(flow_id)

    if flow is None:
        raise click.ClickException(f"Flow '{flow_id}' not found. Make sure it's loaded.")

    runtime = Runtime()

    worker_state, job_context = runtime.post(
        flow_name=flow_id,
        routine_name=routine_id,
        slot_name=slot_name,
        data=data,
        timeout=timeout,
    )

    result = {
        "job_id": job_context.job_id,
        "worker_id": worker_state.worker_id,
        "flow_id": flow_id,
        "status": job_context.status,
    }

    if wait:
        # Wait for completion
        import time
        start = time.time()
        while time.time() - start < timeout:
            if job_context.status in ("completed", "failed"):
                break
            time.sleep(0.1)

        result["status"] = job_context.status
        result["error"] = job_context.error

    return result


def _submit_remote(server_url: str, flow_id: str, routine_id: str, slot_name: str, data: dict, wait: bool, timeout: float) -> dict:
    """Submit job to remote server via HTTP API."""
    import urllib.request
    import urllib.error

    url = f"{server_url.rstrip('/')}/api/v1/jobs"

    payload = {
        "flow_id": flow_id,
        "routine_id": routine_id,
        "slot_name": slot_name,
        "data": data,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        raise click.ClickException(f"Server error {e.code}: {error_body}")


@job.command("status")
@click.argument("job_id")
@click.option("--server", help="Server URL for remote mode")
@click.pass_context
def status(ctx, job_id, server):
    """Check job status."""
    quiet = ctx.obj.get("quiet", False)

    if server:
        result = _get_job_status_remote(server, job_id)
    else:
        result = _get_job_status_local(job_id)

    if not quiet:
        click.echo(json.dumps(result, indent=2))


def _get_job_status_local(job_id: str) -> dict:
    """Get job status locally."""
    from routilux.monitoring.runtime_registry import RuntimeRegistry

    runtime_registry = RuntimeRegistry.get_instance()
    job = runtime_registry.get_job(job_id)

    if job is None:
        raise click.ClickException(f"Job '{job_id}' not found")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "error": job.error,
    }


def _get_job_status_remote(server_url: str, job_id: str) -> dict:
    """Get job status from remote server."""
    import urllib.request
    import urllib.error

    url = f"{server_url.rstrip('/')}/api/v1/jobs/{job_id}"

    req = urllib.request.Request(url, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        raise click.ClickException(f"Job not found: {job_id}")


@job.command("list")
@click.option("--flow", "-f", help="Filter by flow ID")
@click.option("--server", help="Server URL for remote mode")
@click.pass_context
def list_jobs(ctx, flow, server):
    """List jobs."""
    quiet = ctx.obj.get("quiet", False)

    if server:
        result = _list_jobs_remote(server, flow)
    else:
        result = _list_jobs_local(flow)

    if not quiet:
        click.echo(json.dumps(result, indent=2))


def _list_jobs_local(flow_id: str = None) -> list:
    """List jobs locally."""
    from routilux.monitoring.runtime_registry import RuntimeRegistry

    runtime_registry = RuntimeRegistry.get_instance()
    jobs = runtime_registry.list_jobs()

    if flow_id:
        jobs = [j for j in jobs if j.get("flow_id") == flow_id]

    return jobs


def _list_jobs_remote(server_url: str, flow_id: str = None) -> list:
    """List jobs from remote server."""
    import urllib.request

    url = f"{server_url.rstrip('/')}/api/v1/jobs"
    if flow_id:
        url += f"?flow_id={flow_id}"

    req = urllib.request.Request(url, method="GET")

    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode())
        return data.get("jobs", [])
```

**Step 4: Register job command in main.py**

```python
# Add to routilux/cli/main.py

from routilux.cli.commands.job import job

# Add after other imports
cli.add_command(job)
```

**Step 5: Run tests to verify**

Run: `pytest tests/cli/commands/test_job.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add routilux/cli/commands/job.py routilux/cli/main.py tests/cli/commands/test_job.py
git commit -m "feat: add job CLI command group (submit/status/list)"
```

---

## Task 7: Integration Tests

**Files:**
- Test: `tests/cli/test_server_integration.py`

**Step 1: Write integration test**

```python
# tests/cli/test_server_integration.py
"""Integration tests for server flow loading."""

import tempfile
from pathlib import Path

import yaml
from click.testing import CliRunner


def test_server_loads_flows_and_registers_builtins():
    """Test that server loads flows and built-in routines work together."""
    from routilux.cli.server_wrapper import load_flows_from_directory
    from routilux.tools.factory.factory import ObjectFactory
    from routilux.builtin_routines import register_all_builtins

    factory = ObjectFactory()
    register_all_builtins(factory)

    with tempfile.TemporaryDirectory() as tmpdir:
        flows_dir = Path(tmpdir)

        # Create flow using built-in routine
        flow_data = {
            "flow_id": "builtin_test",
            "routines": {
                "mapper": {"class": "Mapper"}
            },
            "connections": []
        }
        (flows_dir / "test.yaml").write_text(yaml.dump(flow_data))

        flows = load_flows_from_directory(flows_dir, factory)

        assert "builtin_test" in flows
        # Verify the Mapper routine was used
        assert "mapper" in flows["builtin_test"].routines
```

**Step 2: Run tests**

Run: `pytest tests/cli/test_server_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/cli/test_server_integration.py
git commit -m "test: add integration tests for server flow loading"
```

---

## Task 8: Update Documentation

**Files:**
- Modify: `docs/source/installation.rst` (add job command docs)
- Modify: `README.md` (update server examples)

**Step 1: Update README with new server usage**

Add to README.md:

```markdown
### Server with Flow Loading

```bash
# Start server with flows directory
routilux server start --flows-dir ./flows --port 8080

# Built-in routines (Mapper, Filter, etc.) are automatically available
# Flows from ./flows/*.yaml are loaded at startup

# Hot reload enabled - flow files are watched for changes
```

### Job Management

```bash
# Submit job locally
routilux job submit --flow myflow --routine processor --data '{"input": "value"}'

# Submit job to remote server
routilux job submit --server http://localhost:8080 --flow myflow --routine processor --data '{}'

# Check job status
routilux job status <job_id>

# List jobs
routilux job list --flow myflow
```
```

**Step 2: Commit**

```bash
git add README.md docs/source/installation.rst
git commit -m "docs: update server and job command documentation"
```

---

## Task 9: Final Verification and Version Bump

**Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short --ignore=tests/benchmarks
```

Expected: All tests pass

**Step 2: Run lint**

```bash
python -m ruff format routilux/ tests/
python -m ruff check routilux/ tests/
```

**Step 3: Update version**

```bash
# Update routilux/__init__.py version to 0.15.0
```

**Step 4: Update CHANGELOG**

```markdown
## [0.15.0] - 2026-02-14

### Added

- **Server enhancements**:
  - `--flows-dir` option to load flows at startup
  - Automatic registration of built-in routines (Mapper, Filter, etc.)
  - Hot reload for flow files (watchdog-based)
  - Flow ID conflict detection with clear error messages

- **Job CLI commands**:
  - `routilux job submit` - Submit jobs (local and remote modes)
  - `routilux job status` - Check job status
  - `routilux job list` - List jobs
  - Support for `--server` flag to target remote servers
```

**Step 5: Final commit and tag**

```bash
git add -A
git commit -m "v0.15.0: CLI server enhancements and job commands"
git tag -a v0.15.0 -m "v0.15.0: CLI server enhancements and job commands"
git push origin main --tags
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Add register_all_builtins() | builtin_routines/__init__.py |
| 2 | Add flow loading with conflict detection | server_wrapper.py |
| 3 | Add --flows-dir option | cli/commands/server.py |
| 4 | Integrate into server startup | server_wrapper.py |
| 5 | Add hot reload | server_wrapper.py, pyproject.toml |
| 6 | Create job CLI commands | cli/commands/job.py, main.py |
| 7 | Integration tests | tests/cli/ |
| 8 | Update documentation | README.md |
| 9 | Final verification | All files |
