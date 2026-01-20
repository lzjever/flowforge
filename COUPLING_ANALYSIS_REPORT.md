# Routilux Coupling Analysis Report

**Date**: 2025-01-XX  
**Purpose**: Analyze coupling issues between core, monitoring, and other modules  
**Focus**: Identify dependencies that prevent core from being used independently

---

## Executive Summary

The analysis identified **3 major coupling issues** where `core` module depends on `monitoring`, preventing users from using core functionality without installing monitoring dependencies. Additionally, there are **2 architectural patterns** that could be improved for better separation of concerns.

---

## 1. Core → Monitoring Dependencies

### Issue 1.1: Direct Import in Runtime.handle_event_emit()

**Location**: `routilux/core/runtime.py:377, 467`

**Problem**:
```python
# Line 377
from routilux.monitoring.registry import MonitoringRegistry

# Line 467
from routilux.monitoring.event_manager import get_event_manager
```

**Impact**:
- Core module cannot be imported without monitoring module
- Users who only want core functionality must install monitoring dependencies
- Violates dependency inversion principle (core should not depend on monitoring)

**Current Usage**:
1. **Breakpoint checking** (lines 404-509): Checks for breakpoints before enqueueing data to slots
2. **Breakpoint event publishing** (lines 467-499): Publishes breakpoint_hit events via event manager

**Severity**: 🔴 **HIGH** - Blocks independent core usage

---

### Issue 1.2: Breakpoint Logic Embedded in Core

**Location**: `routilux/core/runtime.py:432-509`

**Problem**:
Breakpoint checking logic is directly embedded in `Runtime.handle_event_emit()`, which is a core execution method. This creates tight coupling:

```python
# Lines 432-509
if job_context and breakpoint_mgr:
    # ... breakpoint checking logic ...
    breakpoint = breakpoint_mgr.check_slot_breakpoint(...)
    if breakpoint is not None:
        # ... breakpoint handling ...
        event_manager = get_event_manager()
        # ... publish breakpoint_hit event ...
```

**Impact**:
- Core execution path includes monitoring-specific logic
- Cannot disable breakpoints without modifying core code
- Testing core functionality requires monitoring setup

**Severity**: 🔴 **HIGH** - Core logic polluted with monitoring concerns

---

### Issue 1.3: Event Manager Dependency for Breakpoint Events

**Location**: `routilux/core/runtime.py:467-499`

**Problem**:
When a breakpoint is hit, core directly calls monitoring's event manager to publish events:

```python
from routilux.monitoring.event_manager import get_event_manager
event_manager = get_event_manager()
# ... async event publishing ...
```

**Impact**:
- Core depends on monitoring's async event infrastructure
- Creates runtime dependency even if monitoring is "disabled"
- Event manager initialization may fail if monitoring not properly set up

**Severity**: 🟡 **MEDIUM** - Runtime dependency, but only triggered on breakpoint hit

---

## 2. Architectural Patterns Analysis

### Pattern 2.1: Hooks System (✅ Good Design)

**Location**: `routilux/core/hooks.py`

**Status**: ✅ **WELL DESIGNED**

The hooks system correctly uses **Dependency Inversion Principle**:
- Core defines `ExecutionHooksInterface` (abstraction)
- Monitoring provides `MonitoringExecutionHooks` (implementation)
- Default `NullExecutionHooks` allows core to work without monitoring
- Registration via `set_execution_hooks()` allows optional monitoring

**Current Usage**:
- `WorkerExecutor` calls hooks via `get_execution_hooks()` (lines 125-131, 393-399, 467-473, 495-501)
- `Runtime.post()` calls `on_job_start` hook (lines 264-273)
- `Runtime.handle_event_emit()` calls `on_event_emit` hook (lines 398-402)
- `JobContext.complete()` calls `on_job_end` hook (lines 259-281)

**Recommendation**: ✅ Keep this pattern, extend it for breakpoints

---

### Pattern 2.2: Registry Pattern (✅ Good Design)

**Location**: `routilux/core/registry.py`

**Status**: ✅ **WELL DESIGNED**

Core registries (`FlowRegistry`, `WorkerRegistry`) are self-contained:
- No dependencies on monitoring or server
- Use weak references for automatic cleanup
- Thread-safe singleton pattern

