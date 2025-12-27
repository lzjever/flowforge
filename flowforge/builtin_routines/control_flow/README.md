# Control Flow Routines

This package provides routines for flow control, routing, and conditional execution.

## Routines

### ConditionalRouter

Routes data to different outputs based on conditions.

**Usage:**
```python
from flowforge.builtin_routines.control_flow import ConditionalRouter

router = ConditionalRouter()
router.set_config(
    routes=[
        ("high", lambda x: isinstance(x, dict) and x.get("priority") == "high"),
        ("low", lambda x: isinstance(x, dict) and x.get("priority") == "low"),
    ],
    default_route="normal"
)

flow = Flow()
flow.add_routine(router, "router")
```

**Configuration:**
- `routes` (list): List of (route_name, condition_function) tuples
- `default_route` (str): Default route name if no condition matches
- `route_priority` (str): Priority strategy - "first_match" or "all" (default: "first_match")

**Input:**
- `data` (Any): Data to route

**Output:**
- Emits to route event (e.g., "high", "low", "normal")
- `data` (Any): Original data
- `route` (str): Route name that matched

### RetryHandler

Handles retry logic for operations that may fail.

**Usage:**
```python
from flowforge.builtin_routines.control_flow import RetryHandler

retry_handler = RetryHandler()
retry_handler.set_config(
    max_retries=3,
    retry_delay=1.0,
    backoff_multiplier=2.0,
    retryable_exceptions=[ValueError, KeyError]
)

flow = Flow()
flow.add_routine(retry_handler, "retry_handler")
```

**Configuration:**
- `max_retries` (int): Maximum number of retries (default: 3)
- `retry_delay` (float): Initial delay between retries in seconds (default: 1.0)
- `backoff_multiplier` (float): Multiplier for exponential backoff (default: 2.0)
- `retryable_exceptions` (list): List of exception types to retry (default: [Exception])
- `retry_condition` (callable, optional): Custom condition function for retries

**Input:**
- `operation` (dict): Operation definition with:
  - `function` (callable): Function to execute
  - `args` (list, optional): Positional arguments
  - `kwargs` (dict, optional): Keyword arguments

**Output:**
- `success` event: Emitted on successful execution
  - `result` (Any): Function result
  - `attempts` (int): Number of attempts made
- `failure` event: Emitted on final failure
  - `error` (Exception): Last exception raised
  - `attempts` (int): Number of attempts made

## Installation

This package can be used standalone or as part of FlowForge:

```python
# Standalone usage
import sys
sys.path.insert(0, '/path/to/flowforge/builtin_routines/control_flow')
from control_flow import ConditionalRouter

# As part of FlowForge
from flowforge.builtin_routines.control_flow import ConditionalRouter
```

## Testing

Run tests from the package directory:

```bash
cd flowforge/builtin_routines/control_flow
python -m unittest tests.test_control_flow -v
```

## Examples

See `tests/test_control_flow.py` for comprehensive examples.

