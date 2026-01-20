# Decoupling Execution Plan: Core from Monitoring

**Objective**: Remove all dependencies from `core` module on `monitoring` module  
**Principle**: Dependency Inversion - Core defines interfaces, Monitoring implements them  
**Constraint**: Zero breaking changes to public API  
**Timeline**: 2-3 days

---

## Pre-Execution Checklist

Before starting, verify:
- [ ] All existing tests pass: `uv run pytest tests/`
- [ ] No uncommitted changes: `git status`
- [ ] Create feature branch: `git checkout -b decouple-core-monitoring`
- [ ] Backup current state: `git commit -am "Backup before decoupling"`

---

## Phase 1: Add Hook Interface (Non-Breaking)

### Step 1.1: Add `on_slot_before_enqueue` Method to ExecutionHooksInterface

**File**: `routilux/core/hooks.py`

**Action**: Add new abstract method after `on_event_emit` method (after line 145, before line 147)

**Exact Code to Add**:

```python
    @abstractmethod
    def on_slot_before_enqueue(
        self,
        slot: "Slot",
        routine_id: str,
        job_context: "JobContext | None",
        data: dict[str, Any],
        flow_id: str,
    ) -> tuple[bool, str | None]:
        """Called before enqueueing data to a slot.
        
        This hook allows intercepting slot enqueue operations, for example
        to implement breakpoints or data validation.
        
        Args:
            slot: Slot that will receive the data
            routine_id: ID of the routine that owns the slot
            job_context: Current job context (may be None)
            data: Data dictionary that will be enqueued
            flow_id: ID of the flow containing the routine
        
        Returns:
            Tuple of (should_enqueue, reason):
            - should_enqueue: True to proceed with enqueue, False to skip
            - reason: Optional reason string if enqueue is skipped (for logging)
        
        Examples:
            >>> hooks = get_execution_hooks()
            >>> should_enqueue, reason = hooks.on_slot_before_enqueue(
            ...     slot, "routine_1", job_context, {"key": "value"}, "flow_1"
            ... )
            >>> if not should_enqueue:
            ...     logger.info(f"Skipping enqueue: {reason}")
        """
        return True, None
```

**Type Import Update**: Add `Slot` to TYPE_CHECKING imports (line 13-17)

**Exact Change**:
```python
if TYPE_CHECKING:
    from routilux.core.context import JobContext
    from routilux.core.event import Event
    from routilux.core.flow import Flow
    from routilux.core.slot import Slot  # ADD THIS LINE
    from routilux.core.worker import WorkerState
```

**Validation**:
- [ ] File syntax is valid: `python -m py_compile routilux/core/hooks.py`
- [ ] No import errors: `python -c "from routilux.core.hooks import ExecutionHooksInterface"`
- [ ] Type checking passes: `mypy routilux/core/hooks.py` (if configured)

---

### Step 1.2: Implement `on_slot_before_enqueue` in NullExecutionHooks

**File**: `routilux/core/hooks.py`

**Action**: Add implementation method in `NullExecutionHooks` class (after `on_event_emit` method, after line 198, before line 199)

**Exact Code to Add**:

```python
    def on_slot_before_enqueue(
        self,
        slot: "Slot",
        routine_id: str,
        job_context: "JobContext | None",
        data: dict[str, Any],
        flow_id: str,
    ) -> tuple[bool, str | None]:
        """Null implementation - always allows enqueue."""
        return True, None
```

**Validation**:
- [ ] File syntax is valid
- [ ] Can instantiate NullExecutionHooks: `python -c "from routilux.core.hooks import NullExecutionHooks; NullExecutionHooks().on_slot_before_enqueue(None, 'r1', None, {}, 'f1')"`
- [ ] Returns `(True, None)`: Verify return value matches expected tuple

---

### Step 1.3: Update Class Docstring

**File**: `routilux/core/hooks.py`

**Action**: Update `ExecutionHooksInterface` docstring (line 26-33) to include new hook

**Exact Change**:
```python
    """Abstract interface for execution lifecycle hooks.

    Core module defines this interface, monitoring module provides implementation.
    If no implementation is registered, NullExecutionHooks is used (no-op).

    Hook Methods:
        - on_worker_start: Worker begins execution
        - on_worker_stop: Worker stops execution
        - on_job_start: Job begins processing
        - on_job_end: Job finishes processing
        - on_routine_start: Routine begins execution
        - on_routine_end: Routine finishes execution
        - on_event_emit: Event is emitted
        - on_slot_before_enqueue: Before data is enqueued to a slot
    """
```