**Note**: Monitoring has its own `RuntimeRegistry` which is separate and appropriate.

---

## 3. Other Potential Issues

### Issue 3.1: Server → Monitoring Dependency (Expected)

**Location**: `routilux/server/main.py:34-49`

**Status**: ✅ **EXPECTED AND ACCEPTABLE**

Server module depends on monitoring, which is expected:
- Server is the API layer that provides monitoring features
- Server can require monitoring as a dependency
- This does not affect core independence

---

### Issue 3.2: Flow Module Independence (✅ Good)

**Status**: ✅ **NO ISSUES FOUND**

Flow module (`routilux/flow/`) has no dependencies on monitoring or server:
- Self-contained flow building and validation
- Can be used independently
- Proper separation of concerns

---

## 4. Improvement Recommendations

### Recommendation 4.1: Extract Breakpoint Checking to Hooks

**Approach**: Move breakpoint checking from `Runtime.handle_event_emit()` to hooks system

**Implementation**:
1. Add `on_slot_before_enqueue()` hook to `ExecutionHooksInterface`
2. Move breakpoint checking logic to `MonitoringExecutionHooks.on_slot_before_enqueue()`
3. Call hook in `Runtime.handle_event_emit()` before `slot.enqueue()`
4. Hook returns `(should_enqueue: bool, reason: str | None)` to control enqueueing

**Benefits**:
- Core no longer depends on monitoring
- Breakpoints become optional feature
- Easier to test core without monitoring
- Follows existing hooks pattern

**Code Changes**:
```python
# In core/hooks.py
@abstractmethod
def on_slot_before_enqueue(
    self,
    slot: Slot,
    routine_id: str,
    job_context: JobContext | None,
    data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Called before enqueueing data to a slot.
    
    Returns:
        (should_enqueue, reason) - If should_enqueue is False, 
        enqueue is skipped and reason is logged.
    """
    return True, None

# In core/runtime.py (simplified)
should_enqueue, reason = hooks.on_slot_before_enqueue(
    slot, target_routine_id, job_context, data
)
if not should_enqueue:
    logger.info(f"Skipping enqueue: {reason}")
    continue  # Skip this slot
```

---

### Recommendation 4.2: Lazy Import with Optional Dependency

**Approach**: Use lazy imports with try/except for optional monitoring features

**Implementation**:
```python
# In core/runtime.py
def _get_breakpoint_manager(self):
    """Get breakpoint manager if monitoring is available."""
    try:
        from routilux.monitoring.registry import MonitoringRegistry
        registry = MonitoringRegistry.get_instance()
        if registry and MonitoringRegistry.is_enabled():
            return registry.breakpoint_manager
    except ImportError:
        pass
    return None
```

**Benefits**:
- Core can be imported without monitoring
- Graceful degradation if monitoring not installed
- Runtime check instead of import-time dependency

**Drawback**: Still requires monitoring module structure to exist (even if empty)

**Better Alternative**: Use hooks system (Recommendation 4.1)

---

### Recommendation 4.3: Plugin Architecture for Optional Features

**Approach**: Make breakpoints a plugin that can be registered

**Implementation**:
1. Define `BreakpointProvider` interface in core
2. Monitoring provides implementation
3. Runtime checks for registered provider before checking breakpoints
4. Default: no provider = no breakpoints

**Benefits**:
- Clean separation of concerns
- Extensible for other plugins
- Core remains independent

**Complexity**: Higher implementation effort

---

## 5. Priority Recommendations

### Priority 1: Extract Breakpoint Checking to Hooks (Recommendation 4.1)

**Why**: 
- Solves the core coupling issue completely
- Follows existing architectural pattern
- Minimal API changes
- Maintains backward compatibility

**Effort**: Medium (2-3 days)
- Add hook method to interface
- Move breakpoint logic to monitoring hooks
- Update Runtime to use hook
- Update tests

---

### Priority 2: Remove Direct Monitoring Imports (Recommendation 4.2)

**Why**:
- Quick fix for import-time dependencies
- Allows core to be imported without monitoring
- Can be done in parallel with Priority 1

**Effort**: Low (1 day)
- Replace direct imports with lazy imports
- Add try/except blocks
- Test import behavior

---

### Priority 3: Consider Plugin Architecture (Recommendation 4.3)

