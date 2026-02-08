# Error Handling Guide

## Overview

Routilux provides flexible error handling strategies for workflow execution.

## Error Strategies

### STOP (Default)
Stop execution immediately when an error occurs.

**Use when:** The error is critical and subsequent work cannot proceed.

```python
from routilux.core import ErrorHandler, ErrorStrategy

handler = ErrorHandler(strategy=ErrorStrategy.STOP)
routine.set_error_handler(handler)
```

### CONTINUE
Log the error and continue with next routines.

**Use when:** The routine is optional and its failure shouldn't block the workflow.

```python
handler = ErrorHandler(strategy=ErrorStrategy.CONTINUE)
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
)
routine.set_error_handler(handler)
```

### SKIP
Skip the routine and continue with connected routines.

**Use when:** You want to bypass a failed routine but still execute downstream work.

## Decision Tree

```
Is the routine critical for workflow success?
├─ Yes → Use RETRY (transient errors) or STOP (permanent errors)
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