**Validation**:
- [ ] Docstring updated correctly
- [ ] No syntax errors

---

## Phase 2: Implement Hook in Monitoring (Non-Breaking)

### Step 2.1: Add Breakpoint Logic to MonitoringExecutionHooks

**File**: `routilux/monitoring/execution_hooks.py`

**Action**: Add new method `on_slot_before_enqueue` in `MonitoringExecutionHooks` class (after `on_event_emit` method, after line 421, before line 423)

**Exact Code to Add**:

```python
    def on_slot_before_enqueue(
        self,
        slot: "Slot",
        routine_id: str,
        job_context: "JobContext | None",
        data: dict[str, Any],
        flow_id: str,
    ) -> tuple[bool, str | None]:
        """Called before enqueueing data to a slot.
        
        Checks for breakpoints matching (job_id, routine_id, slot_name).
        If breakpoint is hit, returns False to skip enqueue and publishes
        breakpoint_hit event.
        
        Args:
            slot: Slot that will receive the data
            routine_id: ID of the routine that owns the slot
            job_context: Current job context (may be None)
            data: Data dictionary that will be enqueued
            flow_id: ID of the flow containing the routine
        
        Returns:
            Tuple of (should_enqueue, reason):
            - should_enqueue: False if breakpoint hit, True otherwise
            - reason: Breakpoint ID if breakpoint hit, None otherwise
        """
        from routilux.monitoring.registry import MonitoringRegistry
        from datetime import datetime

        # If monitoring not enabled or no job context, allow enqueue
        if not MonitoringRegistry.is_enabled() or not job_context:
            return True, None

        registry = MonitoringRegistry.get_instance()
        if not registry or not registry.breakpoint_manager:
            return True, None

        breakpoint_mgr = registry.breakpoint_manager
        slot_name = slot.name

        # Check for breakpoint
        logger.debug(
            f"Checking breakpoint: job_id={job_context.job_id}, "
            f"routine_id={routine_id}, slot_name={slot_name}, "
            f"data_keys={list(data.keys()) if isinstance(data, dict) else 'not_dict'}"
        )

        breakpoint = breakpoint_mgr.check_slot_breakpoint(
            job_id=job_context.job_id,
            routine_id=routine_id,
            slot_name=slot_name,
            context=None,  # Can be enhanced later if needed
            variables=data,  # Pass event data as variables for condition evaluation
        )

        if breakpoint is not None:
            # Breakpoint hit - skip enqueue and publish event
            logger.info(
                f"Breakpoint hit: job_id={job_context.job_id}, "
                f"routine_id={routine_id}, slot_name={slot_name}, "
                f"breakpoint_id={breakpoint.breakpoint_id}, condition={breakpoint.condition}"
            )

            # Publish breakpoint_hit event
            from routilux.monitoring.event_manager import get_event_manager

            event_manager = get_event_manager()
            try:
                # Use asyncio.create_task for fire-and-forget async call
                import asyncio

                try:
                    loop = asyncio.get_running_loop()
                    asyncio.create_task(
                        event_manager.publish(
                            job_context.job_id,
                            {
                                "type": "breakpoint_hit",
                                "job_id": job_context.job_id,
                                "timestamp": datetime.now().isoformat(),
                                "data": {
                                    "breakpoint_id": breakpoint.breakpoint_id,
                                    "routine_id": routine_id,
                                    "slot_name": slot_name,
                                    "condition": breakpoint.condition,
                                    "event_data": data,  # The data that would have been enqueued
                                },
                            },
                        )
                    )
                except RuntimeError:
                    # No event loop running - skip publishing
                    logger.debug(
                        "No event loop running, skipping breakpoint_hit event publish"
                    )
            except Exception as e:
                logger.warning(f"Failed to publish breakpoint_hit event: {e}")

            # Return False to skip enqueue
            return False, f"breakpoint_{breakpoint.breakpoint_id}"
        else:
            # Debug: Log when breakpoint check returns None
            logger.debug(
                f"No breakpoint match: job_id={job_context.job_id}, "
                f"routine_id={routine_id}, slot_name={slot_name}"
            )
            return True, None
```

