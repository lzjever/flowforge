# Routilux API & Monitoring System Compatibility Analysis Report

**Date**: 2026-01-16  
**Scope**: Analysis of API, DSL, and Monitoring code compatibility with new Runtime-based design  
**Goal**: Evaluate if current implementation can satisfy HTTP monitoring and debugging requirements

---

## Executive Summary

The current API and monitoring system have **significant compatibility issues** with the new Runtime-based design. While the core infrastructure (Flow structure viewing, basic job tracking) works, critical features for monitoring and debugging are **broken or missing**:

### 🔴 Critical Issues
1. **API uses obsolete execution model** - `flow.start()` doesn't exist in new design
2. **Monitoring hooks not integrated** - Runtime doesn't call execution hooks
3. **Event/slot tracking missing** - No hooks called during event routing
4. **Connection-level breakpoints not supported** - Only routine/slot/event breakpoints exist

### ⚠️ Partial Support
1. **Flow structure viewing** - ✅ Works (Flow is static)
2. **Job state tracking** - ⚠️ Works but incomplete (no routine activation tracking)
3. **Basic breakpoints** - ⚠️ Infrastructure exists but not called

### ✅ Working Features
1. Flow structure API (`/api/flows`)
2. Job listing and basic status (`/api/jobs`)
3. Breakpoint management API (infrastructure)
4. DSL loading and export

---

## 1. User Requirements Analysis

### Required Features
1. ✅ **View Flow Structure** - See routines, connections, configuration
2. ⚠️ **View Job Execution State** - See job status, but missing routine activation details
3. ❌ **View Node Activation & Work Status** - Not tracked (hooks not called)
4. ❌ **View Event Trigger & Response Status** - Not tracked (hooks not called)
5. ⚠️ **Set Breakpoints on Event-to-Slot Connections** - Infrastructure exists but not fully functional

---

## 2. Current Implementation Status

### 2.1 Flow Structure Viewing ✅ **FULLY COMPATIBLE**

**Status**: ✅ **WORKS**

**Implementation**: `routilux/api/routes/flows.py`

**Analysis**:
- Flow is now static (no runtime state) - ✅ Perfect for viewing
- API endpoints correctly read Flow structure:
  - `GET /api/flows` - Lists all flows
  - `GET /api/flows/{flow_id}` - Gets flow details
  - `GET /api/flows/{flow_id}/routines` - Lists routines
  - `GET /api/flows/{flow_id}/connections` - Lists connections
- FlowRegistry integration works correctly
- DSL export (`GET /api/flows/{flow_id}/dsl`) works

**Conclusion**: No changes needed.

---

### 2.2 Job Execution State Viewing ⚠️ **PARTIALLY COMPATIBLE**

**Status**: ⚠️ **WORKS BUT INCOMPLETE**

**Current Implementation**: `routilux/api/routes/jobs.py`

**What Works**:
- ✅ Job listing (`GET /api/jobs`)
- ✅ Job details (`GET /api/jobs/{job_id}`)
- ✅ Job status (`GET /api/jobs/{job_id}/status`)
- ✅ Job state serialization (`GET /api/jobs/{job_id}/state`)

**What's Missing**:
- ❌ **Routine activation status** - Not tracked in Runtime
- ❌ **Routine execution history** - JobState has `execution_history` but Runtime doesn't populate it properly
- ❌ **Real-time routine status** - No way to see which routines are currently executing

**Root Cause**: 
- Runtime doesn't call `execution_hooks.on_routine_start()` or `on_routine_end()`
- JobState tracking is minimal (only marks routine as completed/failed)

**Required Fix**:
```python
# In Runtime._activate_routine()
from routilux.monitoring.hooks import execution_hooks

# Before logic execution
execution_hooks.on_routine_start(routine, routine_id, job_state)

# After logic execution (in try/except)
execution_hooks.on_routine_end(routine, routine_id, job_state, status="completed")
```

---

### 2.3 Node Activation & Work Status ❌ **NOT WORKING**

**Status**: ❌ **BROKEN**

