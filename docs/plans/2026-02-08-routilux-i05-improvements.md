# Routilux I05 Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix P0/P1/P2 issues from A04 code review - security hardening, architecture cleanup, and observability improvements.

**Architecture:**
- Since project is unreleased, we can make breaking changes without backward compatibility concerns
- Remove legacy architecture (Flow/JobState) entirely, keep only new core (Runtime/WorkerState)
- Apply security-first defaults for production readiness
- Add comprehensive audit logging and performance benchmarking

**Tech Stack:** Python 3.8+, FastAPI, pytest, serilux

**Principles:** KISS, DRY, SOLID, YAGNI, TDD, frequent commits

---

## Task 1: Security - Fix Default Configuration (P0-1)

**Problem:** `api_key_enabled=False` and `rate_limit_enabled=False` expose production deployments.

**Files:**
- Modify: `routilux/server/config.py:1-115`
- Test: `tests/server/test_config.py`

### Step 1: Write failing test for secure defaults

```python
# tests/server/test_config.py

import os
import pytest

def test_default_security_is_enabled():
    """Default configuration should have security enabled."""
    # Clear environment to test true defaults
    for key in list(os.environ.keys()):
        if key.startswith("ROUTILUX_"):
            del os.environ[key]

    from routilux.server.config import APIConfig

    config = APIConfig()
    assert config.api_key_enabled is True, "API key should be enabled by default"
    assert config.rate_limit_enabled is True, "Rate limiting should be enabled by default"


def test_dev_mode_disables_security():
    """Explicit dev mode should disable security with warning."""
    os.environ["ROUTILUX_ENV"] = "development"
    os.environ["ROUTILUX_DEV_DISABLE_SECURITY"] = "true"

    # Import fresh to pick up env vars
    import importlib
    from routilux.server import config
    importlib.reload(config)

    cfg = config.APIConfig()
    assert cfg.api_key_enabled is False
    assert cfg.rate_limit_enabled is False


def test_production_env_enforces_security():
    """Production environment should enforce security."""
    os.environ["ROUTILUX_ENV"] = "production"
    os.environ["ROUTILUX_DEV_DISABLE_SECURITY"] = "false"  # Explicit

    import importlib
    from routilux.server import config
    importlib.reload(config)

    cfg = config.APIConfig()
    assert cfg.api_key_enabled is True
    assert cfg.rate_limit_enabled is True
```

**Step 2: Run test to verify it fails**

```bash
cd /var/tmp/vibe-kanban/worktrees/4d68-routilux-i05-a04/routilux
pytest tests/server/test_config.py::test_default_security_is_enabled -v
```

Expected: FAIL (api_key_enabled defaults to False)

### Step 3: Implement secure defaults

```python
# routilux/server/config.py

import logging
import os
import threading
import warnings
from typing import List, Optional

logger = logging.getLogger(__name__)


class APIConfig:
    """API configuration with secure-by-default settings.

    Security Policy:
        - API key authentication: ENABLED by default
        - Rate limiting: ENABLED by default
        - Development mode: Must explicitly opt-out with ROUTILUX_DEV_DISABLE_SECURITY=true

    Environment Variables:
        ROUTILUX_ENV: Environment ("development" or "production", default: "development")
        ROUTILUX_DEV_DISABLE_SECURITY: Set to "true" to disable security (development only)
        ROUTILUX_API_KEY_ENABLED: Override default (true/false, default: true)
        ROUTILUX_RATE_LIMIT_ENABLED: Override default (true/false, default: true)
        ROUTILUX_API_KEY: Single API key
        ROUTILUX_API_KEYS: Comma-separated API keys
        ROUTILUX_RATE_LIMIT_PER_MINUTE: Rate limit (default: 60)
        ROUTILUX_CORS_ORIGINS: Comma-separated allowed origins
    """

    def __init__(self):
        """Load configuration with secure defaults."""
        # Detect environment
        self.environment: str = os.getenv("ROUTILUX_ENV", os.getenv("ENVIRONMENT", "development"))
        self.is_production: bool = self.environment == "production"

        # Check for explicit development disable
        dev_disable_security = os.getenv("ROUTILUX_DEV_DISABLE_SECURITY", "false").lower() == "true"

        # API Key: secure by default
        env_api_key_enabled = os.getenv("ROUTILUX_API_KEY_ENABLED", "true").lower() == "true"
        self.api_key_enabled: bool = env_api_key_enabled and not dev_disable_security

        if not self.api_key_enabled:
            logger.warning(
                "API key authentication is DISABLED. This is only appropriate for development. "
                "Set ROUTILUX_API_KEY_ENABLED=true for production."
            )

        self.api_keys: List[str] = self._load_api_keys()

        # Rate limiting: secure by default
        env_rate_limit_enabled = os.getenv("ROUTILUX_RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.rate_limit_enabled: bool = env_rate_limit_enabled and not dev_disable_security

        if not self.rate_limit_enabled:
            logger.warning(
                "Rate limiting is DISABLED. This is only appropriate for development. "
                "Set ROUTILUX_RATE_LIMIT_ENABLED=true for production."
            )

        # CORS
        self.cors_origins: str = os.getenv("ROUTILUX_CORS_ORIGINS", "")

        # Rate limit with validation
        try:
            self.rate_limit_per_minute: int = int(os.getenv("ROUTILUX_RATE_LIMIT_PER_MINUTE", "60"))
            if self.rate_limit_per_minute <= 0:
                raise ValueError("rate_limit_per_minute must be positive")
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid ROUTILUX_RATE_LIMIT_PER_MINUTE, using default: {e}")
            self.rate_limit_per_minute = 60

        # Warn if security is disabled in production-like environment
        if dev_disable_security:
            warnings.warn(
                "Security DISABLED via ROUTILUX_DEV_DISABLE_SECURITY. "
                "NEVER use this setting in production.",
                UserWarning,
                stacklevel=2
            )

    def _load_api_keys(self) -> List[str]:
        """Load API keys from environment.

        Supports:
        - ROUTILUX_API_KEY: Single API key
        - ROUTILUX_API_KEYS: Comma-separated list of API keys

        Returns:
            List of API keys.
        """
        keys = []

        # Single key
        single_key = os.getenv("ROUTILUX_API_KEY")
        if single_key:
            keys.append(single_key.strip())

        # Multiple keys
        multiple_keys = os.getenv("ROUTILUX_API_KEYS")
        if multiple_keys:
            keys.extend([k.strip() for k in multiple_keys.split(",") if k.strip()])

        return keys

    def is_api_key_valid(self, api_key: Optional[str]) -> bool:
        """Check if API key is valid.

        Args:
            api_key: API key to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not self.api_key_enabled:
            return True

        if not api_key:
            return False

        return api_key in self.api_keys


# Global config instance
_config: Optional[APIConfig] = None
_config_lock = threading.Lock()


def get_config() -> APIConfig:
    """Get global API config instance (thread-safe singleton)."""
    global _config
    if _config is None:
        with _config_lock:
            if _config is None:
                _config = APIConfig()
    return _config
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/server/test_config.py::test_default_security_is_enabled -v
```

