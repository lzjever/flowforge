# Routilux API & Monitoring System Analysis Report

**Date**: 2026-01-16  
**Scope**: Analysis of API, DSL, and Monitoring code compatibility with new Runtime-based design  
**Goal**: Evaluate if current implementation can satisfy monitoring and debugging requirements

---

## Executive Summary

The current API and monitoring system have **significant compatibility issues** with the new Runtime-based design. While the monitoring infrastructure (hooks, breakpoints, event collection) is well-designed, it is **not integrated** with the new `Runtime` execution model. The API still uses the old `Flow.start()` method instead of `Runtime.exec()`, and monitoring hooks are not called during Runtime execution.

**Key Findings**:
- ❌ **API uses outdated execution model** (`flow.start()` instead of `Runtime.exec()`)
- ❌ **Monitoring hooks not integrated with Runtime** (hooks exist but are never called)
- ⚠️ **Connection-level breakpoints not directly supported** (can be achieved via event/slot breakpoints)
- ✅ **Monitoring infrastructure is well-designed** (just needs integration)
- ✅ **Flow structure viewing works** (uses FlowRegistry)
- ⚠️ **Job state tracking partially works** (depends on Runtime integration)

---

## 1. Current Architecture Analysis

### 1.1 New Design: Runtime-Based Execution

**Key Components**:
- `Runtime`: Centralized execution manager with thread pool
- `Runtime.exec()`: Non-blocking flow execution method
- `Runtime.handle_event_emit()`: Routes events to slots
- `Runtime._check_routine_activation()`: Checks activation policies
- `Runtime._activate_routine()`: Executes routine logic

**Execution Flow**:
```
Runtime.exec(flow_name)
  → _execute_flow()
    → Find entry routine
    → Trigger entry routine (enqueue data to trigger slot)
    → _check_routine_activation()
      → Call activation_policy
      → _activate_routine()
        → Execute logic
        → Logic emits events
          → Runtime.handle_event_emit()
            → Route to connected slots
            → _check_routine_activation() for target routines
```

### 1.2 Current API Implementation

**Location**: `routilux/api/routes/jobs.py`

**Problem**: Uses `flow.start()` instead of `Runtime.exec()`

```python
# Current implementation (WRONG for new design)
started_job_state = flow.start(
    entry_routine_id=request.entry_routine_id,
    entry_params=request.entry_params,
    timeout=request.timeout,
    job_state=job_state,
)
```

**Issues**:
1. `Flow.start()` doesn't exist in the new design (Flow is static)
2. Should use `Runtime.exec(flow_name)` instead
3. Job execution bypasses Runtime, so monitoring hooks won't be called
4. Job state won't be tracked in Runtime's `_active_jobs` registry

### 1.3 Monitoring Hooks System

**Location**: `routilux/monitoring/hooks.py`

**Design**: Well-structured hook system with:
- `on_flow_start()` / `on_flow_end()`
- `on_routine_start()` / `on_routine_end()`
- `on_slot_call()` - Called when slot handler executes
- `on_event_emit()` - Called when event is emitted
- `should_pause_routine()` - Breakpoint checking

**Problem**: **Hooks are never called by Runtime**

The Runtime execution path does not call any monitoring hooks:
- `Runtime._execute_flow()` - No hook calls
- `Runtime.handle_event_emit()` - No hook calls
- `Runtime._activate_routine()` - No hook calls
- `Event.emit()` - No hook calls
- `Slot.enqueue()` - No hook calls

**Impact**: 
- No execution events collected
- No metrics tracked
- Breakpoints won't trigger
- Debug sessions won't work
- WebSocket events won't be published

---

## 2. Requirements Analysis

### 2.1 User Requirements

1. ✅ **View flow structure** - Can be satisfied
2. ⚠️ **View job execution state** - Partially works (needs Runtime integration)
3. ⚠️ **View routine activation and work status** - Needs hook integration
4. ⚠️ **View event trigger and response status** - Needs hook integration
5. ⚠️ **Set breakpoints on event-to-slot connections** - Needs connection breakpoint type

### 2.2 Current Capabilities

#### ✅ Flow Structure Viewing

**Status**: **WORKS**

- `GET /api/flows` - Lists all flows
- `GET /api/flows/{flow_id}` - Shows flow structure
- `GET /api/flows/{flow_id}/routines` - Lists routines
- `GET /api/flows/{flow_id}/connections` - Lists connections