**Problem**: Runtime doesn't track routine activation or execution.

**Current State**:
- `Runtime._activate_routine()` executes logic but doesn't:
  - Call monitoring hooks
  - Track activation time
  - Track execution duration
  - Record activation events

**Required Integration Points**:

1. **In `Runtime._check_routine_activation()`**:
   ```python
   from routilux.monitoring.hooks import execution_hooks
   from routilux.monitoring.registry import MonitoringRegistry
   
   # Track activation check
   if MonitoringRegistry.is_enabled():
       collector = MonitoringRegistry.get_instance().monitor_collector
       if collector:
           collector.record_routine_activation_check(routine_id, job_state.job_id)
   ```

2. **In `Runtime._activate_routine()`**:
   ```python
   # Track routine start
   execution_hooks.on_routine_start(routine, routine_id, job_state)
   
   # Track routine end (in finally block)
   execution_hooks.on_routine_end(routine, routine_id, job_state, status, error)
   ```

**Impact**: 
- `/api/jobs/{job_id}/metrics` will return empty/incomplete data
- `/api/jobs/{job_id}/trace` will miss routine execution events
- No visibility into which routines are active

---

### 2.4 Event Trigger & Response Status ❌ **NOT WORKING**

**Status**: ❌ **BROKEN**

**Problem**: Event emission and routing are not tracked.

**Current Flow**:
1. `Event.emit()` → packs data → calls `Runtime.handle_event_emit()`
2. `Runtime.handle_event_emit()` → routes to slots → calls `slot.enqueue()`
3. **No hooks called** ❌

**Missing Integration**:

1. **In `Event.emit()` or `Runtime.handle_event_emit()`**:
   ```python
   from routilux.monitoring.hooks import execution_hooks
   
   # Track event emission
   routine_id = self._get_routine_id(event.routine, job_state)
   if routine_id:
       execution_hooks.on_event_emit(
           event, routine_id, job_state, data=event_data["data"]
       )
   ```

2. **In `Runtime.handle_event_emit()` after `slot.enqueue()`**:
   ```python
   # Track slot data reception
   target_routine_id = self._get_routine_id(slot.routine, job_state)
   if target_routine_id:
       execution_hooks.on_slot_data_received(
           slot, target_routine_id, job_state, data=event_data["data"]
       )
   ```

**Impact**:
- Cannot see when events are emitted
- Cannot see when data arrives at slots
- Cannot track event-to-slot routing
- Breakpoints on events won't trigger

---

### 2.5 Connection-Level Breakpoints ⚠️ **PARTIALLY SUPPORTED**

**Status**: ⚠️ **INFRASTRUCTURE EXISTS BUT NOT FUNCTIONAL**

