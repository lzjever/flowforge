# FlowForge Built-in Routines

This package contains commonly used routines that are generic and reusable across different business domains.

## Architecture

All built-in routines inherit from `Routine`, which provides:
- **Common data extraction**: Unified handling of slot input data
- **Statistics tracking**: Consistent operation tracking across routines
- **Error handling**: Standardized error management
- **Configuration management**: Safe configuration access

This architecture ensures consistency, reduces code duplication, and makes it easier to create new routines.

## Directory Structure

```
builtin_routines/
├── text_processing/    # Text manipulation and formatting
│   ├── tests/         # Package-specific tests
│   └── README.md      # Package documentation
├── utils/              # General utility routines
│   ├── tests/         # Package-specific tests
│   └── README.md      # Package documentation
├── data_processing/    # Data transformation and validation
│   ├── tests/         # Package-specific tests
│   └── README.md      # Package documentation
└── control_flow/      # Flow control and routing
    ├── tests/         # Package-specific tests
    └── README.md      # Package documentation
```

Each package is self-contained with its own tests and documentation, making it easy to copy and use in other projects.

## Text Processing Routines

### TextClipper

Clips text to a maximum length while preserving important information.

**Features:**
- Preserves tracebacks completely
- Clips text line by line
- Provides informative truncation messages
- Configurable maximum length

**Example:**
```python
from flowforge.builtin_routines import TextClipper

clipper = TextClipper()
clipper.set_config(max_length=1000)

# In a flow
flow.add_routine(clipper, "clipper")
flow.connect("source", "output", "clipper", "input")
flow.connect("clipper", "output", "target", "input")
```

### TextRenderer

Renders objects (dicts, lists) into formatted text with XML-like tags.

**Features:**
- Recursively renders nested structures
- Adds XML-like tags for structure
- Handles primitive types
- Configurable tag formatting

**Example:**
```python
from flowforge.routines import TextRenderer

renderer = TextRenderer()
renderer.set_config(tag_format="xml")

# Input: {"name": "test", "value": 42}
# Output: "<name>test</name>\n<value>42</value>"
```

### ResultExtractor

Extracts and formats results from various output formats with extensible architecture.

**Features:**
- **Multiple built-in extractors**: JSON, YAML, XML, code blocks, interpreter output
- **Extensible architecture**: Register custom extractors
- **Multiple extraction strategies**: auto, priority, all, first_match
- **Intelligent type detection**: Automatic format detection
- **Confidence scoring**: Quality metrics for extraction results
- **Comprehensive error handling**: Graceful fallback mechanisms
- **Rich metadata**: Detailed information about extraction process

**Extraction Strategies:**
- `auto`: Try extractors in order, return first successful match (default)
- `priority`: Use custom priority order
- `all`: Return all successful extractions
- `first_match`: Return first successful match (same as auto)

**Examples:**
```python
from flowforge.routines import ResultExtractor

# Basic usage
extractor = ResultExtractor()
extractor.set_config(strategy="auto")
extractor.input_slot.receive({"data": '```json\n{"key": "value"}\n```'})

# Register custom extractor
def my_extractor(data, config):
    if isinstance(data, str) and data.startswith("CUSTOM:"):
        return data[7:], "custom", {"method": "prefix"}
    return None

extractor.register_extractor("custom_prefix", my_extractor)
extractor.set_config(extractor_priority=["custom_prefix"])
```

## Utility Routines

### TimeProvider

Provides current time in various formats.

**Features:**
- Multiple time formats (ISO, formatted string, timestamp)
- Configurable format strings
- Locale-aware formatting

**Example:**
```python
from flowforge.routines import TimeProvider

time_provider = TimeProvider()
time_provider.set_config(format="iso", include_weekday=True)

# Emits: {"time_string": "...", "timestamp": 1234567890, ...}
```

### DataFlattener

Flattens nested data structures into flat dictionaries.

**Features:**
- Recursive flattening
- Handles Serializable objects
- Configurable separator for keys
- Preserves list indices

**Example:**
```python
from flowforge.routines import DataFlattener

flattener = DataFlattener()
flattener.set_config(separator=".")

# Input: {"a": {"b": 1, "c": [2, 3]}}
# Output: {"a.b": 1, "a.c.0": 2, "a.c.1": 3}
```