Expected: PASS

### Step 5: Update auth middleware to warn on missing API keys

```python
# routilux/server/middleware/auth.py

"""
Authentication middleware for API.

All-or-nothing: when ROUTILUX_API_KEY_ENABLED=true, every endpoint requires X-API-Key.
When false (development only), all endpoints are public.
"""

import logging
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from routilux.server.config import get_config

logger = logging.getLogger(__name__)

# API Key header name
API_KEY_HEADER = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key from request header.

    Args:
        api_key: API key from request header.

    Returns:
        API key if valid, or 'anonymous' when auth is disabled.

    Raises:
        HTTPException: If API key is invalid or missing when auth is enabled.
    """
    config = get_config()

    # Auth disabled: allow all (development only)
    if not config.api_key_enabled:
        return api_key or "anonymous"

    # Check if API key is provided
    if not api_key:
        logger.warning("API request rejected: missing X-API-Key header")
        raise HTTPException(
            status_code=401,
            detail={
                "error": "authentication_required",
                "message": "API key is required. Provide it in the X-API-Key header.",
            },
        )

    # Validate API key
    if not config.is_api_key_valid(api_key):
        logger.warning(f"API request rejected: invalid API key (hash: {hash(api_key) % 10000})")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "invalid_api_key",
                "message": "Invalid API key provided.",
            },
        )

    return api_key


# Dependency for endpoints that require authentication
RequireAuth = Depends(verify_api_key)
```

**Step 6: Run all tests**

```bash
pytest tests/server/test_config.py -v
```

### Step 7: Commit

```bash
git add tests/server/test_config.py routilux/server/config.py routilux/server/middleware/auth.py
git commit -m "fix(server): enable security by default

- api_key_enabled defaults to True
- rate_limit_enabled defaults to True
- Add ROUTILUX_DEV_DISABLE_SECURITY for explicit development opt-out
- Add warning logs when security is disabled
- Add comprehensive tests for secure defaults

Resolves P0-1 from A04 code review"
```

---

## Task 2: Architecture - Remove Legacy Code (P0-2)

**Problem:** Dual architecture (Flow/JobState legacy vs Runtime/WorkerState new) creates complexity.

**Files:**
- Delete: `routilux/routine.py` (legacy Routine with mixins)
- Delete: `routilux/job_state.py`
- Delete: `routilux/connection.py`
- Delete: `routilux/error_handler.py`
- Delete: `routilux/execution_tracker.py`
- Delete: `routilux/routine_mixins.py`
- Delete: `routilux/event.py`
- Delete: `routilux/slot.py`
- Delete: `routilux/output_handler.py`
- Delete: `routilux/flow/` (entire directory)
- Modify: `routilux/__init__.py` (remove legacy exports)
- Test: `tests/test_legacy_removed.py`

### Step 1: Write test that verifies legacy is removed

```python
# tests/test_legacy_removed.py

import pytest


def test_legacy_routine_not_importable():
    """Legacy Routine should not be importable from root."""
    with pytest.raises(ImportError):
        from routilux import Routine  # This should fail


def test_legacy_job_state_not_importable():
    """Legacy JobState should not be importable."""
    with pytest.raises(ImportError):
        from routilux import JobState


def test_legacy_flow_not_importable():
    """Legacy Flow should not be importable."""
    with pytest.raises(ImportError):
        from routilux import Flow


def test_core_routine_is_available():
    """New core Routine should be available."""
    from routilux.core import Routine
    assert Routine is not None


def test_core_runtime_is_available():
    """New Runtime should be available."""
    from routilux.core import Runtime
    assert Runtime is not None
```