**Current Breakpoint Types**:
- ✅ `routine` - Pause at routine start
- ⚠️ `slot` - Pause at slot (but slots don't have handlers in new design)
- ⚠️ `event` - Pause at event emit (but hooks not called)

**Missing**: Direct `connection` breakpoint type

**Current Breakpoint Model** (`routilux/api/models/breakpoint.py`):
```python
type: Literal["routine", "slot", "event"]  # No "connection" type
routine_id: Optional[str]
slot_name: Optional[str]  # For slot breakpoints
event_name: Optional[str]  # For event breakpoints
```

**User Requirement**: Set breakpoints on **event-to-slot connections** to:
- Pause when data flows through a specific connection
- Inspect data being transferred
- Modify data before it reaches the slot

**Current Workaround** (Not Ideal):
1. Set breakpoint on source event emit
2. Set breakpoint on target slot enqueue
3. Both must match - but this is cumbersome

**Recommended Solution**: Add `connection` breakpoint type

**Implementation**:

1. **Update Breakpoint Model**:
   ```python
   @dataclass
   class Breakpoint:
       type: Literal["routine", "slot", "event", "connection"]  # Add "connection"
       routine_id: Optional[str] = None
       slot_name: Optional[str] = None
       event_name: Optional[str] = None
       # New fields for connection breakpoints
       source_routine_id: Optional[str] = None
       source_event_name: Optional[str] = None
       target_routine_id: Optional[str] = None
       target_slot_name: Optional[str] = None
   ```

2. **Add Connection Breakpoint Check in Runtime**:
   ```python
   # In Runtime.handle_event_emit(), after finding connections
   for connection in connections:
       # Check connection breakpoint
       if MonitoringRegistry.is_enabled():
           breakpoint_mgr = MonitoringRegistry.get_instance().breakpoint_manager
           if breakpoint_mgr:
               source_routine_id = self._get_routine_id(event.routine, job_state)
               target_routine_id = self._get_routine_id(slot.routine, job_state)
               
               breakpoint = breakpoint_mgr.check_breakpoint(
                   job_state.job_id,
                   source_routine_id,  # Use source routine for connection breakpoint
                   "connection",
                   source_event_name=event.name,
                   target_routine_id=target_routine_id,
                   target_slot_name=slot.name,
                   variables=event_data["data"]
               )
               if breakpoint:
                   # Pause execution
                   debug_store = MonitoringRegistry.get_instance().debug_session_store
                   if debug_store:
                       session = debug_store.get_or_create(job_state.job_id)
                       session.pause(
                           context=None,  # Could create connection context
                           reason=f"Breakpoint at connection {source_routine_id}.{event.name} -> {target_routine_id}.{slot.name}"
                       )
                       return  # Don't enqueue data yet
   ```

3. **Update BreakpointManager**:
   ```python
   def check_breakpoint(
       self,
       job_id: str,
       routine_id: str,
       breakpoint_type: Literal["routine", "slot", "event", "connection"],
       slot_name: Optional[str] = None,
       event_name: Optional[str] = None,
       source_routine_id: Optional[str] = None,  # New
       source_event_name: Optional[str] = None,  # New
       target_routine_id: Optional[str] = None,  # New
       target_slot_name: Optional[str] = None,  # New
       context: Optional["ExecutionContext"] = None,
       variables: Optional[Dict] = None,
   ) -> Optional[Breakpoint]:
       # ... existing code ...
       
       # Add connection breakpoint checking
       if breakpoint_type == "connection":
           if (breakpoint.source_routine_id == source_routine_id and
               breakpoint.source_event_name == source_event_name and
               breakpoint.target_routine_id == target_routine_id and
               breakpoint.target_slot_name == target_slot_name):
               # Match - check condition and return
               ...
   ```

---

## 3. Critical Compatibility Issues

### 3.1 API Execution Model Mismatch 🔴 **CRITICAL**

**File**: `routilux/api/routes/jobs.py:73`

**Current Code**:
```python
started_job_state = flow.start(
    entry_routine_id=request.entry_routine_id,
    entry_params=request.entry_params,
    timeout=request.timeout,
    job_state=job_state,
)
```

**Problem**: 
- `Flow.start()` **does not exist** in new design
- Flow is static - it doesn't execute
- Execution is handled by `Runtime`

**Required Fix**:
```python
from routilux.runtime import Runtime
from routilux.monitoring.flow_registry import FlowRegistry

# Get or create Runtime instance
# Option 1: Singleton Runtime (recommended for API)
runtime = Runtime.get_instance()  # Need to implement singleton

# Option 2: Per-request Runtime (simpler, less efficient)
runtime = Runtime(thread_pool_size=10)

# Ensure flow is registered
flow_registry = FlowRegistry.get_instance()
if not flow_registry.get_by_name(request.flow_id):
    flow_registry.register_by_name(request.flow_id, flow)

# Execute via Runtime
job_state = runtime.exec(request.flow_id, job_state=job_state)
```

**Impact**: 
- ❌ Job start endpoint (`POST /api/jobs`) **will fail**
- ❌ Cannot start jobs via API
- ❌ All job management features broken

---

### 3.2 Monitoring Hooks Not Called 🔴 **CRITICAL**

**Problem**: Runtime execution path doesn't call monitoring hooks.

**Missing Hook Calls**:

1. **`on_routine_start()`** - Not called in `Runtime._activate_routine()`
2. **`on_routine_end()`** - Not called in `Runtime._activate_routine()`
3. **`on_event_emit()`** - Not called in `Event.emit()` or `Runtime.handle_event_emit()`
4. **`on_slot_data_received()`** - Doesn't exist (old `on_slot_call()` expects handlers)

**Required Integration**:

**File**: `routilux/runtime.py`

```python
def _activate_routine(self, routine, job_state, data_slice=None, policy_message=None):
    """Activate routine logic."""
    routine_id = self._get_routine_id(routine, job_state)
    if routine_id is None:
        return
    
    job_state.current_routine_id = routine_id
    
    # CRITICAL: Call monitoring hook
    from routilux.monitoring.hooks import execution_hooks
    execution_hooks.on_routine_start(routine, routine_id, job_state)
    
    try:
        # Prepare and execute logic
        ...
        routine._logic(*slot_data_lists, policy_message=policy_message, job_state=job_state)
        job_state.update_routine_state(routine_id, {"status": "completed"})
        
        # CRITICAL: Call monitoring hook
        execution_hooks.on_routine_end(routine, routine_id, job_state, status="completed")
    except Exception as e:
        # Error handling
        ...
        # CRITICAL: Call monitoring hook
        execution_hooks.on_routine_end(routine, routine_id, job_state, status="failed", error=e)
```

**File**: `routilux/runtime.py` - `handle_event_emit()`

```python
def handle_event_emit(self, event, event_data, job_state):
    """Handle event emission and route to connected slots."""
    # CRITICAL: Track event emission
    from routilux.monitoring.hooks import execution_hooks
    
    source_routine_id = self._get_routine_id(event.routine, job_state)
    if source_routine_id:
        execution_hooks.on_event_emit(
            event, source_routine_id, job_state, data=event_data["data"]
        )
    
    # Find connections and route
    for connection in connections:
        slot = connection.target_slot
        slot.enqueue(...)
        
        # CRITICAL: Track slot data reception
        target_routine_id = self._get_routine_id(slot.routine, job_state)
        if target_routine_id:
            # New hook for slot data reception (replaces on_slot_call)
            execution_hooks.on_slot_data_received(
                slot, target_routine_id, job_state, data=event_data["data"]
            )
        
        # Check routine activation
        self._check_routine_activation(routine, job_state)
```

**Impact**:
- ❌ No execution metrics collected
- ❌ No execution trace
- ❌ Breakpoints won't trigger
- ❌ Debug sessions won't work

---

### 3.3 Slot Hook Compatibility Issue ⚠️ **MEDIUM**

**Problem**: `on_slot_call()` hook expects slot handlers, but new design uses queues.

**Current Hook** (`routilux/monitoring/hooks.py:183`):
```python
def on_slot_call(
    self,
    slot: "Slot",
    routine_id: str,
    job_state: Optional["JobState"] = None,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    """Hook called when slot handler is called."""
```

**New Design**: 
- Slots are queues (`Slot.enqueue()`)
- No handlers - data is consumed by activation policies
- Logic executes separately

**Required Changes**:

1. **Rename/Add Hook**:
   ```python
   def on_slot_data_received(
       self,
       slot: "Slot",
       routine_id: str,
       job_state: Optional["JobState"] = None,
       data: Optional[Any] = None,  # Can be any type, not just Dict
   ) -> bool:
       """Hook called when data is enqueued to a slot.
       
       Returns:
           True if execution should continue, False if should pause.
       """
   ```

2. **Call in `Slot.enqueue()` or `Runtime.handle_event_emit()`**:
   ```python
   # In Runtime.handle_event_emit(), after slot.enqueue()
   execution_hooks.on_slot_data_received(slot, target_routine_id, job_state, data=data)
   ```

---

### 3.4 JobState Tracking Incomplete ⚠️ **MEDIUM**

**Problem**: Runtime doesn't properly populate JobState execution history.

**Current State**:
- `Runtime._activate_routine()` calls `job_state.update_routine_state()` but doesn't call `job_state.record_execution()`
- Execution history is minimal

**Required Fix**:
```python
# In Runtime._activate_routine()
job_state.record_execution(routine_id, "start", {
    "slot_data_counts": {name: len(data) for name, data in data_slice.items()},
    "policy_message": policy_message,
})

# After logic execution
job_state.record_execution(routine_id, "completed", {
    "duration": ...,
})

# On error
job_state.record_execution(routine_id, "error", {
    "error": str(e),
    "error_type": type(e).__name__,
})
```

---

## 4. DSL Compatibility ✅ **FULLY COMPATIBLE**

**Status**: ✅ **WORKS**

**Implementation**: `routilux/dsl/loader.py`

**Analysis**:
- DSL loader creates Flow objects (static) - ✅ Compatible
- DSL export works - ✅ Compatible
- No runtime dependencies - ✅ Compatible

**Conclusion**: No changes needed.

---

## 5. Recommended Implementation Plan

### Phase 1: Critical Fixes (Required for Basic Functionality)

#### 5.1 Fix API Job Execution
**Priority**: 🔴 **CRITICAL**

**Files to Modify**:
- `routilux/api/routes/jobs.py`

**Changes**:
1. Replace `flow.start()` with `Runtime.exec()`
2. Ensure flow is registered in FlowRegistry
3. Handle Runtime instance (singleton or per-request)

**Estimated Effort**: 2-3 hours

---

#### 5.2 Integrate Monitoring Hooks in Runtime
**Priority**: 🔴 **CRITICAL**

**Files to Modify**:
- `routilux/runtime.py`

**Changes**:
1. Call `execution_hooks.on_routine_start()` in `_activate_routine()`
2. Call `execution_hooks.on_routine_end()` in `_activate_routine()` (finally block)
3. Call `execution_hooks.on_event_emit()` in `handle_event_emit()`
4. Add `on_slot_data_received()` hook call after `slot.enqueue()`

**Estimated Effort**: 3-4 hours

---

#### 5.3 Update Slot Hook for New Design
**Priority**: ⚠️ **HIGH**

**Files to Modify**:
- `routilux/monitoring/hooks.py`

**Changes**:
1. Add `on_slot_data_received()` method
2. Keep `on_slot_call()` for backward compatibility (deprecated)
3. Update hook to work with queue-based slots

**Estimated Effort**: 1-2 hours

---

### Phase 2: Enhanced Features (Required for Full Functionality)

#### 5.4 Add Connection Breakpoint Support
**Priority**: ⚠️ **HIGH**

**Files to Modify**:
- `routilux/monitoring/breakpoint_manager.py`
- `routilux/api/models/breakpoint.py`
- `routilux/runtime.py`

**Changes**:
1. Add `"connection"` to breakpoint type
2. Add connection-specific fields to Breakpoint dataclass
3. Implement `check_connection_breakpoint()` in Runtime
4. Update API models

**Estimated Effort**: 4-5 hours

---

#### 5.5 Enhance JobState Tracking
**Priority**: ⚠️ **MEDIUM**

**Files to Modify**:
- `routilux/runtime.py`

**Changes**:
1. Call `job_state.record_execution()` for all routine events
2. Track activation policy checks
3. Track event routing
4. Track slot data reception

**Estimated Effort**: 2-3 hours

---

### Phase 3: Optional Improvements

#### 5.6 Runtime Singleton Pattern
**Priority**: ⚠️ **LOW**

**Recommendation**: Implement singleton Runtime for API to:
- Share thread pool across requests
- Centralize job management
- Better resource utilization

**Estimated Effort**: 1-2 hours

---

## 6. Best Practice Recommendations

### 6.1 Execution Model
✅ **Current Design is Correct**:
- Flow is static (template)
- Runtime manages execution
- JobState tracks runtime state

**Recommendation**: Keep this separation. API should use Runtime, not Flow.execute().

---

### 6.2 Monitoring Integration
✅ **Hook Pattern is Good**:
- Zero overhead when disabled
- Clean separation of concerns
- Easy to extend

**Recommendation**: 
- Integrate hooks in Runtime execution path
- Add hooks for all key events (routine start/end, event emit, slot receive)
- Ensure hooks are called synchronously (don't block execution)

---

### 6.3 Breakpoint Design
⚠️ **Current Design Needs Enhancement**:

**Current**: Breakpoints on routine/slot/event
**Needed**: Breakpoints on connections (event → slot)

**Recommendation**:
- Add `connection` breakpoint type
- Support breakpoints at connection level (most intuitive for users)
- Allow conditional breakpoints (e.g., `data.value > 10`)

---

### 6.4 API Design
✅ **RESTful Design is Good**:
- Clear resource hierarchy
- Proper HTTP methods
- Good error handling

**Recommendation**:
- Add WebSocket support for real-time updates (already exists but needs integration)
- Add pagination for large result sets (already implemented)
- Consider GraphQL for complex queries (optional)

---

## 7. Compatibility Matrix

| Feature | Current Status | After Phase 1 | After Phase 2 | Notes |
|---------|---------------|---------------|---------------|-------|
| View Flow Structure | ✅ Works | ✅ Works | ✅ Works | No changes needed |
| View Job Status | ⚠️ Partial | ✅ Works | ✅ Works | Needs Runtime integration |
| View Routine Activation | ❌ Broken | ✅ Works | ✅ Works | Needs hooks |
| View Event Trigger | ❌ Broken | ✅ Works | ✅ Works | Needs hooks |
| View Slot Response | ❌ Broken | ✅ Works | ✅ Works | Needs hooks |
| Routine Breakpoints | ⚠️ Infrastructure | ✅ Works | ✅ Works | Needs hooks |
| Event Breakpoints | ⚠️ Infrastructure | ✅ Works | ✅ Works | Needs hooks |
| Connection Breakpoints | ❌ Missing | ❌ Missing | ✅ Works | Needs implementation |
| Debug Session | ⚠️ Infrastructure | ✅ Works | ✅ Works | Needs hooks |
| Execution Metrics | ❌ Empty | ✅ Works | ✅ Works | Needs hooks |
| Execution Trace | ❌ Empty | ✅ Works | ✅ Works | Needs hooks |

---

## 8. Conclusion

### Current State
The API and monitoring system have **good infrastructure** but **critical integration gaps** with the new Runtime-based design. The core concepts (Flow structure, job tracking, breakpoints) are sound, but execution tracking is broken.

### Required Actions
1. **Immediate** (Phase 1): Fix API execution and hook integration
2. **Short-term** (Phase 2): Add connection breakpoints and enhance tracking
3. **Long-term** (Phase 3): Optimize and enhance

### Estimated Total Effort
- **Phase 1**: 6-9 hours
- **Phase 2**: 6-8 hours
- **Phase 3**: 1-2 hours
- **Total**: 13-19 hours

### Risk Assessment
- **Low Risk**: Flow structure viewing, DSL
- **Medium Risk**: Job state tracking (needs careful integration)
- **High Risk**: Breakpoint integration (complex, affects execution flow)

---

## 9. Implementation Priority

### Must Have (Blocking)
1. ✅ Fix API job execution (`flow.start()` → `Runtime.exec()`)
2. ✅ Integrate monitoring hooks in Runtime
3. ✅ Update slot hook for queue-based design

### Should Have (Important)
4. ⚠️ Add connection breakpoint support
5. ⚠️ Enhance JobState tracking
6. ⚠️ Add event/slot tracking hooks

### Nice to Have (Optional)
7. ⚠️ Runtime singleton pattern
8. ⚠️ Enhanced WebSocket integration
9. ⚠️ Performance optimizations

---

## 10. Next Steps

1. **Review this report** with team
2. **Prioritize fixes** based on user needs
3. **Implement Phase 1** fixes (critical)
4. **Test thoroughly** with real workflows
5. **Implement Phase 2** enhancements
6. **Update documentation** for new API usage

---

**Report Generated**: 2026-01-16  
**Analysis Based On**: Codebase as of latest commit  
**Recommendations**: Based on best practices and user requirements