**Type Import Update**: Add `Slot` to TYPE_CHECKING imports (line 18-22)

**Exact Change**:
```python
if TYPE_CHECKING:
    from routilux.core.context import JobContext
    from routilux.core.event import Event
    from routilux.core.flow import Flow
    from routilux.core.slot import Slot  # ADD THIS LINE
    from routilux.core.worker import WorkerState
```

**Validation**:
- [ ] File syntax is valid: `python -m py_compile routilux/monitoring/execution_hooks.py`
- [ ] No import errors: `python -c "from routilux.monitoring.execution_hooks import MonitoringExecutionHooks"`
- [ ] Method signature matches interface exactly
- [ ] Return type is `tuple[bool, str | None]`

---

### Step 2.2: Update MonitoringExecutionHooks Docstring

**File**: `routilux/monitoring/execution_hooks.py`

**Action**: Update class docstring (line 138-148) to mention breakpoint support

**Exact Change**:
```python
class MonitoringExecutionHooks(ExecutionHooksInterface):
    """Monitoring implementation of execution hooks.

    Implements ExecutionHooksInterface with:
    - Metrics collection via MonitorCollector
    - Breakpoint support via BreakpointManager (in on_slot_before_enqueue)
    - Event broadcasting via EventManager
    - Debug session management

    All methods check if monitoring is enabled before proceeding,
    ensuring zero overhead when monitoring is disabled.
    """
```

**Validation**:
- [ ] Docstring updated correctly

---

## Phase 3: Update Runtime to Use Hook (Breaking Internal, Non-Breaking External)

### Step 3.1: Remove Monitoring Imports from Runtime

**File**: `routilux/core/runtime.py`

**Action**: Remove or comment out the following import statements:

**Line 377** - REMOVE THIS LINE:
```python
from routilux.monitoring.registry import MonitoringRegistry
```

**Line 467** - REMOVE THIS LINE:
```python
from routilux.monitoring.event_manager import get_event_manager
```

**Validation**:
- [ ] Imports removed
- [ ] File still compiles: `python -m py_compile routilux/core/runtime.py`
- [ ] No references to `MonitoringRegistry` or `get_event_manager` remain in the file (except in comments)

---

### Step 3.2: Replace Breakpoint Logic with Hook Call

**File**: `routilux/core/runtime.py`

**Action**: Replace the entire breakpoint checking block (lines 404-509) with hook call

**Exact Replacement**:

