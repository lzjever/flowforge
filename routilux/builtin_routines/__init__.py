"""
Routilux built-in routines.

This package contains commonly used routines that are generic and reusable
across different business domains. Routines are organized by category:

- text_processing: Text manipulation and formatting routines
- utils: General utility routines
- data_processing: Data transformation and validation routines
- control_flow: Flow control and routing routines
- reliability: Error handling and retry routines

All routines inherit from Routine which provides common utilities like
_extract_input_data() and _track_operation().
"""

from routilux.builtin_routines.control_flow import (
    Aggregator,
    Batcher,
    ConditionalRouter,
    Debouncer,
    Splitter,
)
from routilux.builtin_routines.data_processing import (
    DataTransformer,
    DataValidator,
    Filter,
    Mapper,
    SchemaValidator,
)
from routilux.builtin_routines.reliability import RetryHandler
from routilux.builtin_routines.text_processing import ResultExtractor

__all__ = [
    # Text processing
    "ResultExtractor",
    # Data processing
    "DataTransformer",
    "DataValidator",
    "Mapper",
    "SchemaValidator",
    "Filter",
    # Control flow
    "ConditionalRouter",
    "Aggregator",
    "Batcher",
    "Debouncer",
    "Splitter",
    # Reliability
    "RetryHandler",
]