**Implementation**: Uses `FlowRegistry` and `flow_store`, which work with the new design.

#### ⚠️ Job Execution State

**Status**: **PARTIALLY WORKS**

- `GET /api/jobs` - Lists jobs
- `GET /api/jobs/{job_id}` - Shows job details
- `GET /api/jobs/{job_id}/state` - Shows full job state

**Issues**:
- API uses `flow.start()` which doesn't exist in new design
- Jobs started via API won't be tracked by Runtime
- Job state updates won't be synchronized

**Fix Required**: Use `Runtime.exec()` instead of `flow.start()`

#### ❌ Routine Activation and Work Status

**Status**: **DOES NOT WORK**

- `GET /api/jobs/{job_id}/metrics` - Returns empty/no data
- `GET /api/jobs/{job_id}/trace` - Returns empty/no events

**Root Cause**: Monitoring hooks are not called during Runtime execution.

**Required Hooks**:
- `on_routine_start()` - When `_activate_routine()` is called
- `on_routine_end()` - When logic execution completes
- `on_slot_call()` - When slot receives data (but slots don't have handlers anymore)

**Note**: In the new design, slots don't have handlers - they're just queues. The activation happens via `activation_policy` → `logic`. So we need hooks at:
- Activation policy evaluation
- Logic execution start/end
- Slot data enqueue (for tracking data flow)

#### ❌ Event Trigger and Response Status

**Status**: **DOES NOT WORK**

**Root Cause**: `Event.emit()` and `Runtime.handle_event_emit()` don't call hooks.

**Required Integration**:
- Call `execution_hooks.on_event_emit()` in `Event.emit()` or `Runtime.handle_event_emit()`
- Track event routing to slots
- Track slot data reception

#### ⚠️ Connection-Level Breakpoints

**Status**: **PARTIALLY SUPPORTED**

**Current Breakpoint Types**:
- `routine` - Pause at routine start
- `slot` - Pause at slot call (but slots don't have handlers in new design)
- `event` - Pause at event emit

**Missing**: Direct `connection` breakpoint type

**Workaround**: Can set breakpoints on:
- Source event emit (pause before routing)
- Target slot enqueue (pause after routing, before activation)

**Better Solution**: Add `connection` breakpoint type that triggers when:
- Event is emitted AND
- Data is routed to the specific slot via the connection

---

## 3. Detailed Issue Analysis

### 3.1 Critical Issue: API Execution Model Mismatch

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
- `Flow.start()` doesn't exist in new design
- Flow is static, doesn't execute
- Should use `Runtime.exec()`

**Required Fix**:
```python
from routilux.runtime import Runtime
from routilux.monitoring.flow_registry import FlowRegistry

# Get or create Runtime instance (singleton pattern recommended)
runtime = Runtime.get_instance()  # Or create per-request

# Register flow if not already registered
flow_registry = FlowRegistry.get_instance()
if not flow_registry.get_by_name(request.flow_id):
    flow_registry.register_by_name(request.flow_id, flow)

# Execute via Runtime
job_state = runtime.exec(request.flow_id, job_state=job_state)
```

### 3.2 Critical Issue: Monitoring Hooks Not Called

**Problem**: Runtime execution path doesn't call monitoring hooks.

**Required Integration Points**:

1. **Flow Start/End**:
   - `Runtime._execute_flow()` should call `execution_hooks.on_flow_start()` at start
   - Should call `execution_hooks.on_flow_end()` at completion/failure

2. **Routine Activation**:
   - `Runtime._activate_routine()` should call `execution_hooks.on_routine_start()` before logic
   - Should call `execution_hooks.on_routine_end()` after logic (success or error)

3. **Event Emission**:
   - `Event.emit()` or `Runtime.handle_event_emit()` should call `execution_hooks.on_event_emit()`
   - Should check breakpoints and pause if needed

4. **Slot Data Reception**:
   - `Slot.enqueue()` should call a hook (or Runtime should call it)
   - Track data flow from events to slots

**Implementation Pattern**:
```python
# In Runtime._execute_flow()
from routilux.monitoring.hooks import execution_hooks

execution_hooks.on_flow_start(flow, job_state)
try:
    # ... execution logic ...
finally:
    execution_hooks.on_flow_end(flow, job_state, status)

# In Runtime._activate_routine()
execution_hooks.on_routine_start(routine, routine_id, job_state)
try:
    routine._logic(...)
    execution_hooks.on_routine_end(routine, routine_id, job_state, "completed")
except Exception as e:
    execution_hooks.on_routine_end(routine, routine_id, job_state, "failed", e)
    raise

# In Runtime.handle_event_emit() or Event.emit()
if not execution_hooks.on_event_emit(event, routine_id, job_state, event_data["data"]):
    # Hook returned False, execution paused
    return
```

### 3.3 Missing Feature: Connection-Level Breakpoints

**Current State**: Breakpoints can be set on:
- Routine start
- Slot call (but slots don't have handlers in new design)
- Event emit

**User Requirement**: Set breakpoints on event-to-slot connections.

**Analysis**:
- Connection breakpoints should trigger when:
  1. Event is emitted from source routine
  2. AND data is routed to target slot via the specific connection
  3. AND before activation policy is checked

**Implementation Options**:

**Option A: Add Connection Breakpoint Type**
```python
@dataclass
class Breakpoint:
    type: Literal["routine", "slot", "event", "connection"]  # Add "connection"
    source_routine_id: Optional[str] = None
    source_event_name: Optional[str] = None
    target_routine_id: Optional[str] = None
    target_slot_name: Optional[str] = None
```

**Option B: Use Event + Slot Breakpoints**
- Set breakpoint on source event emit
- Set breakpoint on target slot enqueue
- Both must match the connection

**Recommendation**: **Option A** - More intuitive and explicit.

**Integration Point**: In `Runtime.handle_event_emit()`, after finding connections:
```python
for connection in connections:
    # Check connection breakpoint
    breakpoint = breakpoint_mgr.check_connection_breakpoint(
        job_state.job_id,
        connection,
        event_data
    )
    if breakpoint:
        # Pause execution
        return
```

### 3.4 Slot Hook Compatibility Issue

**Problem**: `on_slot_call()` hook expects slot handlers, but new design doesn't use handlers.

**Current Hook Signature**:
```python
def on_slot_call(
    self,
    slot: "Slot",
    routine_id: str,
    job_state: Optional["JobState"] = None,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
```

**New Design**: Slots are queues, not handlers. Data flows:
1. Event emits → Runtime routes → Slot.enqueue()
2. Activation policy checks slot data
3. Logic executes with consumed data

**Required Changes**:
- Rename/repurpose `on_slot_call()` to `on_slot_data_received()` or `on_slot_enqueue()`
- Call it in `Slot.enqueue()` or `Runtime.handle_event_emit()` after enqueueing
- Track data reception, not handler calls

---

## 4. Compatibility Assessment

### 4.1 Flow Structure Viewing ✅

**Status**: **FULLY COMPATIBLE**

- Uses `FlowRegistry` which works with new design
- Flow structure is static (routines, connections, config)
- No execution state needed

**No changes required**.

### 4.2 Job Execution via API ❌

**Status**: **INCOMPATIBLE**

**Issues**:
- Uses `flow.start()` which doesn't exist
- Should use `Runtime.exec()`

**Required Changes**:
1. Update `jobs.py` to use `Runtime.exec()`
2. Ensure Runtime instance is available (singleton or per-request)
3. Register flows with FlowRegistry before execution

### 4.3 Job State Tracking ⚠️

**Status**: **PARTIALLY COMPATIBLE**

**Current**: Uses `job_store` (in-memory storage)

**New Design**: Runtime maintains `_active_jobs` registry

**Integration Options**:
1. **Option A**: Runtime updates `job_store` when jobs are created/completed
2. **Option B**: API queries Runtime's `_active_jobs` instead of `job_store`
3. **Option C**: Both (Runtime as source of truth, job_store as cache)

**Recommendation**: **Option C** - Runtime updates job_store for API compatibility.

### 4.4 Execution Metrics and Tracing ❌

**Status**: **INCOMPATIBLE**

**Root Cause**: Hooks not called, so no events collected.

**Required Changes**:
- Integrate hooks into Runtime execution path
- Ensure all execution events are captured

### 4.5 Breakpoints ❌

**Status**: **INCOMPATIBLE**

**Root Cause**: Hooks not called, so breakpoints never trigger.

**Required Changes**:
- Integrate hooks into Runtime
- Add connection breakpoint type
- Update breakpoint checking logic for new execution model

### 4.6 Debug Sessions ❌

**Status**: **INCOMPATIBLE**

**Root Cause**: Debug sessions depend on breakpoints triggering, which requires hooks.

**Required Changes**:
- Integrate hooks
- Ensure pause/resume works with Runtime execution

---

## 5. Recommended Solutions

### 5.1 Immediate Fixes (Critical)

#### Fix 1: Update API to Use Runtime

**File**: `routilux/api/routes/jobs.py`

**Change**:
```python
from routilux.runtime import Runtime
from routilux.monitoring.flow_registry import FlowRegistry

# In start_job()
runtime = Runtime.get_instance()  # Or create singleton
flow_registry = FlowRegistry.get_instance()

# Ensure flow is registered
if not flow_registry.get_by_name(request.flow_id):
    flow_registry.register_by_name(request.flow_id, flow)

# Execute via Runtime
job_state = runtime.exec(request.flow_id, job_state=job_state)
job_store.add(job_state)  # Update store for API compatibility
```

#### Fix 2: Integrate Monitoring Hooks into Runtime

**Files**: 
- `routilux/runtime.py`
- `routilux/event.py`
- `routilux/slot.py`

**Changes**:

1. **In Runtime._execute_flow()**:
```python
from routilux.monitoring.hooks import execution_hooks

def _execute_flow(self, flow: Flow, job_state: JobState) -> None:
    execution_hooks.on_flow_start(flow, job_state)
    try:
        # ... existing execution logic ...
        status = "completed" if job_state.status == ExecutionStatus.COMPLETED else "failed"
    except Exception as e:
        status = "failed"
        raise
    finally:
        execution_hooks.on_flow_end(flow, job_state, status)
```

2. **In Runtime._activate_routine()**:
```python
def _activate_routine(self, routine, job_state, data_slice, policy_message):
    routine_id = self._get_routine_id(routine, job_state)
    if routine_id is None:
        return
    
    execution_hooks.on_routine_start(routine, routine_id, job_state)
    try:
        routine._logic(...)
        execution_hooks.on_routine_end(routine, routine_id, job_state, "completed")
    except Exception as e:
        execution_hooks.on_routine_end(routine, routine_id, job_state, "failed", e)
        raise
```

3. **In Runtime.handle_event_emit()**:
```python
def handle_event_emit(self, event, event_data, job_state):
    # Get routine_id for event
    routine_id = self._get_routine_id(event.routine, job_state) if event.routine else "unknown"
    
    # Call hook (checks breakpoints)
    if not execution_hooks.on_event_emit(event, routine_id, job_state, event_data["data"]):
        # Hook returned False, execution paused
        return
    
    # Route to slots
    for connection in connections:
        slot = connection.target_slot
        # ... enqueue logic ...
        
        # Track slot data reception
        target_routine_id = self._get_routine_id(slot.routine, job_state) if slot.routine else None
        if target_routine_id:
            # Call hook for slot data reception
            execution_hooks.on_slot_data_received(slot, target_routine_id, job_state, data)
```

4. **Add new hook method** (in `hooks.py`):
```python
def on_slot_data_received(
    self,
    slot: "Slot",
    routine_id: str,
    job_state: Optional["JobState"] = None,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    """Hook called when slot receives data (enqueued).
    
    This replaces on_slot_call() for the new queue-based design.
    """
    # Similar implementation to on_slot_call() but for data reception
    # Check breakpoints, record metrics, etc.
```

#### Fix 3: Add Connection Breakpoint Type

**File**: `routilux/monitoring/breakpoint_manager.py`

**Changes**:
1. Update `Breakpoint` dataclass to support `type="connection"`
2. Add `check_connection_breakpoint()` method
3. Integrate into `Runtime.handle_event_emit()`

### 5.2 Architecture Improvements (Recommended)

#### Improvement 1: Runtime Singleton Pattern

**Current**: Runtime instances are created per-request or manually.

**Recommendation**: Use singleton pattern for Runtime in API context.

```python
# In routilux/runtime.py
class Runtime:
    _api_instance: Optional["Runtime"] = None
    _api_lock = threading.Lock()
    
    @classmethod
    def get_api_instance(cls) -> "Runtime":
        """Get singleton Runtime instance for API use."""
        if cls._api_instance is None:
            with cls._api_lock:
                if cls._api_instance is None:
                    cls._api_instance = Runtime(thread_pool_size=10)
        return cls._api_instance
```

#### Improvement 2: Job Store Synchronization

**Recommendation**: Runtime should update job_store when jobs are created/updated.

```python
# In Runtime.exec()
job_store.add(job_state)  # Sync to API store

# In Runtime._execute_flow() finally block
job_store.add(job_state)  # Update on completion
```

#### Improvement 3: Connection Breakpoint API

**Add endpoint**: `POST /api/jobs/{job_id}/breakpoints` with connection type

**Request Model**:
```python
class BreakpointCreateRequest:
    type: Literal["routine", "slot", "event", "connection"]
    # For connection type:
    source_routine_id: Optional[str] = None
    source_event_name: Optional[str] = None
    target_routine_id: Optional[str] = None
    target_slot_name: Optional[str] = None
    condition: Optional[str] = None
```

---

## 6. Implementation Priority

### Phase 1: Critical Fixes (Required for Basic Functionality)

1. ✅ Update API to use `Runtime.exec()` instead of `flow.start()`
2. ✅ Integrate monitoring hooks into Runtime execution path
3. ✅ Add `on_slot_data_received()` hook for new design
4. ✅ Ensure job_store is synchronized with Runtime

### Phase 2: Enhanced Features (Required for Full Functionality)

5. ✅ Add connection breakpoint type
6. ✅ Update breakpoint checking for new execution model
7. ✅ Ensure debug sessions work with Runtime
8. ✅ Test WebSocket event streaming

### Phase 3: Polish and Optimization

9. ✅ Runtime singleton for API
10. ✅ Performance optimization for hook calls
11. ✅ Comprehensive testing

---

## 7. Testing Requirements

After implementing fixes, test:

1. **Flow Structure Viewing**:
   - ✅ List flows
   - ✅ Get flow details
   - ✅ List routines and connections

2. **Job Execution**:
   - ✅ Start job via API
   - ✅ Job appears in Runtime's active jobs
   - ✅ Job state is tracked

3. **Execution Monitoring**:
   - ✅ Metrics are collected
   - ✅ Execution trace shows events
   - ✅ Routine metrics are accurate

4. **Breakpoints**:
   - ✅ Routine breakpoints trigger
   - ✅ Event breakpoints trigger
   - ✅ Connection breakpoints trigger
   - ✅ Breakpoint conditions work

5. **Debug Sessions**:
   - ✅ Pause/resume works
   - ✅ Step over/into works
   - ✅ Variable inspection works

---

## 8. Conclusion

The current API and monitoring system have a **solid foundation** but are **not compatible** with the new Runtime-based design. The main issues are:

1. **API uses outdated execution model** - Needs to use `Runtime.exec()`
2. **Monitoring hooks not integrated** - Runtime doesn't call hooks
3. **Connection breakpoints missing** - Need to add this feature

**Estimated Effort**:
- Phase 1 (Critical): 2-3 days
- Phase 2 (Enhanced): 2-3 days
- Phase 3 (Polish): 1-2 days

**Total**: ~1 week of focused development

**Recommendation**: Implement Phase 1 fixes immediately to restore basic functionality, then proceed with Phase 2 for full feature support.

---

## Appendix: Code Locations

### Files Requiring Changes

1. **API Routes**:
   - `routilux/api/routes/jobs.py` - Update to use Runtime
   - `routilux/api/routes/breakpoints.py` - Add connection breakpoint support

2. **Runtime Integration**:
   - `routilux/runtime.py` - Add hook calls
   - `routilux/event.py` - Add hook calls (optional, can be in Runtime)
   - `routilux/slot.py` - Add hook calls (optional, can be in Runtime)

3. **Monitoring**:
   - `routilux/monitoring/hooks.py` - Add `on_slot_data_received()`
   - `routilux/monitoring/breakpoint_manager.py` - Add connection breakpoint support

4. **Storage**:
   - `routilux/monitoring/storage.py` - Ensure synchronization with Runtime

### Files That Work Correctly

- `routilux/api/routes/flows.py` - Flow structure viewing ✅
- `routilux/monitoring/flow_registry.py` - Flow registry ✅
- `routilux/monitoring/monitor_collector.py` - Event collection ✅
- `routilux/monitoring/debug_session.py` - Debug session management ✅
