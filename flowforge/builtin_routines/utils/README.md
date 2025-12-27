# Utility Routines

This package provides general-purpose utility routines for common operations.

## Routines

### TimeProvider

Provides current time in various formats (ISO, formatted, timestamp, custom).

**Usage:**
```python
from flowforge.builtin_routines.utils import TimeProvider
from flowforge import Flow

time_provider = TimeProvider()
time_provider.set_config(format="iso", locale="zh_CN")

flow = Flow()
flow.add_routine(time_provider, "time_provider")
```

**Configuration:**
- `format` (str): Format type - "iso", "formatted", "timestamp", "custom" (default: "iso")
- `locale` (str): Locale for formatted output (default: "zh_CN")
- `custom_format` (str): Custom format string for "custom" format (default: "%Y-%m-%d %H:%M:%S")
- `include_weekday` (bool): Include weekday in formatted output (default: True)

**Input:**
- Trigger via `trigger_slot.receive({})`

**Output:**
- `time_string` (str): Formatted time string
- `timestamp` (float): Unix timestamp
- `datetime` (str): ISO datetime string
- `formatted` (str): Custom formatted string

### DataFlattener

Flattens nested data structures into flat dictionaries.

**Usage:**
```python
from flowforge.builtin_routines.utils import DataFlattener

flattener = DataFlattener()
flattener.set_config(separator=".", max_depth=100, preserve_lists=True)

flow = Flow()
flow.add_routine(flattener, "flattener")
```

**Configuration:**
- `separator` (str): Key separator for nested keys (default: ".")
- `max_depth` (int): Maximum nesting depth (default: 100)
- `preserve_lists` (bool): Preserve list structures (default: True)

**Input:**
- `data` (Any): Data to flatten

**Output:**
- `flattened_data` (dict): Flattened dictionary

## Installation

This package can be used standalone or as part of FlowForge:

```python
# Standalone usage
import sys
sys.path.insert(0, '/path/to/flowforge/builtin_routines/utils')
from utils import TimeProvider

# As part of FlowForge
from flowforge.builtin_routines.utils import TimeProvider
```

## Testing

Run tests from the package directory:

```bash
cd flowforge/builtin_routines/utils
python -m unittest tests.test_utils -v
```

## Examples

See `tests/test_utils.py` for comprehensive examples.

