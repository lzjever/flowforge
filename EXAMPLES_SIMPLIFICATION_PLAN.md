# Examples Simplification Plan

**Date**: 2025-01-XX  
**Objective**: Simplify `examples/overseer_demo_app.py` with practical, simple routines and flows  
**Status**: Planning Phase

---

## Current State Analysis

### Current File Structure
- **12 complex routines**: DataSource, DataValidator, DataTransformer, QueuePressureGenerator, DebugTargetRoutine, StateTransitionDemo, DataSink, RateLimitedProcessor, DataAggregator, ErrorGenerator, MultiSlotProcessor, LoopController
- **10 complex flows**: Multiple flows demonstrating various patterns
- **~1,294 lines of code**: Complex logic with state management, error handling, etc.

### Issues with Current Implementation
1. **Too complex**: Routines have complex state management, multiple outputs, error handling
2. **Hard to understand**: Input/output formats not clearly documented
3. **Over-engineered**: Many routines serve similar purposes with slight variations
4. **Not practical**: Focus on demonstrating features rather than real-world use cases

---

## Requirements Analysis

### User Requirements

#### 1. Countdown Timer Routine
**Purpose**: Test routed stdout and display progress in client

**Input Format**:
```python
{
    "delay_ms": 5000  # Total delay in milliseconds
}
```

**Behavior**:
- Receives delay in milliseconds
- Loops: sleep 1 second, print remaining time, emit event
- Continues until delay is exhausted
- Each second emits an event with remaining time

**Output Format** (Events):
```python
{
    "remaining_ms": 4000,  # Remaining milliseconds
    "elapsed_ms": 1000,    # Elapsed milliseconds
    "progress": 0.2        # Progress ratio (0.0 to 1.0)
}
```

**Print Output**:
```
Countdown: 5000ms remaining
Countdown: 4000ms remaining
Countdown: 3000ms remaining
...
```

**Use Case**: Test routed stdout capture, show progress in UI

---

#### 2. Batch Processor Routine
**Purpose**: Generic test routine with configurable batch size

**Input Format**:
```python
{
    "data": "any_data",  # Data to process
    "index": 1           # Optional index
}
```

**Configuration**:
```python
{
    "batch_size": 3  # Process every N messages (via batch_size_policy)
}
```

**Behavior**:
- Uses `batch_size_policy(N)` to collect N messages
- When batch is ready, prints the entire batch
- Emits the batch as output event

**Output Format** (Event):
```python
{
    "batch": [
        {"data": "data1", "index": 1},
        {"data": "data2", "index": 2},
        {"data": "data3", "index": 3}
    ],
    "batch_size": 3,
    "processed_at": "2025-01-20T10:00:00"
}
```

**Print Output**:
```
Processing batch of 3 items:
  - Item 1: data1
  - Item 2: data2
  - Item 3: data3
```

**Use Case**: Test batch processing, demonstrate batch_size_policy

---

#### 3. Simple Printer Routine
**Purpose**: Receive input and print it (sink for testing)

**Input Format**:
```python
{
    "data": "any_data",  # Any data to print
    "index": 1          # Optional index
}
```

**Behavior**:
- Receives input
- Prints the data
- No output event (sink routine)

**Print Output**:
```
Received: any_data (index: 1)
```

**Use Case**: Simple sink for testing, verify data flow

---

#### 4. Delay Routine
**Purpose**: Delay data transmission by configured milliseconds

**Input Format**:
```python
{
    "data": "any_data"  # Data to delay
}
```

**Configuration**:
```python
{
    "delay_ms": 2000  # Delay in milliseconds before emitting
}
```

**Behavior**:
- Receives input data
- Sleeps for configured milliseconds
- Emits the same data after delay

**Output Format** (Event):
```python
{
    "data": "any_data",  # Original data
    "delayed_by_ms": 2000,
    "emitted_at": "2025-01-20T10:00:00"
}
```

**Print Output**:
```
Delaying data for 2000ms...
Data emitted after delay
```

**Use Case**: Test timing, simulate slow processing

---

### Additional Routines to Design

#### 5. Echo Routine
**Purpose**: Simple echo - receives input and emits it unchanged

**Input Format**:
```python
{
    "data": "any_data"  # Data to echo
}
```

**Output Format** (Event):
```python
{
    "data": "any_data"  # Same as input
}
```

**Print Output**:
```
Echo: any_data
```

**Use Case**: Simple pass-through, test event routing

---

#### 6. Counter Routine
**Purpose**: Counts received messages and emits count

**Input Format**:
```python
{
    "data": "any_data"  # Any data (ignored)
}
```

**Behavior**:
- Maintains internal counter
- Increments on each message
- Emits current count

