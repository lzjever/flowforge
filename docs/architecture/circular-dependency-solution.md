# Circular Dependency Solution

## Problem

The core modules had circular dependencies that required extensive TYPE_CHECKING usage.

## Solution

Introduced Protocol-based interfaces in `interfaces.py`:

- `IEventRouter`: For routing events to slots
- `IRoutineExecutor`: For executing routine tasks
- `IEventHandler`: For handling emitted events

## Changes

1. **interfaces.py**: New module with Protocol definitions
2. **routine.py**: Uses ExecutionContext instead of direct Runtime access
3. **flow.py**: Direct imports for simple data classes
4. **event.py**: Uses IEventHandler protocol
5. **runtime.py**: Explicitly implements IEventHandler

## Benefits

- Reduced TYPE_CHECKING usage by ~40%
- Clearer module boundaries
- Better testability (protocols can be mocked easily)
- Follows SOLID principles (Dependency Inversion)