**DELETE LINES 404-509** (entire breakpoint checking block):
```python
        # Get breakpoint manager if available
        breakpoint_mgr = None
        if job_context:
            registry = MonitoringRegistry.get_instance()
            if registry:
                breakpoint_mgr = registry.breakpoint_manager

        # Route to all connected slots
        for connection in connections:
            slot = connection.target_slot
            if slot is None:
                continue

            try:
                if not isinstance(event_data, dict):
                    logger.error(f"Invalid event_data type: {type(event_data).__name__}")
                    continue

                metadata = event_data.get("metadata")
                if not isinstance(metadata, dict):
                    logger.error("Invalid or missing metadata in event_data")
                    continue

                data = event_data.get("data", {})
                emitted_from = metadata.get("emitted_from", "unknown")
                emitted_at = metadata.get("emitted_at", datetime.now())

                # === BREAKPOINT CHECK (NEW) ===
                # Check if there's a breakpoint for this slot before enqueueing
                if job_context and breakpoint_mgr:
                    # Get target routine and slot information
                    target_routine = slot.routine
                    if target_routine is not None:
                        # Get routine_id from flow
                        target_routine_id = flow._get_routine_id(target_routine)
                        target_slot_name = slot.name

                        if target_routine_id:
                            # Check for breakpoint
                            # Debug: Log breakpoint check details
                            logger.debug(
                                f"Checking breakpoint: job_id={job_context.job_id}, "
                                f"routine_id={target_routine_id}, slot_name={target_slot_name}, "
                                f"data_keys={list(data.keys()) if isinstance(data, dict) else 'not_dict'}"
                            )

                            breakpoint = breakpoint_mgr.check_slot_breakpoint(
                                job_id=job_context.job_id,
                                routine_id=target_routine_id,
                                slot_name=target_slot_name,
                                context=None,  # Can be enhanced later if needed
                                variables=data,  # Pass event data as variables for condition evaluation
                            )

                            if breakpoint is not None:
                                # Breakpoint hit - skip enqueue and publish event
                                logger.info(
                                    f"Breakpoint hit: job_id={job_context.job_id}, "
                                    f"routine_id={target_routine_id}, slot_name={target_slot_name}, "
                                    f"breakpoint_id={breakpoint.breakpoint_id}, condition={breakpoint.condition}"
                                )

                                # Publish breakpoint_hit event
                                from routilux.monitoring.event_manager import get_event_manager

                                event_manager = get_event_manager()
                                try:
                                    # Use asyncio.create_task for fire-and-forget async call
                                    import asyncio

                                    try:
                                        loop = asyncio.get_running_loop()
                                        asyncio.create_task(
                                            event_manager.publish(
                                                job_context.job_id,
                                                {
                                                    "type": "breakpoint_hit",
                                                    "job_id": job_context.job_id,
                                                    "timestamp": datetime.now().isoformat(),
                                                    "data": {
                                                        "breakpoint_id": breakpoint.breakpoint_id,
                                                        "routine_id": target_routine_id,
                                                        "slot_name": target_slot_name,
                                                        "condition": breakpoint.condition,
                                                        "event_data": data,  # The data that would have been enqueued
                                                    },
                                                },
                                            )
                                        )
                                    except RuntimeError:
                                        # No event loop running - skip publishing
                                        logger.debug(
                                            "No event loop running, skipping breakpoint_hit event publish"
                                        )
                                except Exception as e:
                                    logger.warning(f"Failed to publish breakpoint_hit event: {e}")

                                # Skip this enqueue operation
                                continue
                            else:
                                # Debug: Log when breakpoint check returns None
                                logger.debug(
                                    f"No breakpoint match: job_id={job_context.job_id}, "
                                    f"routine_id={target_routine_id}, slot_name={target_slot_name}"
                                )
                # === END BREAKPOINT CHECK ===

                slot.enqueue(
                    data=data,
                    emitted_from=emitted_from,
                    emitted_at=emitted_at,
                )
```

**REPLACE WITH** (insert at the same location, after line 402):
```python
        # Route to all connected slots
        for connection in connections:
            slot = connection.target_slot
            if slot is None:
                continue

            try:
                if not isinstance(event_data, dict):
                    logger.error(f"Invalid event_data type: {type(event_data).__name__}")
                    continue

                metadata = event_data.get("metadata")
                if not isinstance(metadata, dict):
                    logger.error("Invalid or missing metadata in event_data")
                    continue

                data = event_data.get("data", {})
                emitted_from = metadata.get("emitted_from", "unknown")
                emitted_at = metadata.get("emitted_at", datetime.now())

                # Get target routine and slot information for hook
                target_routine = slot.routine
                target_routine_id = None
                if target_routine is not None:
                    target_routine_id = flow._get_routine_id(target_routine)

                # Call hook before enqueueing
                should_enqueue, reason = hooks.on_slot_before_enqueue(
                    slot=slot,
                    routine_id=target_routine_id or "",
                    job_context=job_context,
                    data=data,
                    flow_id=flow.flow_id,
                )

                if not should_enqueue:
                    # Hook indicates we should skip enqueue (e.g., breakpoint hit)
                    if reason:
                        logger.info(f"Skipping slot enqueue: {reason}")
                    continue

                # Proceed with enqueue
                slot.enqueue(
                    data=data,
                    emitted_from=emitted_from,
                    emitted_at=emitted_at,
                )
```

**Validation**:
- [ ] Old breakpoint code completely removed
- [ ] New hook call code added
- [ ] File compiles: `python -m py_compile routilux/core/runtime.py`
- [ ] No references to `MonitoringRegistry` or `get_event_manager` in runtime.py
- [ ] Hook call uses correct parameters matching interface signature

---

### Step 3.3: Update Runtime Docstring

**File**: `routilux/core/runtime.py`

**Action**: Update `handle_event_emit` method docstring (lines 303-356) to reflect hook usage

**Find and Replace** in the docstring:

**OLD** (around line 324):
```python
        1. **Breakpoint checking**: Breakpoints are matched by (job_id, routine_id, slot_name).
           Without job_context, breakpoints will not trigger.
```