**Step 2: Run test to verify current state (will fail since legacy exists)**

```bash
pytest tests/test_legacy_removed.py -v
```

Expected: FAIL (legacy still exists)

### Step 3: Delete legacy files

```bash
cd /var/tmp/vibe-kanban/worktrees/4d68-routilux-i05-a04/routilux

# Delete legacy root-level files
rm -f routilux/routine.py
rm -f routilux/job_state.py
rm -f routilux/connection.py
rm -f routilux/error_handler.py
rm -f routilux/execution_tracker.py
rm -f routilux/routine_mixins.py
rm -f routilux/event.py
rm -f routilux/slot.py
rm -f routilux/output_handler.py

# Delete entire flow module
rm -rf routilux/flow/
```

### Step 4: Update __init__.py to export only new architecture

```python
# routilux/__init__.py

"""
Routilux - Event-driven workflow orchestration framework

Provides flexible connection, state management, and workflow orchestration capabilities.
"""

# Version
__version__ = "0.12.0"

# Core architecture (Runtime, Worker, Routine)
from routilux.core import (
    Event,
    ExecutionContext,
    Flow,  # New Flow from core
    FlowRegistry,
    JobContext,
    Routine,
    Runtime,
    Slot,
    WorkerState,
    get_current_execution_context,
    get_current_job,
    get_current_worker_state,
)

# Built-in routines
from routilux.builtin_routines import (
    ConditionalRouter,
    DataFlattener,
    DataTransformer,
    DataValidator,
    ResultExtractor,
    TextClipper,
    TextRenderer,
    TimeProvider,
)

# Exceptions
from routilux.exceptions import (
    ConfigurationError,
    ExecutionError,
    RoutiluxError,
    SerializationError,
    SlotHandlerError,
    StateError,
    ValidationError,
)

# Analysis tools
from routilux.analysis import (
    BaseFormatter,
    RoutineAnalyzer,
    RoutineMarkdownFormatter,
    WorkflowAnalyzer,
    WorkflowD2Formatter,
    analyze_routine_file,
    analyze_workflow,
)

# Monitoring
from routilux.monitoring import (
    BreakpointCondition,
    ExecutionHook,
    MonitoringRegistry,
)

__all__ = [
    # Version
    "__version__",
    # Core classes
    "Routine",
    "Runtime",
    "Flow",
    "FlowRegistry",
    "Event",
    "Slot",
    "WorkerState",
    "ExecutionContext",
    "JobContext",
    "get_current_execution_context",
    "get_current_job",
    "get_current_worker_state",
    # Built-in routines - Control flow
    "ConditionalRouter",
    # Built-in routines - Data processing
    "DataTransformer",
    "DataValidator",
    # Built-in routines - Text processing
    "TextClipper",
    "TextRenderer",
    "ResultExtractor",
    # Built-in routines - Utils
    "TimeProvider",
    "DataFlattener",
    # Exceptions
    "RoutiluxError",
    "ExecutionError",
    "SerializationError",
    "ConfigurationError",
    "StateError",
    "SlotHandlerError",
    "ValidationError",
    # Analysis tools
    "RoutineAnalyzer",
    "analyze_routine_file",
    "WorkflowAnalyzer",
    "analyze_workflow",
    "BaseFormatter",
    "RoutineMarkdownFormatter",
    "WorkflowD2Formatter",
    # Monitoring
    "MonitoringRegistry",
    "ExecutionHook",
    "BreakpointCondition",
]
```

**Step 5: Run test to verify legacy is removed**

```bash
pytest tests/test_legacy_removed.py -v
```

Expected: PASS

### Step 6: Update all example files to use new architecture

Find and update all imports in examples:

```bash
# Find files using legacy imports
grep -r "from routilux import Flow" examples/ || true
grep -r "from routilux import JobState" examples/ || true
grep -r "from routilux import Routine" examples/ || true
```

Update each file to use:
- `from routilux import Runtime, Flow, Routine` (new imports)
- `worker_state, job = runtime.post(...)` instead of `job_state = flow.execute(...)`

### Step 7: Run tests to identify broken tests

```bash
pytest tests/ -v --tb=no -q 2>&1 | head -50
```

Fix each failing test by updating to new architecture.

### Step 8: Commit

```bash
git add -A
git commit -m "refactor: remove legacy Flow/JobState architecture

- Delete legacy routilux/routine.py, job_state.py, connection.py
- Delete legacy flow/ module entirely
- Update __init__.py to export only new core architecture
- Migration guide:
  - Old: flow.execute() -> New: runtime.exec() + runtime.post()
  - Old: JobState -> New: WorkerState + JobContext
  - Old: routilux.Routine -> New: routilux.core.Routine

Resolves P0-2 from A04 code review"
```

---

## Task 3: Serialization Version Management (P0-3)

**Problem:** No version field in serialization format - cross-version upgrade may fail.

**Files:**
- Modify: `routilux/core/flow.py` (add version field)
- Modify: `routilux/flow/serialization.py` (handle version)
- Test: `tests/core/test_serialization_version.py`

### Step 1: Write test for version field

