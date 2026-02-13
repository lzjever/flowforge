"""
Data processing routines.

Routines for data transformation, validation, and manipulation.
"""

# New enhanced implementations
from routilux.builtin_routines.data_processing.filter import Filter
from routilux.builtin_routines.data_processing.mapper import DataTransformer, Mapper
from routilux.builtin_routines.data_processing.schema_validator import (
    DataValidator,
    SchemaValidator,
)

__all__ = [
    # New names
    "Mapper",
    "SchemaValidator",
    "Filter",
    # Backward compatibility aliases
    "DataTransformer",
    "DataValidator",
]