## Data Processing Routines

### DataTransformer

Transforms data using configurable transformation functions.

**Features:**
- Configurable transformation functions
- Chain multiple transformations
- Built-in transformations (lowercase, uppercase, etc.)
- Custom transformation support

**Example:**
```python
from flowforge.routines import DataTransformer

transformer = DataTransformer()
transformer.set_config(transformations=["lowercase", "strip_whitespace"])

# Register custom transformation
transformer.register_transformation("custom", lambda x: x.upper())
```

### DataValidator

Validates data against schemas or validation rules.

**Features:**
- Configurable validation rules
- Built-in validators (not_empty, is_string, etc.)
- Detailed validation error messages
- Optional strict mode

**Example:**
```python
from flowforge.routines import DataValidator

validator = DataValidator()
validator.set_config(
    rules={
        "name": "not_empty",
        "age": lambda x: isinstance(x, int) and x > 0
    },
    required_fields=["name", "age"]
)
```

## Control Flow Routines

### ConditionalRouter

Routes data to different outputs based on conditions.

**Features:**
- Multiple conditional routes
- Configurable condition functions
- Default route for unmatched cases
- Priority-based routing

**Example:**
```python
from flowforge.routines import ConditionalRouter

router = ConditionalRouter()
router.set_config(
    routes=[
        ("high_priority", lambda x: x.get("priority") == "high"),
        ("low_priority", lambda x: x.get("priority") == "low"),
    ],
    default_route="normal"
)
```

### RetryHandler

Handles retry logic for operations that may fail.

**Features:**
- Configurable retry attempts
- Exponential backoff
- Custom retry conditions
- Detailed retry statistics

**Example:**
```python
from flowforge.routines import RetryHandler

retry_handler = RetryHandler()
retry_handler.set_config(
    max_retries=3,
    retry_delay=1.0,
    backoff_multiplier=2.0
)

# Execute operation with retry
retry_handler.input_slot.receive({
    "func": my_function,
    "args": [arg1, arg2],
    "kwargs": {"key": "value"}
})
```

## Usage in Flows

All routines follow the same pattern:

1. Create routine instance
2. Configure using `set_config()`
3. Add to flow
4. Connect slots and events

```python
from flowforge import Flow
from flowforge.builtin_routines import TextClipper, ConditionalRouter

flow = Flow()

# Create routines
clipper = TextClipper()
clipper.set_config(max_length=1000)

router = ConditionalRouter()
router.set_config(routes=[...])

# Add to flow
flow.add_routine(clipper, "clipper")
flow.add_routine(router, "router")

# Connect
flow.connect("source", "output", "clipper", "input")
flow.connect("clipper", "output", "router", "input")
```

## Best Practices

1. **Configuration**: Always use `set_config()` instead of constructor parameters
2. **Statistics**: Use `_track_operation()` for consistent statistics tracking
3. **Data Extraction**: Use `_extract_input_data()` or `_extract_string_input()` for slot data
4. **Configuration Access**: Use `_safe_get_config()` for safe configuration retrieval
5. **Error Handling**: Routines handle errors gracefully and emit error events
6. **Serialization**: All routines are fully serializable via `_config` and `_stats`

## Creating Custom Routines

When creating custom routines, inherit from `BaseRoutine` to get common utilities:

```python
from flowforge import Routine

class MyCustomRoutine(Routine):
    def __init__(self):
        super().__init__()
        self.set_config(my_setting="default_value")
        self.input_slot = self.define_slot("input", handler=self._handle_input)
        self.output_event = self.define_event("output", ["result"])
    
    def _handle_input(self, data=None, **kwargs):
        # Use base class helper to extract data
        data = self._extract_input_data(data, **kwargs)
        
        # Track operation
        self._track_operation("my_operations")
        
        # Process data
        result = self._process(data)
        
        # Emit result
        self.emit("output", result=result)
```

## Code Quality Improvements

The routines have been refactored to:
- **Eliminate code duplication**: Common logic extracted to `BaseRoutine`
- **Improve type hints**: Better type annotations for better IDE support
- **Consistent error handling**: Unified error tracking and reporting
- **Better documentation**: Comprehensive docstrings and examples