```python
# tests/core/test_serialization_version.py

import pytest
from routilux.core import Flow, Routine


def test_flow_serialization_includes_version():
    """Serialized flow should include version field."""
    flow = Flow("test_flow")
    routine = Routine()
    flow.add_routine(routine, "test_routine")

    serialized = flow.serialize()

    assert "version" in serialized, "Serialized data must include version field"
    assert isinstance(serialized["version"], int), "Version must be an integer"


def test_flow_deserialization_validates_version():
    """Deserialization should validate version compatibility."""
    flow = Flow("test_flow")
    routine = Routine()
    flow.add_routine(routine, "test_routine")

    serialized = flow.serialize()

    # Simulate future version
    serialized["version"] = 999

    with pytest.raises(SerializationError):
        flow.deserialize(serialized)
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/core/test_serialization_version.py -v
```

Expected: FAIL (no version field exists yet)

### Step 3: Add version constant and field

```python
# routilux/core/__init__.py

# Add at top of file
SERIALIZATION_VERSION = 1
SUPPORTED_SERIALIZATION_VERSIONS = {1}
```

```python
# routilux/core/flow.py

from serilux import Serializable
from routilux.core import SERIALIZATION_VERSION, SUPPORTED_SERIALIZATION_VERSIONS
from routilux.exceptions import SerializationError


class Flow(Serializable):
    """Flow manager for orchestrating workflow execution."""

    # Current serialization version
    _SERIALIZATION_VERSION = SERIALIZATION_VERSION

    def __init__(self, flow_id: str | None = None):
        """Initialize Flow."""
        super().__init__()
        self.flow_id: str = flow_id or str(uuid.uuid4())
        self._serialization_version: int = self._SERIALIZATION_VERSION

        # Register serializable fields including version
        self.add_serializable_fields([
            "_serialization_version",
            "flow_id",
            # ... other fields
        ])

    def serialize(self) -> dict[str, Any]:
        """Serialize Flow with version information."""
        data = super().serialize()
        data["version"] = self._SERIALIZATION_VERSION
        return data

    def deserialize(self, data: dict[str, Any], strict: bool = False, registry: Any = None) -> None:
        """Deserialize Flow with version validation."""
        # Check version before deserializing
        if "version" in data:
            version = data["version"]
            if version not in SUPPORTED_SERIALIZATION_VERSIONS:
                raise SerializationError(
                    f"Incompatible serialization version: {version}. "
                    f"Supported versions: {SUPPORTED_SERIALIZATION_VERSIONS}"
                )
            self._serialization_version = version
        else:
            # Legacy data without version field - assume version 0
            self._serialization_version = 0

        # Continue with normal deserialization
        super().deserialize(data, strict=strict, registry=registry)
```

**Step 4: Run test to verify it passes**

```bash
pytest tests/core/test_serialization_version.py -v
```

Expected: PASS

### Step 5: Add version migration framework for future use

```python
# routilux/core/migration.py

"""
Serialization version migration framework.

This module handles migrating serialized data between different versions.
"""

from typing import Any, Dict


class Migration:
    """Base class for version migrations."""

    def migrate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate data to next version.

        Args:
            data: Serialized data dictionary

        Returns:
            Migrated data dictionary
        """
        raise NotImplementedError


class MigrationRegistry:
    """Registry for version migrations."""

    _migrations: Dict[int, Migration] = {}

    @classmethod
    def register(cls, from_version: int, migration: Migration) -> None:
        """Register a migration from a specific version."""
        cls._migrations[from_version] = migration

    @classmethod
    def get_migration(cls, from_version: int) -> Migration | None:
        """Get migration for a specific version."""
        return cls._migrations.get(from_version)

    @classmethod
    def migrate(cls, data: Dict[str, Any], target_version: int) -> Dict[str, Any]:
        """Migrate data through multiple versions.

        Args:
            data: Serialized data dictionary
            target_version: Target version to migrate to

        Returns:
            Migrated data dictionary
        """
        current_version = data.get("version", 0)

        while current_version < target_version:
            migration = cls.get_migration(current_version)
            if migration is None:
                break
            data = migration.migrate(data)
            current_version = data.get("version", current_version + 1)

        return data
```

### Step 6: Commit

```bash
git add routilux/core/__init__.py routilux/core/flow.py routilux/core/migration.py tests/core/test_serialization_version.py
git commit -m "feat: add serialization version management

- Add SERIALIZATION_VERSION constant to core module
- Flow serialization now includes version field
- Deserialization validates version compatibility
- Add MigrationRegistry framework for future version migrations
- Add comprehensive tests for version handling

Resolves P0-3 from A04 code review"
```

---

## Task 4: Performance Benchmark Tests (P1-1)

**Problem:** Only micro-benchmarks exist; no end-to-end performance tests.

**Files:**
- Create: `tests/benchmarks/test_end_to_end_benchmark.py`
- Create: `tests/benchmarks/test_large_workflow_benchmark.py`

### Step 1: Write end-to-end benchmark test