**Why**:
- Long-term architectural improvement
- Enables extensibility
- Better separation of concerns

**Effort**: High (1-2 weeks)
- Design plugin interface
- Refactor breakpoint system
- Update documentation
- Migration guide

---

## 6. Impact Assessment

### Current State
- ❌ Core cannot be used without monitoring
- ❌ Importing core requires monitoring dependencies
- ✅ Hooks system is well-designed
- ✅ Flow module is independent
- ✅ Server → Monitoring dependency is acceptable

### After Priority 1 Implementation
- ✅ Core can be used without monitoring
- ✅ Importing core does not require monitoring
- ✅ Breakpoints work via hooks (optional)
- ✅ No API changes for users
- ✅ Backward compatible

### After Priority 2 Implementation
- ✅ Import-time dependencies removed
- ✅ Graceful degradation if monitoring not installed
- ⚠️ Still requires monitoring module structure

### After Priority 3 Implementation
- ✅ Plugin architecture for extensibility
- ✅ Clean separation of concerns
- ✅ Future features can use same pattern

---

## 7. Testing Strategy

### Test Core Independence
```python
# Test that core can be imported without monitoring
def test_core_import_without_monitoring():
    # Temporarily remove monitoring from path
    import sys
    monitoring_path = [p for p in sys.path if 'monitoring' in p]
    for p in monitoring_path:
        sys.path.remove(p)
    
    # Should still be able to import core
    from routilux.core import Runtime
    runtime = Runtime()
    assert runtime is not None
```

### Test Breakpoint Hook
```python
# Test breakpoint hook without monitoring
def test_breakpoint_hook():
    from routilux.core.hooks import NullExecutionHooks
    
    hooks = NullExecutionHooks()
    should_enqueue, reason = hooks.on_slot_before_enqueue(...)
    assert should_enqueue is True  # Null hooks allow enqueue
```

---

## 8. Migration Plan

### Phase 1: Add Hook Method (Non-Breaking)
1. Add `on_slot_before_enqueue()` to `ExecutionHooksInterface`
2. Implement in `NullExecutionHooks` (returns `True, None`)
3. Implement in `MonitoringExecutionHooks` (breakpoint logic)
4. Keep existing breakpoint code in Runtime (dual implementation)

### Phase 2: Switch to Hook (Non-Breaking)
1. Update `Runtime.handle_event_emit()` to call hook
2. Remove direct breakpoint checking code
3. Remove monitoring imports from Runtime
4. Test with and without monitoring

### Phase 3: Cleanup (Non-Breaking)
1. Remove old breakpoint code
2. Update documentation
3. Add migration guide

---

## 9. Summary

### Issues Found
1. **Core → Monitoring direct imports** (2 locations in runtime.py)
2. **Breakpoint logic embedded in core** (runtime.py:432-509)
3. **Event manager dependency for breakpoints** (runtime.py:467-499)

### Good Patterns
1. ✅ Hooks system (dependency inversion)
2. ✅ Registry pattern (self-contained)
3. ✅ Flow module independence

### Recommended Actions
1. **Priority 1**: Extract breakpoint checking to hooks system
2. **Priority 2**: Remove direct monitoring imports (lazy loading)
3. **Priority 3**: Consider plugin architecture for future

### Expected Outcome
- Core module can be used independently
- Monitoring becomes optional feature
- No breaking API changes
- Better separation of concerns
- Easier testing and maintenance

---

## 10. Appendix: Code Locations

### Core Dependencies on Monitoring
- `routilux/core/runtime.py:377` - `from routilux.monitoring.registry import MonitoringRegistry`
- `routilux/core/runtime.py:467` - `from routilux.monitoring.event_manager import get_event_manager`
- `routilux/core/runtime.py:404-509` - Breakpoint checking logic

### Hooks System (Good Pattern)
- `routilux/core/hooks.py` - Interface definition
- `routilux/monitoring/execution_hooks.py` - Implementation
- `routilux/core/executor.py` - Hook usage
- `routilux/core/runtime.py` - Hook usage

### Independent Modules
- `routilux/core/registry.py` - No external dependencies
- `routilux/flow/` - No monitoring/server dependencies
- `routilux/core/context.py` - No monitoring dependencies

---

**Report Generated**: 2025-01-XX  
**Next Review**: After Priority 1 implementation