**REPLACE WITH**:
```python
        1. **Hook-based interception**: The `on_slot_before_enqueue` hook is called before
           enqueueing data to slots. This allows breakpoints and other interceptors to
           control whether data is enqueued. Without job_context, hooks may not function
           correctly.
```

**OLD** (around line 351):
```python
        **Breakpoint Mechanism:**
        Before enqueueing data to a slot, this method checks for breakpoints matching
        (job_id, routine_id, slot_name). If a breakpoint matches and its condition
        (if any) evaluates to True, the enqueue operation is skipped, effectively
        intercepting the event at that slot.
```

**REPLACE WITH**:
```python
        **Hook-Based Interception:**
        Before enqueueing data to a slot, this method calls the `on_slot_before_enqueue`
        hook. If the hook returns `should_enqueue=False`, the enqueue operation is
        skipped. This mechanism is used by monitoring to implement breakpoints, but
        can be used for other interception purposes as well.
```

**Validation**:
- [ ] Docstring updated correctly
- [ ] No references to direct breakpoint checking remain
- [ ] Mentions hook-based approach

---

## Phase 4: Testing and Validation

### Step 4.1: Unit Test - Hook Interface

**File**: `tests/test_core_hooks.py` (create if doesn't exist)

**Action**: Add test for new hook method

**Exact Test Code**:

```python
"""Tests for core hooks interface."""

import pytest
from routilux.core.hooks import (
    ExecutionHooksInterface,
    NullExecutionHooks,
    get_execution_hooks,
    set_execution_hooks,
    reset_execution_hooks,
)


def test_null_hooks_on_slot_before_enqueue():
    """Test that NullExecutionHooks allows all enqueues."""
    hooks = NullExecutionHooks()
    
    # Should always return (True, None) - allow enqueue
    should_enqueue, reason = hooks.on_slot_before_enqueue(
        slot=None,  # Slot not needed for null implementation
        routine_id="test_routine",
        job_context=None,
        data={"key": "value"},
        flow_id="test_flow",
    )
    
    assert should_enqueue is True
    assert reason is None


def test_hook_interface_requires_implementation():
    """Test that ExecutionHooksInterface requires on_slot_before_enqueue."""
    # Create a partial implementation
    class PartialHooks(ExecutionHooksInterface):
        def on_worker_start(self, flow, worker_state):
            pass
        def on_worker_stop(self, flow, worker_state, status):
            pass
        def on_job_start(self, job_context, worker_state):
            pass
        def on_job_end(self, job_context, worker_state, status="completed", error=None):
            pass
        def on_routine_start(self, routine_id, worker_state, job_context=None):
            return True
        def on_routine_end(self, routine_id, worker_state, job_context=None, status="completed", error=None):
            pass
        def on_event_emit(self, event, source_routine_id, worker_state, job_context=None, data=None):
            return True
        # Missing on_slot_before_enqueue - should fail
    
    # Should raise TypeError when trying to instantiate
    with pytest.raises(TypeError):
        PartialHooks()
```

**Validation**:
- [ ] Test file created
- [ ] Tests pass: `uv run pytest tests/test_core_hooks.py -v`
- [ ] All assertions pass

---

### Step 4.2: Integration Test - Runtime Uses Hook

**File**: `tests/test_core_runtime.py` (or existing runtime test file)

**Action**: Add test to verify Runtime calls hook

**Exact Test Code**:

```python
"""Test that Runtime calls on_slot_before_enqueue hook."""

import pytest
from unittest.mock import Mock, MagicMock
from routilux.core import Runtime
from routilux.core.hooks import ExecutionHooksInterface, set_execution_hooks


class TestHook(ExecutionHooksInterface):
    """Test hook implementation that tracks calls."""
    
    def __init__(self):
        self.calls = []
        self.should_enqueue = True
        self.reason = None
    
    def on_worker_start(self, flow, worker_state):
        pass
    def on_worker_stop(self, flow, worker_state, status):
        pass
    def on_job_start(self, job_context, worker_state):
        pass
    def on_job_end(self, job_context, worker_state, status="completed", error=None):
        pass
    def on_routine_start(self, routine_id, worker_state, job_context=None):
        return True
    def on_routine_end(self, routine_id, worker_state, job_context=None, status="completed", error=None):
        pass
    def on_event_emit(self, event, source_routine_id, worker_state, job_context=None, data=None):
        return True
    
    def on_slot_before_enqueue(self, slot, routine_id, job_context, data, flow_id):
        """Track calls and return configured value."""
        self.calls.append({
            "slot": slot,
            "routine_id": routine_id,
            "job_context": job_context,
            "data": data,
            "flow_id": flow_id,
        })
        return self.should_enqueue, self.reason


def test_runtime_calls_on_slot_before_enqueue_hook():
    """Test that Runtime.handle_event_emit calls on_slot_before_enqueue hook."""
    # Setup
    test_hook = TestHook()
    set_execution_hooks(test_hook)
    
    try:
        # Create minimal runtime and flow
        runtime = Runtime(thread_pool_size=1)
        
        # Create a simple flow with two routines connected
        from routilux.core.flow import Flow
        from routilux.core.routine import Routine
        from routilux.core.slot import Slot
        from routilux.core.event import Event
        
        flow = Flow(flow_id="test_flow")
        
        # Create source routine
        source_routine = Routine()
        source_output = Event("output", source_routine)
        source_routine.add_event(source_output)
        flow.add_routine("source", source_routine)
        
        # Create target routine
        target_routine = Routine()
        target_input = Slot("input", target_routine)
        target_routine.add_slot(target_input)
        flow.add_routine("target", target_routine)
        
        # Connect them
        flow.connect(source_output, target_input)
        
        # Register flow
        from routilux.core.registry import FlowRegistry
        FlowRegistry.get_instance().register(flow)
        
        # Create worker and job
        worker_state = runtime.exec("test_flow")
        from routilux.core.context import JobContext
        job_context = JobContext(
            job_id="test_job",
            worker_id=worker_state.worker_id,
            flow_id=flow.flow_id,
        )
        
        # Emit event
        source_output.emit(
            runtime=runtime,
            worker_state=worker_state,
            data={"test": "value"},
        )
        
        # Give it a moment to process
        import time
        time.sleep(0.1)
        
        # Verify hook was called
        assert len(test_hook.calls) > 0, "Hook should have been called"
        
        call = test_hook.calls[0]
        assert call["routine_id"] == "target" or call["routine_id"] == ""
        assert call["flow_id"] == "test_flow"
        assert call["data"] == {"test": "value"}
        
    finally:
        # Cleanup
        from routilux.core.hooks import reset_execution_hooks
        reset_execution_hooks()
```

**Validation**:
- [ ] Test added to appropriate test file
- [ ] Test passes: `uv run pytest tests/test_core_runtime.py::test_runtime_calls_on_slot_before_enqueue_hook -v`
- [ ] Hook is actually called during event routing

---

### Step 4.3: Integration Test - Breakpoint Still Works

**File**: `tests/test_breakpoint_runtime_integration_comprehensive.py` (or existing breakpoint test)

**Action**: Verify existing breakpoint tests still pass

**Validation**:
- [ ] All breakpoint tests pass: `uv run pytest tests/test_breakpoint* -v`
- [ ] Breakpoints still trigger correctly
- [ ] Breakpoint events are still published
- [ ] No regression in breakpoint functionality

---

### Step 4.4: Test Core Independence

**File**: `tests/test_core_independence.py` (create new)

**Action**: Verify core can be imported and used without monitoring

**Exact Test Code**:

```python
"""Test that core module can be used without monitoring module."""

import sys
import importlib
from pathlib import Path


def test_core_import_without_monitoring():
    """Test that core can be imported even if monitoring is not available."""
    # This test verifies that core module has no hard dependencies on monitoring
    # at import time
    
    # Import core - should succeed
    from routilux.core import Runtime, Flow, Routine
    from routilux.core.hooks import ExecutionHooksInterface, NullExecutionHooks
    
    # Verify we can use core without monitoring
    runtime = Runtime(thread_pool_size=1)
    assert runtime is not None
    
    # Verify hooks work without monitoring
    hooks = NullExecutionHooks()
    should_enqueue, reason = hooks.on_slot_before_enqueue(
        slot=None,
        routine_id="test",
        job_context=None,
        data={},
        flow_id="test",
    )
    assert should_enqueue is True
    assert reason is None


def test_runtime_no_monitoring_imports():
    """Test that Runtime module does not import monitoring at module level."""
    import routilux.core.runtime as runtime_module
    
    # Check that monitoring is not in the module's globals at import time
    # (it may be imported lazily in functions, which is OK)
    module_source = Path(runtime_module.__file__).read_text()
    
    # Should not have top-level imports from monitoring
    lines = module_source.split('\n')
    top_level_imports = [
        line.strip() 
        for line in lines 
        if line.strip().startswith('from routilux.monitoring') 
        or line.strip().startswith('import routilux.monitoring')
    ]
    
    # All monitoring imports should be inside functions (lazy imports)
    # or in TYPE_CHECKING blocks
    for imp in top_level_imports:
        # Check if it's in a function or TYPE_CHECKING
        # This is a simple check - in practice, we rely on the fact that
        # we removed the imports in Step 3.1
        assert 'TYPE_CHECKING' in imp or imp == '', \
            f"Found top-level monitoring import: {imp}. Should be lazy import inside function."
```

**Validation**:
- [ ] Test file created
- [ ] Tests pass: `uv run pytest tests/test_core_independence.py -v`
- [ ] Core can be imported without monitoring module
- [ ] No import errors when monitoring is unavailable

---

### Step 4.5: Run Full Test Suite

**Action**: Run all tests to ensure no regressions

**Commands**:
```bash
# Run all tests
uv run pytest tests/ -v

# Run core tests specifically
uv run pytest tests/test_core* -v

# Run breakpoint tests
uv run pytest tests/test_breakpoint* -v

# Run integration tests
uv run pytest tests/test_*integration* -v
```

**Validation**:
- [ ] All existing tests pass
- [ ] No test failures introduced
- [ ] No deprecation warnings related to our changes
- [ ] Test coverage maintained or improved

---

## Phase 5: Documentation Updates

### Step 5.1: Update Hooks Documentation

**File**: `routilux/core/hooks.py`

**Action**: Ensure docstrings are complete and accurate (already done in Phase 1)

**Validation**:
- [ ] All docstrings are present
- [ ] Examples are correct
- [ ] Type hints are accurate

---

### Step 5.2: Update Runtime Documentation

**File**: `routilux/core/runtime.py`

**Action**: Ensure `handle_event_emit` docstring is updated (already done in Step 3.3)

**Validation**:
- [ ] Docstring reflects hook-based approach
- [ ] No references to direct breakpoint checking

---

### Step 5.3: Update Monitoring Documentation

**File**: `routilux/monitoring/execution_hooks.py`

**Action**: Ensure class docstring mentions breakpoint support (already done in Step 2.2)

**Validation**:
- [ ] Docstring is accurate
- [ ] Mentions breakpoint functionality

---

## Phase 6: Final Validation

### Step 6.1: Code Review Checklist

Verify:
- [ ] No `from routilux.monitoring` imports in `routilux/core/runtime.py`
- [ ] No `MonitoringRegistry` references in `routilux/core/runtime.py`
- [ ] No `get_event_manager` calls in `routilux/core/runtime.py`
- [ ] Hook interface has `on_slot_before_enqueue` method
- [ ] `NullExecutionHooks` implements `on_slot_before_enqueue`
- [ ] `MonitoringExecutionHooks` implements `on_slot_before_enqueue`
- [ ] `Runtime.handle_event_emit` calls hook instead of checking breakpoints directly
- [ ] All tests pass
- [ ] No breaking API changes

---

### Step 6.2: Import Test

**Action**: Verify core can be imported without monitoring

**Command**:
```bash
python -c "
import sys
# Remove monitoring from path temporarily
sys.path = [p for p in sys.path if 'monitoring' not in p.lower() or 'routilux' not in p.lower()]

# Should still be able to import core
from routilux.core import Runtime
from routilux.core.hooks import ExecutionHooksInterface, NullExecutionHooks

# Should be able to use core
runtime = Runtime(thread_pool_size=1)
hooks = NullExecutionHooks()
result = hooks.on_slot_before_enqueue(None, 'r1', None, {}, 'f1')
assert result == (True, None)
print('SUCCESS: Core can be used without monitoring')
"
```

**Validation**:
- [ ] Command succeeds
- [ ] No import errors
- [ ] Core functionality works

---

### Step 6.3: Breakpoint Functionality Test

**Action**: Manually test breakpoint functionality still works

**Steps**:
1. Start API server: `uv run python -m routilux.server.main`
2. Create a flow with breakpoint
3. Set breakpoint via API
4. Execute flow
5. Verify breakpoint triggers
6. Verify breakpoint_hit event is published

**Validation**:
- [ ] Breakpoints still work
- [ ] Breakpoint events are published
- [ ] No errors in logs

---

## Phase 7: Cleanup and Commit

### Step 7.1: Remove Obsolete Comments

**File**: `routilux/monitoring/execution_hooks.py`

**Action**: Update comment in `on_event_emit` method (line 418-419)

**Find**:
```python
        # Note: Breakpoints are now checked during event routing in Runtime.handle_event_emit
        # when data is about to be enqueued to slots. No breakpoint check needed here for event emit.
```

**Replace With**:
```python
        # Note: Breakpoints are checked in on_slot_before_enqueue hook when data is about
        # to be enqueued to slots. No breakpoint check needed here for event emit.
```

**Validation**:
- [ ] Comment updated
- [ ] No obsolete references remain

---

### Step 7.2: Run Linter

**Action**: Ensure code quality

**Commands**:
```bash
# Run ruff
uv run ruff check routilux/core/hooks.py routilux/core/runtime.py routilux/monitoring/execution_hooks.py

# Fix any issues
uv run ruff check --fix routilux/core/hooks.py routilux/core/runtime.py routilux/monitoring/execution_hooks.py
```

**Validation**:
- [ ] No linting errors
- [ ] Code follows style guidelines

---

### Step 7.3: Commit Changes

**Action**: Commit all changes

**Commands**:
```bash
# Stage all changes
git add routilux/core/hooks.py
git add routilux/core/runtime.py
git add routilux/monitoring/execution_hooks.py
git add tests/

# Commit
git commit -m "refactor: decouple core from monitoring using hooks

- Add on_slot_before_enqueue hook to ExecutionHooksInterface
- Move breakpoint checking logic from Runtime to MonitoringExecutionHooks
- Remove monitoring imports from Runtime module
- Maintain backward compatibility - no API changes
- All tests pass, breakpoint functionality preserved"
```

**Validation**:
- [ ] All changes committed
- [ ] Commit message is clear
- [ ] No uncommitted changes

---

## Acceptance Criteria

### Must Have (All Required)
- [ ] Core module has zero imports from monitoring module
- [ ] Core can be imported and used without monitoring module installed
- [ ] All existing tests pass (no regressions)
- [ ] Breakpoint functionality still works correctly
- [ ] Hook interface is properly defined and documented
- [ ] Null implementation allows all enqueues (backward compatible)
- [ ] Monitoring implementation handles breakpoints correctly

### Should Have (Highly Recommended)
- [ ] New tests verify hook is called
- [ ] New tests verify core independence
- [ ] Documentation is updated
- [ ] Code passes linting
- [ ] No performance regression

### Nice to Have (Optional)
- [ ] Performance benchmarks show no degradation
- [ ] Additional hook examples in documentation

---

## Rollback Plan

If issues are discovered:

1. **Revert commit**: `git revert HEAD`
2. **Restore from backup**: `git checkout backup-before-decoupling -- routilux/`
3. **Verify**: Run tests to ensure rollback succeeded

---

## Post-Execution

After completion:
1. Create pull request with changes
2. Request code review
3. Run CI/CD pipeline
4. Update changelog if needed
5. Update architecture documentation

---

## Notes for Developers

### Key Principles Applied
1. **Dependency Inversion**: Core defines interface, Monitoring implements
2. **Open/Closed Principle**: Extend via hooks, don't modify core
3. **Single Responsibility**: Breakpoint logic belongs in monitoring, not core
4. **Backward Compatibility**: No breaking changes to public API

### Common Pitfalls to Avoid
1. **Don't** add monitoring imports back to Runtime
2. **Don't** skip the hook call - always call it before enqueue
3. **Don't** change hook signature - it must match interface exactly
4. **Don't** forget to update both NullExecutionHooks and MonitoringExecutionHooks
5. **Don't** remove tests - add new ones instead

### Testing Strategy
- Test hook interface independently
- Test Runtime calls hook
- Test breakpoint functionality end-to-end
- Test core independence
- Test backward compatibility

---

**End of Execution Plan**