```python
# tests/benchmarks/test_end_to_end_benchmark.py

"""
End-to-end performance benchmarks for Routilux.

These benchmarks test complete workflow execution with realistic data sizes.
"""

import pytest
from routilux.core import Runtime, Routine, Flow, FlowRegistry


class LinearProcessingRoutine(Routine):
    """Simple routine that passes through data."""

    def setup(self):
        self.add_slot("input")
        self.add_event("output")

    def logic(self, input_data, **kwargs):
        # Simulate some processing
        result = {"value": input_data.get("value", 0) * 2}
        self.emit("output", **result)


class EndToEndBenchmarks:
    """End-to-end performance benchmarks."""

    def test_linear_chain_10_routines(self, benchmark):
        """Benchmark a linear chain of 10 routines."""
        # Create flow with 10 routines in a chain
        flow = Flow("linear_chain")

        routines = []
        for i in range(10):
            routine = LinearProcessingRoutine()
            routines.append(routine)
            flow.add_routine(routine, f"r{i}")

        # Connect them in a chain
        for i in range(9):
            routines[i].get_event("output").connect(routines[i + 1].get_slot("input"))

        # Register flow
        registry = FlowRegistry.get_instance()
        registry.register(flow)

        # Create runtime
        runtime = Runtime(thread_pool_size=4)
        runtime.exec("linear_chain")

        def execute_chain():
            worker_state, job = runtime.post(
                "linear_chain", "r0", "input",
                {"value": 1}
            )
            # Wait for completion
            job.wait_for_completion(timeout=5.0)
            return job

        result = benchmark(execute_chain)
        assert result.status == "completed"

        # Cleanup
        runtime.shutdown()

    def test_parallel_execution_50_jobs(self, benchmark):
        """Benchmark 50 parallel jobs."""
        flow = Flow("parallel_test")
        routine = LinearProcessingRoutine()
        flow.add_routine(routine, "processor")

        registry = FlowRegistry.get_instance()
        registry.register(flow)

        runtime = Runtime(thread_pool_size=10)
        runtime.exec("parallel_test")

        def run_parallel_jobs():
            jobs = []
            for i in range(50):
                _, job = runtime.post(
                    "parallel_test", "processor", "input",
                    {"value": i}
                )
                jobs.append(job)

            # Wait for all
            for job in jobs:
                job.wait_for_completion(timeout=10.0)

            return jobs

        result = benchmark(run_parallel_jobs)
        assert len(result) == 50
        assert all(j.status == "completed" for j in result)

        runtime.shutdown()
```

### Step 2: Write large workflow benchmark

```python
# tests/benchmarks/test_large_workflow_benchmark.py

"""
Large workflow performance benchmarks.

Tests performance with hundreds of routines and complex connection patterns.
"""

import pytest
from routilux.core import Runtime, Routine, Flow, FlowRegistry


class LargeWorkflowBenchmarks:
    """Benchmarks for large-scale workflows."""

    def test_workflow_100_routines(self, benchmark):
        """Benchmark workflow with 100 routines."""
        flow = Flow("large_workflow")

        # Create 100 routines
        for i in range(100):
            routine = LinearProcessingRoutine()
            flow.add_routine(routine, f"r{i}")

        # Create a diamond pattern (each routine connects to next two)
        routines = list(flow.routines.values())
        for i in range(99):
            routines[i].get_event("output").connect(routines[i + 1].get_slot("input"))
            if i + 2 < 100:
                routines[i].get_event("output").connect(routines[i + 2].get_slot("input"))

        registry = FlowRegistry.get_instance()
        registry.register(flow)

        runtime = Runtime(thread_pool_size=10)
        runtime.exec("large_workflow")

        def execute_large():
            _, job = runtime.post("large_workflow", "r0", "input", {"value": 1})
            job.wait_for_completion(timeout=30.0)
            return job

        result = benchmark(execute_large)
        assert result.status == "completed"

        runtime.shutdown()

    def test_serialization_large_workflow(self, benchmark):
        """Benchmark serializing a workflow with 100 routines."""
        flow = Flow("serialization_test")

        for i in range(100):
            routine = LinearProcessingRoutine()
            flow.add_routine(routine, f"r{i}")

        def serialize_large():
            return flow.serialize()

        data = benchmark(serialize_large)
        assert "version" in data
        assert len(data["routines"]) == 100
```

### Step 3: Run benchmarks

```bash
pytest tests/benchmarks/test_end_to_end_benchmark.py -v --benchmark-only
pytest tests/benchmarks/test_large_workflow_benchmark.py -v --benchmark-only
```

### Step 4: Commit

```bash
git add tests/benchmarks/test_end_to_end_benchmark.py tests/benchmarks/test_large_workflow_benchmark.py
git commit -m "feat(benchmarks): add end-to-end performance tests

- Add test_end_to_end_benchmark.py for realistic workflow execution
- Add test_large_workflow_benchmark.py for scale testing (100+ routines)
- Test parallel execution with 50 concurrent jobs
- Test serialization performance for large workflows

Resolves P1-1 from A04 code review"
```

---

## Task 5: HTTP Server Audit Logging (P1-2)

**Problem:** No audit logs for security events and API access.

**Files:**
- Create: `routilux/server/audit.py`
- Modify: `routilux/server/main.py` (add audit middleware)
- Test: `tests/server/test_audit.py`

### Step 1: Write test for audit logging

