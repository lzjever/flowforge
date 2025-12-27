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
        # String expression (recommended for serialization)
        ("high", "data.get('priority') == 'high'"),
        ("low", "isinstance(data, dict) and data.get('priority') == 'low'"),
        # Dictionary condition
        ("medium", {"priority": "medium"}),
    ],
    default_route="normal"
)

flow = Flow()
flow.add_routine(router, "router")
```

**Configuration:**
- `routes` (list): List of (route_name, condition) tuples. Condition can be:
  - **String expression** (recommended): `"data.get('priority') == 'high'"` - Fully serializable
  - **Function reference**: A callable function - Serializable if function is in a module
  - **Dictionary**: Field matching condition - Fully serializable
  - **Lambda function**: `lambda x: x.get('priority') == 'high'` - May be converted to string expression during serialization
- `default_route` (str): Default route name if no condition matches
- `route_priority` (str): Priority strategy - "first_match" or "all_matches" (default: "first_match")

**Input:**
- `data` (Any): Data to route

**Output:**
- Emits to route event (e.g., "high", "low", "normal")
- `data` (Any): Original data
- `route` (str): Route name that matched

**Serialization:**
ConditionalRouter supports full serialization/deserialization. For best results:
- ✅ **Use string expressions**: `"data.get('priority') == 'high'"` - Always serializable
- ✅ **Use dictionary conditions**: `{"priority": "high"}` - Always serializable
- ✅ **Use module-level functions**: Functions defined at module level can be serialized
- ⚠️ **Lambda functions**: May be automatically converted to string expressions, but complex lambdas may fail

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