**Output Format** (Event):
```python
{
    "count": 5,  # Current count
    "message": "Received 5 messages"
}
```

**Print Output**:
```
Counter: 5 messages received
```

**Use Case**: Test state persistence, count messages

---

#### 7. Filter Routine
**Purpose**: Filters data based on simple condition

**Input Format**:
```python
{
    "value": 42,        # Value to filter
    "threshold": 50     # Optional threshold (from config)
}
```

**Configuration**:
```python
{
    "threshold": 50  # Only emit if value >= threshold
}
```

**Behavior**:
- Receives value
- Compares with threshold
- Emits only if value >= threshold

**Output Format** (Event):
```python
{
    "value": 42,
    "passed": True  # Whether value passed filter
}
```

**Print Output**:
```
Filter: value=42, threshold=50, passed=False
```

**Use Case**: Test conditional logic, data filtering

---

## Flow Templates Design

### Flow 1: Simple Pipeline Flow
**Purpose**: Basic linear flow for testing

**Structure**:
```
Echo -> Delay -> Printer
```

**Routines**:
- `echo`: Echo routine (immediate policy)
- `delay`: Delay routine (immediate policy, delay_ms=1000)
- `printer`: Simple printer routine (immediate policy)

**Flow ID**: `simple_pipeline_flow`

**Use Case**: Test basic event routing, delay functionality

---

### Flow 2: Batch Processing Flow
**Purpose**: Demonstrate batch processing

**Structure**:
```
Echo -> BatchProcessor -> Printer
```

**Routines**:
- `echo`: Echo routine (immediate policy)
- `batch_processor`: Batch processor (batch_size_policy(3))
- `printer`: Simple printer routine (immediate policy)

**Flow ID**: `batch_processing_flow`

**Use Case**: Test batch processing, demonstrate batch_size_policy

---

### Flow 3: Countdown Flow
**Purpose**: Test routed stdout and progress display

**Structure**:
```
CountdownTimer -> Printer
```

**Routines**:
- `countdown`: Countdown timer routine (immediate policy)
- `printer`: Simple printer routine (immediate policy)

**Flow ID**: `countdown_flow`

**Use Case**: Test routed stdout capture, progress display in UI

---

## Implementation Plan

### Phase 1: Remove Existing Code
1. Delete all existing routine classes (12 classes)
2. Delete all existing flow creation functions (10 functions)
3. Simplify main() function
4. Keep only essential setup (monitoring, registry, factory registration)

### Phase 2: Implement New Routines
1. **CountdownTimer** - Countdown with stdout output
2. **BatchProcessor** - Batch processing with configurable size
3. **SimplePrinter** - Simple sink routine
4. **DelayRoutine** - Configurable delay
5. **EchoRoutine** - Simple echo
6. **CounterRoutine** - Message counter
7. **FilterRoutine** - Simple filter

### Phase 3: Create Flow Templates
1. Simple Pipeline Flow
2. Batch Processing Flow
3. Countdown Flow

### Phase 4: Register Everything
1. Register all routines in ObjectFactory
2. Register all flows in FlowRegistry
3. Register flows in flow_store (for API)

---

## Detailed Routine Specifications

### 1. CountdownTimer Routine

**Class Name**: `CountdownTimer`

**Slots**:
- `trigger`: Receives delay_ms

**Events**:
- `tick`: Emitted every second with remaining time

**Activation Policy**: `immediate_policy()`

**Input Format** (via trigger slot):
```python
{
    "delay_ms": 5000  # Total delay in milliseconds (required)
}
```

**Output Format** (tick event):
```python
{
    "remaining_ms": 4000,    # Remaining milliseconds
    "elapsed_ms": 1000,      # Elapsed milliseconds
    "progress": 0.2,         # Progress (0.0 to 1.0)
    "total_ms": 5000         # Total delay
}
```

**Print Output**:
```
[CountdownTimer] Starting countdown: 5000ms
[CountdownTimer] Remaining: 4000ms (80% complete)
[CountdownTimer] Remaining: 3000ms (60% complete)
[CountdownTimer] Remaining: 2000ms (40% complete)
[CountdownTimer] Remaining: 1000ms (20% complete)
[CountdownTimer] Countdown complete!
```

**Logic**:
- Extract delay_ms from trigger data
- Loop: sleep 1 second, calculate remaining, print, emit tick event
- Continue until remaining_ms <= 0

---

### 2. BatchProcessor Routine

**Class Name**: `BatchProcessor`

**Slots**:
- `input`: Receives data items

**Events**:
- `output`: Emits batch when ready

**Activation Policy**: `batch_size_policy(N)` where N is from config