```python
# tests/server/test_audit.py

import pytest
import json
from io import StringIO
from routilux.server.audit import AuditLogger


def test_audit_log_api_call():
    """Audit logger should record API calls."""
    output = StringIO()
    logger = AuditLogger(output)

    logger.log_api_call(
        api_key_hash="abc123",
        endpoint="/api/v1/flows",
        method="GET",
        status=200,
        duration_ms=45,
    )

    log_output = output.getvalue()
    log_data = json.loads(log_output)

    assert log_data["event_type"] == "api_call"
    assert log_data["endpoint"] == "/api/v1/flows"
    assert log_data["status"] == 200
    assert "timestamp" in log_data


def test_audit_log_auth_failure():
    """Audit logger should record authentication failures."""
    output = StringIO()
    logger = AuditLogger(output)

    logger.log_auth_failure(
        reason="missing_api_key",
        ip_address="127.0.0.1",
    )

    log_output = output.getvalue()
    log_data = json.loads(log_output)

    assert log_data["event_type"] == "auth_failure"
    assert log_data["reason"] == "missing_api_key"
```

**Step 2: Run test to verify it fails**

```bash
pytest tests/server/test_audit.py -v
```

Expected: FAIL (AuditLogger doesn't exist)

### Step 3: Implement audit logger

```python
# routilux/server/audit.py

"""
Audit logging for HTTP server.

Provides structured logging of security-relevant events including:
- API calls with authentication status
- Authentication failures
- Rate limit events
- Configuration changes
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, TextIO


class AuditLogger:
    """Structured audit logger for security events.

    Logs are written in JSON format for easy parsing and analysis.
    Sensitive data (API keys) is hashed before logging.
    """

    def __init__(self, output: TextIO | logging.Logger | None = None):
        """Initialize audit logger.

        Args:
            output: Output destination. Defaults to a logger named "routilux.audit".
        """
        if output is None:
            self._logger = logging.getLogger("routilux.audit")
            self._use_logger = True
        elif isinstance(output, logging.Logger):
            self._logger = output
            self._use_logger = True
        else:
            self._output = output
            self._use_logger = False

    def _write(self, data: dict[str, Any]) -> None:
        """Write audit log entry."""
        # Ensure timestamp
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

        if self._use_logger:
            self._logger.info(json.dumps(data))
        else:
            self._output.write(json.dumps(data) + "\n")
            self._output.flush()

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        status: int,
        duration_ms: float,
        api_key_hash: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Log an API call.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            status: HTTP status code
            duration_ms: Request duration in milliseconds
            api_key_hash: Hashed API key (first 8 chars)
            ip_address: Client IP address
        """
        self._write({
            "event_type": "api_call",
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "duration_ms": duration_ms,
            "api_key_hash": api_key_hash,
            "ip_address": ip_address,
        })

    def log_auth_failure(
        self,
        reason: str,
        ip_address: str | None = None,
        api_key_provided: bool = False,
    ) -> None:
        """Log an authentication failure.

        Args:
            reason: Reason for failure (e.g., "missing_api_key", "invalid_api_key")
            ip_address: Client IP address
            api_key_provided: Whether an API key was provided
        """
        self._write({
            "event_type": "auth_failure",
            "reason": reason,
            "ip_address": ip_address,
            "api_key_provided": api_key_provided,
        })

    def log_rate_limit_exceeded(
        self,
        api_key_hash: str | None,
        ip_address: str,
        limit: int,
    ) -> None:
        """Log a rate limit event.

        Args:
            api_key_hash: Hashed API key (first 8 chars)
            ip_address: Client IP address
            limit: Rate limit that was exceeded
        """
        self._write({
            "event_type": "rate_limit_exceeded",
            "api_key_hash": api_key_hash,
            "ip_address": ip_address,
            "limit": limit,
        })

    def log_configuration_change(
        self,
        setting: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Log a configuration change.

        Args:
            setting: Name of the setting that changed
            old_value: Previous value
            new_value: New value
        """
        self._write({
            "event_type": "configuration_change",
            "setting": setting,
            "old_value": str(old_value),
            "new_value": str(new_value),
        })


# Global audit logger instance
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        # Check if audit logging is disabled
        if os.getenv("ROUTILUX_AUDIT_LOGGING_ENABLED", "true").lower() == "false":
            _audit_logger = AuditLogger(output=None)  # No-op logger
        else:
            _audit_logger = AuditLogger()
    return _audit_logger
```

### Step 4: Add audit middleware to main.py

```python
# routilux/server/main.py

# Add after imports, before app creation

import time
from fastapi import Request
from routilux.server.audit import get_audit_logger

audit_logger = get_audit_logger()


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    """Middleware to audit all HTTP requests."""
    start_time = time.time()

    # Get client info
    client_ip = request.client.host if request.client else None

    # Get API key hash (if provided)
    api_key = request.headers.get("X-API-Key")
    api_key_hash = hash(api_key) % 10000000 if api_key else None

    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Log successful request
        audit_logger.log_api_call(
            endpoint=str(request.url.path),
            method=request.method,
            status=response.status_code,
            duration_ms=duration_ms,
            api_key_hash=str(api_key_hash) if api_key_hash else None,
            ip_address=client_ip,
        )

        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        # Log failed request
        audit_logger.log_api_call(
            endpoint=str(request.url.path),
            method=request.method,
            status=500,
            duration_ms=duration_ms,
            api_key_hash=str(api_key_hash) if api_key_hash else None,
            ip_address=client_ip,
        )

        raise
```

### Step 5: Update auth middleware to log failures

```python
# routilux/server/middleware/auth.py

# Add at top
from routilux.server.audit import get_audit_logger

audit_logger = get_audit_logger()


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key from request header."""
    config = get_config()
    client_ip = None  # Would need to be passed from request

    if not config.api_key_enabled:
        return api_key or "anonymous"

    if not api_key:
        audit_logger.log_auth_failure(
            reason="missing_api_key",
            ip_address=client_ip,
            api_key_provided=False,
        )
        raise HTTPException(status_code=401, detail={...})

    if not config.is_api_key_valid(api_key):
        audit_logger.log_auth_failure(
            reason="invalid_api_key",
            ip_address=client_ip,
            api_key_provided=True,
        )
        raise HTTPException(status_code=403, detail={...})

    return api_key
```

### Step 6: Run tests

```bash
pytest tests/server/test_audit.py -v
```

### Step 7: Commit

```bash
git add routilux/server/audit.py routilux/server/main.py routilux/server/middleware/auth.py tests/server/test_audit.py
git commit -m "feat(server): add audit logging

- Add AuditLogger for structured JSON logging
- Log API calls with timing, auth status, IP address
- Log authentication failures with reason
- Add audit middleware to track all HTTP requests
- Add ROUTILUX_AUDIT_LOGGING_ENABLED to disable if needed

Resolves P1-2 from A04 code review"
```

---

## Task 6: Error Handling Documentation (P1-3)

**Problem:** Error handling strategies are complex but documentation is scattered.

**Files:**
- Create: `docs/source/error_handling_guide.md`
- Create: `docs/source/examples/error_handling_examples.md`

### Step 1: Create error handling guide

```markdown
# docs/source/error_handling_guide.md

# Error Handling Guide

## Overview

Routilux provides flexible error handling strategies at both the Flow and Routine levels.

## Error Strategies

### STOP (Default)
Stop execution immediately when an error occurs.

**Use when:** The error is critical and subsequent work cannot proceed.

```python
from routilux import ErrorHandler, ErrorStrategy

handler = ErrorHandler(strategy=ErrorStrategy.STOP)
flow.set_error_handler(handler)
```

### CONTINUE
Log the error and continue with next routines.

**Use when:** The routine is optional and its failure shouldn't block the workflow.

```python
handler = ErrorHandler(strategy=ErrorStrategy.CONTINUE, is_critical=False)
routine.set_error_handler(handler)
```

### RETRY
Retry the routine a specified number of times before failing.

**Use when:** The error is transient (network issues, temporary unavailability).

```python
handler = ErrorHandler(
    strategy=ErrorStrategy.RETRY,
    max_retries=3,
    retry_delay=1.0,
    retry_backoff=2.0,
    is_critical=True
)
routine.set_error_handler(handler)
```

### SKIP
Skip the routine and continue with connected routines.

**Use when:** You want to bypass a failed routine but still execute downstream work.

## Decision Tree

```
Is the routine critical for workflow success?
├─ Yes → Use RETRY (with is_critical=True)
│       └─ Is the error transient?
│           ├─ Yes → Configure retry_delay and retry_backoff
│           └─ No → Use STOP (default)
└─ No → Use CONTINUE or SKIP
    └─ Should downstream routines still execute?
        ├─ Yes → Use CONTINUE
        └─ No → Use SKIP
```

## Priority

Error handlers are checked in this order:
1. Routine-level handler (highest priority)
2. Flow-level handler (default for all routines)
3. Default STOP behavior (fallback)
```

### Step 2: Create examples file

```python
# docs/source/examples/error_handling_examples.py

"""
Complete error handling examples for Routilux.
"""

from routilux import (
    ErrorHandler,
    ErrorStrategy,
    Routine,
    Flow,
)


# Example 1: Optional routine with CONTINUE
class OptionalEnrichmentRoutine(Routine):
    """Optional data enrichment that shouldn't block the workflow."""

    def setup(self):
        self.add_slot("input")
        self.add_event("output")

    def logic(self, input_data, **kwargs):
        try:
            # Call external API that might fail
            enriched = self._call_enrichment_api(input_data)
            self.emit("output", **enriched)
        except Exception:
            # Let CONTINUE strategy handle this
            raise


def optional_routine_example():
    """Example: Mark routine as optional."""
    flow = Flow()

    routine = OptionalEnrichmentRoutine()
    routine.set_as_optional()  # Uses CONTINUE strategy
    flow.add_routine(routine, "enricher")


# Example 2: Critical routine with RETRY
class CriticalAPICall(Routine):
    """Critical API call that must succeed."""

    def setup(self):
        self.add_slot("input")
        self.add_event("output")

    def logic(self, input_data, **kwargs):
        # Call critical API
        result = self._call_critical_api(input_data)
        self.emit("output", **result)


def critical_routine_example():
    """Example: Mark routine as critical with retry."""
    flow = Flow()

    routine = CriticalAPICall()
    routine.set_as_critical(
        max_retries=5,
        retry_delay=2.0,
        retry_backoff=2.0
    )
    flow.add_routine(routine, "caller")


# Example 3: Flow-level default handler
def flow_level_handler_example():
    """Example: Set default error handling for entire flow."""
    flow = Flow()

    # Set CONTINUE as default for all routines
    flow.set_error_handler(
        ErrorHandler(strategy=ErrorStrategy.CONTINUE, is_critical=False)
    )

    # Individual routines can override
    critical = CriticalAPICall()
    critical.set_as_critical()
    flow.add_routine(critical, "critical")
```

### Step 3: Commit

```bash
git add docs/source/error_handling_guide.md docs/source/examples/error_handling_examples.md
git commit -m "docs: add comprehensive error handling guide

- Add decision tree for choosing error strategies
- Document all error strategies (STOP, CONTINUE, RETRY, SKIP)
- Add complete code examples for each scenario
- Explain priority: routine-level > flow-level > default

Resolves P1-3 from A04 code review"
```

---

## Task 7: Add Detailed Comments (P2-1)

**Problem:** Complex functions lack detailed comments.

**Files:**
- Modify: `routilux/core/worker.py`
- Modify: `routilux/core/runtime.py`

### Step 1: Add detailed comments to WorkerExecutor.execute()

```python
# routilux/core/worker.py

def execute(self, routine: Routine, slot: Slot, data: dict[str, Any]) -> None:
    """Execute a routine with data from a slot.

    Execution Flow:
        1. Set context variables (worker_state, job_context, execution_context)
        2. Check activation policy (if defined)
        3. Call routine's logic() method
        4. Handle errors with appropriate strategy
        5. Clear context variables

    Args:
        routine: The Routine instance to execute
        slot: The Slot that triggered this execution
        data: Input data dictionary from the slot

    Raises:
        SlotQueueFullError: If a downstream slot queue is full
        RuntimeError: If execution context cannot be established
    """
    # Implementation...
```

### Step 2: Add detailed comments to Runtime._dispatch_event()

```python
# routilux/core/runtime.py

def _dispatch_event(
    self,
    event: Event,
    data: dict[str, Any],
    worker_state: WorkerState,
) -> None:
    """Dispatch an event to all connected slots.

    Dispatching Strategy:
        1. Get all slots connected to this event
        2. For each connected slot:
           a. Push data to slot queue (non-blocking)
           b. If queue full, apply backpressure (wait or raise)
        3. Schedule worker for any slots that now have pending data

    Args:
        event: The Event being dispatched
        data: Data payload to send to connected slots
        worker_state: Current WorkerState for tracking

    Raises:
        SlotQueueFullError: If a slot queue is full and backpressure is configured to raise
    """
    # Implementation...
```

### Step 3: Commit

```bash
git add routilux/core/worker.py routilux/core/runtime.py
git commit -m "docs: add detailed comments to complex functions

- Add execution flow documentation to WorkerExecutor.execute()
- Add dispatching strategy documentation to Runtime._dispatch_event
- Document all parameters, raises, and behavior

Resolves P2-1 from A04 code review"
```

---

## Task 8: TODO Tracking (P2-2)

**Problem:** TODO markers are not tracked.

**Files:**
- Modify: Remove TODO from `routilux/server/main.py:51`
- Create: `.github/ISSUE_TEMPLATE/TODO.md`

### Step 1: Find all TODOs

```bash
grep -r "TODO" routilux/ --include="*.py" || true
```

### Step 2: Address or create GitHub issues for each TODO

For each TODO found:
1. If it's a quick fix, fix it
2. Otherwise, create a GitHub issue with the TODO content

### Step 3: Remove TODO comment from main.py

```python
# routilux/server/main.py

# Remove or replace the TODO at line 51
# If it's a feature request, create a GitHub issue instead
```

### Step 4: Commit

```bash
git add routilux/server/main.py
git commit -m "chore: remove TODO markers and create GitHub issues

- Remove inline TODO from server/main.py
- Create corresponding GitHub issues for tracking
- Prefer issue tracking over inline TODOs

Resolves P2-2 from A04 code review"
```

---

## Task 9: Test Coverage Threshold (P2-3)

**Problem:** Test coverage threshold exists but is commented out.

**Files:**
- Modify: `pyproject.toml:122`

### Step 1: Uncomment and set coverage threshold

```toml
# pyproject.toml

[tool.coverage.run]
source = ["routilux"]
omit = ["*/tests/*", "*/test_*.py"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
# Enable coverage threshold
fail_under = 80
```

### Step 2: Run coverage to check current status

```bash
pytest --cov=routilux --cov-report=term-missing
```

If coverage is below 80%, incrementally improve or set a realistic threshold.

### Step 3: Commit

```bash
git add pyproject.toml
git commit -m "test: enable test coverage threshold enforcement

- Uncomment fail_under in coverage configuration
- Set threshold to 80% minimum coverage
- Run coverage in CI to prevent regressions

Resolves P2-3 from A04 code review"
```

---

## Summary

This plan addresses all P0, P1, and P2 issues from the A04 code review:

| Priority | Task | Status |
|----------|------|--------|
| P0-1 | Security defaults | Task 1 |
| P0-2 | Legacy removal | Task 2 |
| P0-3 | Serialization versioning | Task 3 |
| P1-1 | Performance benchmarks | Task 4 |
| P1-2 | Audit logging | Task 5 |
| P1-3 | Error handling docs | Task 6 |
| P2-1 | Detailed comments | Task 7 |
| P2-2 | TODO tracking | Task 8 |
| P2-3 | Coverage threshold | Task 9 |
