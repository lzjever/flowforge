"""
Object metadata for factory registration.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ObjectMetadata:
    """Metadata for registered objects in the factory.

    Attributes:
        name: Object name (identifier).
        description: Human-readable description.
        category: Category for grouping (e.g., "data_processing", "validation").
        tags: List of tags for searching/filtering.
        example_config: Example configuration dictionary.
        version: Version string.
        docstring: Optional full docstring from the class/object. Returned as-is for client parsing.
    """

    name: str
    description: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    example_config: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    docstring: Optional[str] = None