**Configuration**:
```python
{
    "batch_size": 3  # Number of items to collect before processing
}
```

**Input Format** (via input slot):
```python
{
    "data": "item1",  # Data item
    "index": 1        # Optional index
}
```

**Output Format** (output event):
```python
{
    "batch": [
        {"data": "item1", "index": 1},
        {"data": "item2", "index": 2},
        {"data": "item3", "index": 3}
    ],
    "batch_size": 3,
    "processed_at": "2025-01-20T10:00:00"
}
```

**Print Output**:
```
[BatchProcessor] Processing batch of 3 items:
  - Item 1: item1
  - Item 2: item2
  - Item 3: item3
```

**Logic**:
- Collects items until batch_size is reached (handled by policy)
- Prints entire batch
- Emits batch as output event

---

### 3. SimplePrinter Routine

**Class Name**: `SimplePrinter`

**Slots**:
- `input`: Receives data

**Events**: None (sink routine)

**Activation Policy**: `immediate_policy()`

**Input Format** (via input slot):
```python
{
    "data": "any_data",  # Any data
    "index": 1          # Optional index
}
```

**Print Output**:
```
[SimplePrinter] Received: any_data (index: 1)
```

**Logic**:
- Receives input
- Prints data
- No output (sink)

---

### 4. DelayRoutine

**Class Name**: `DelayRoutine`

**Slots**:
- `input`: Receives data

**Events**:
- `output`: Emits data after delay

**Activation Policy**: `immediate_policy()`

**Configuration**:
```python
{
    "delay_ms": 2000  # Delay in milliseconds
}
```

**Input Format** (via input slot):
```python
{
    "data": "any_data"  # Data to delay
}
```

**Output Format** (output event):
```python
{
    "data": "any_data",      # Original data
    "delayed_by_ms": 2000,    # Delay applied
    "emitted_at": "2025-01-20T10:00:00"
}
```

**Print Output**:
```
[DelayRoutine] Delaying data for 2000ms...
[DelayRoutine] Data emitted after delay
```

**Logic**:
- Receives input
- Sleeps for delay_ms milliseconds
- Emits same data with metadata

---

### 5. EchoRoutine

**Class Name**: `EchoRoutine`

**Slots**:
- `input`: Receives data

**Events**:
- `output`: Emits same data

**Activation Policy**: `immediate_policy()`

**Input Format** (via input slot):
```python
{
    "data": "any_data"  # Data to echo
}
```

**Output Format** (output event):
```python
{
    "data": "any_data"  # Same as input
}
```

**Print Output**:
```
[EchoRoutine] Echo: any_data
```

**Logic**:
- Receives input
- Prints echo message
- Emits same data unchanged

---

### 6. CounterRoutine

**Class Name**: `CounterRoutine`

**Slots**:
- `input`: Receives data

**Events**:
- `output`: Emits count

**Activation Policy**: `immediate_policy()`

**Input Format** (via input slot):
```python
{
    "data": "any_data"  # Any data (ignored)
}
```

**Output Format** (output event):
```python
{
    "count": 5,  # Current message count
    "message": "Received 5 messages"
}
```

**Print Output**:
```
[CounterRoutine] Counter: 5 messages received
```

**Logic**:
- Maintains counter in routine state (via WorkerState)
- Increments on each message
- Emits current count

---

### 7. FilterRoutine

**Class Name**: `FilterRoutine`

**Slots**:
- `input`: Receives value

**Events**:
- `output`: Emits if value passes filter

**Activation Policy**: `immediate_policy()`

**Configuration**:
```python
{
    "threshold": 50  # Only emit if value >= threshold
}
```

**Input Format** (via input slot):
```python
{
    "value": 42  # Value to filter
}
```

**Output Format** (output event, only if value >= threshold):
```python
{
    "value": 42,
    "threshold": 50,
    "passed": False  # Whether value passed filter
}
```

**Print Output**:
```
[FilterRoutine] Filter: value=42, threshold=50, passed=False
```

**Logic**:
- Receives value
- Compares with threshold from config
- Emits only if value >= threshold
- Always prints result

---

## Flow Templates Specifications

### Flow 1: Simple Pipeline Flow

**Flow ID**: `simple_pipeline_flow`

**Structure**:
```
EchoRoutine -> DelayRoutine -> SimplePrinter
```

**Routine IDs**:
- `echo`: EchoRoutine
- `delay`: DelayRoutine (delay_ms=1000)
- `printer`: SimplePrinter

**Connections**:
- `echo.output` -> `delay.input`
- `delay.output` -> `printer.input`

**Entry Point**: `echo.trigger` (via post to echo.trigger)

**Use Case**: Test basic event routing, delay functionality

