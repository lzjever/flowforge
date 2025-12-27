# Data Processing Routines

This package provides routines for data transformation, validation, and manipulation.

## Routines

### DataTransformer

Transforms data using configurable transformation functions.

**Usage:**
```python
from flowforge.builtin_routines.data_processing import DataTransformer

transformer = DataTransformer()
transformer.set_config(transformations=["lowercase", "strip"])

flow = Flow()
flow.add_routine(transformer, "transformer")
```

**Configuration:**
- `transformations` (list): List of transformation names to apply
- `transformation_map` (dict): Custom transformation functions

**Built-in Transformations:**
- `lowercase`: Convert string to lowercase
- `uppercase`: Convert string to uppercase
- `strip`: Strip whitespace
- `reverse`: Reverse string or list

**Input:**
- `data` (Any): Data to transform
- `transformations` (list, optional): Override config transformations

**Output:**
- `transformed_data` (Any): Transformed data
- `transformations_applied` (list): List of transformations applied

### DataValidator

Validates data against schemas or validation rules.

**Usage:**
```python
from flowforge.builtin_routines.data_processing import DataValidator

validator = DataValidator()
validator.set_config(
    rules={"age": "is_int", "name": "is_string"},
    required_fields=["name", "age"],
    strict_mode=False
)

flow = Flow()
flow.add_routine(validator, "validator")
```

**Configuration:**
- `rules` (dict): Validation rules mapping field names to validators
- `required_fields` (list): List of required field names
- `strict_mode` (bool): Reject extra fields not in rules (default: False)
- `allow_extra_fields` (bool): Allow extra fields (default: True)

**Built-in Validators:**
- `is_string`: Check if value is string
- `is_int`: Check if value is integer
- `is_float`: Check if value is float
- `is_dict`: Check if value is dictionary
- `is_list`: Check if value is list
- `not_empty`: Check if value is not empty

**Input:**
- `data` (Any): Data to validate
- `rules` (dict, optional): Override config rules

**Output:**
- `is_valid` (bool): Whether data is valid
- `validated_data` (Any): Validated data (if valid)
- `errors` (list): List of validation errors (if invalid)

## Installation

This package can be used standalone or as part of FlowForge:

```python
# Standalone usage
import sys
sys.path.insert(0, '/path/to/flowforge/builtin_routines/data_processing')
from data_processing import DataTransformer

# As part of FlowForge
from flowforge.builtin_routines.data_processing import DataTransformer
```

## Testing

Run tests from the package directory:

```bash
cd flowforge/builtin_routines/data_processing
python -m unittest tests.test_data_processing -v
```

## Examples

See `tests/test_data_processing.py` for comprehensive examples.