---

### Flow 2: Batch Processing Flow

**Flow ID**: `batch_processing_flow`

**Structure**:
```
EchoRoutine -> BatchProcessor -> SimplePrinter
```

**Routine IDs**:
- `echo`: EchoRoutine
- `batch_processor`: BatchProcessor (batch_size=3)
- `printer`: SimplePrinter

**Connections**:
- `echo.output` -> `batch_processor.input`
- `batch_processor.output` -> `printer.input`

**Entry Point**: `echo.trigger` (via post to echo.trigger)

**Use Case**: Test batch processing, demonstrate batch_size_policy

---

### Flow 3: Countdown Flow

**Flow ID**: `countdown_flow`

**Structure**:
```
CountdownTimer -> SimplePrinter
```

**Routine IDs**:
- `countdown`: CountdownTimer
- `printer`: SimplePrinter

**Connections**:
- `countdown.tick` -> `printer.input`

**Entry Point**: `countdown.trigger` (via post to countdown.trigger with delay_ms)

**Use Case**: Test routed stdout capture, progress display in UI

---

## Implementation Details

### Code Structure

```python
#!/usr/bin/env python
"""
Simplified Overseer Demo App for Routilux

Simple, practical routines and flows for testing and demonstration.
"""

# Imports
from routilux import Flow, Routine
from routilux.activation_policies import batch_size_policy, immediate_policy
from routilux.monitoring.registry import MonitoringRegistry
from routilux.core.registry import FlowRegistry
from routilux.monitoring.storage import flow_store
from routilux.tools.factory import ObjectFactory, ObjectMetadata

# ===== Routines =====

class CountdownTimer(Routine):
    """Countdown timer that emits progress events and prints to stdout.
    
    Input (via trigger slot):
        {
            "delay_ms": 5000  # Total delay in milliseconds
        }
    
    Output (tick event):
        {
            "remaining_ms": 4000,    # Remaining milliseconds
            "elapsed_ms": 1000,       # Elapsed milliseconds
            "progress": 0.2,          # Progress (0.0 to 1.0)
            "total_ms": 5000          # Total delay
        }
    
    Print Output:
        [CountdownTimer] Starting countdown: 5000ms
        [CountdownTimer] Remaining: 4000ms (80% complete)
        ...
    """
    # Implementation details...

class BatchProcessor(Routine):
    """Processes data in batches with configurable batch size.
    
    Configuration:
        {
            "batch_size": 3  # Number of items to collect
        }
    
    Input (via input slot):
        {
            "data": "item1",  # Data item
            "index": 1        # Optional index
        }
    
    Output (output event):
        {
            "batch": [...],      # List of batch items
            "batch_size": 3,
            "processed_at": "..."
        }
    """
    # Implementation details...

# ... (other routines)

# ===== Flows =====

def create_simple_pipeline_flow():
    """Simple linear flow: Echo -> Delay -> Printer"""
    # Implementation...

def create_batch_processing_flow():
    """Batch processing flow: Echo -> BatchProcessor -> Printer"""
    # Implementation...

def create_countdown_flow():
    """Countdown flow: CountdownTimer -> Printer"""
    # Implementation...

# ===== Main =====

def main():
    """Register all routines and flows"""
    # Enable monitoring
    # Register routines in factory
    # Create and register flows
    # Start server
```

---

## File Size Reduction

**Current**: ~1,294 lines  
**Target**: ~400-500 lines  
**Reduction**: ~60-70%

---

## Benefits

1. **Simplicity**: Each routine has single, clear purpose
2. **Clarity**: Input/output formats clearly documented in docstrings
3. **Practical**: Routines serve real testing/demo purposes
4. **Maintainability**: Easy to understand and modify
5. **Testability**: Simple routines are easier to test

---

## Testing Strategy

### Unit Tests
- Test each routine independently
- Verify input/output formats
- Test configuration options

### Integration Tests
- Test flows end-to-end
- Verify event routing
- Test routed stdout capture

### User Story Tests
- Test countdown flow with stdout capture
- Test batch processing flow
- Test simple pipeline flow

---

## Migration Notes

### Breaking Changes
- All existing routine names will change
- All existing flow IDs will change
- API users will need to update flow_id references

### Backward Compatibility
- Not maintained (as per user rules)
- Users should update their code to use new routines/flows

---

## Next Steps

1. **Review and Approve Plan**: Get user approval
2. **Implement Routines**: Create 7 simple routines
3. **Create Flows**: Create 3 flow templates
4. **Register Everything**: Register in factory and registry
5. **Test**: Verify all routines and flows work
6. **Update Documentation**: Update any docs referencing old routines

---

**End of Plan**
