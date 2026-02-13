"""
Mapper routine for field mapping and data transformation.

Provides field remapping, JSONPath extraction, and nested data transformation.
"""

from __future__ import annotations

from typing import Any, Callable

from routilux.core import Routine

# Try to import jsonpath_ng for JSONPath support
try:
    from jsonpath_ng import parse as jsonpath_parse

    HAS_JSONPATH = True
except ImportError:
    HAS_JSONPATH = False
    jsonpath_parse = None


class Mapper(Routine):
    """Routine for mapping and transforming data fields.

    This routine provides flexible field mapping capabilities including:
    - Simple field renaming
    - JSONPath extraction for nested data
    - Dot-notation path extraction (fallback when jsonpath-ng not installed)
    - Field value transformation
    - Missing field handling

    Configuration Options:
        mappings: Dict of field mappings. Values can be:
            - String (new field name for rename)
            - JSONPath string (starts with $.)
            - Dict with "path", "transform", "default" keys
        jsonpath_enabled: Whether to use JSONPath (requires jsonpath-ng)
        drop_missing: Whether to drop fields that don't exist in source
        keep_unmapped: Whether to keep fields not in mappings
        default_value: Default value for missing fields

    Examples:
        Simple field renaming:

        >>> mapper = Mapper()
        >>> mapper.set_config(mappings={
        ...     "old_name": "new_name",
        ...     "user_name": "username"
        ... })

        JSONPath extraction:

        >>> mapper = Mapper()
        >>> mapper.set_config(
        ...     jsonpath_enabled=True,
        ...     mappings={
        ...         "user_name": "$.user.profile.name",
        ...         "user_email": "$.user.contact.email"
        ...     }
        ... )

        With transforms:

        >>> mapper = Mapper()
        >>> mapper.set_config(mappings={
        ...     "full_name": {
        ...         "path": "$.user",
        ...         "transform": lambda u: f"{u['first']} {u['last']}"
        ...     },
        ...     "status": {
        ...         "path": "$.state",
        ...         "default": "unknown"
        ...     }
        ... })
    """

    def __init__(self) -> None:
        """Initialize Mapper routine."""
        super().__init__()

        # Set default configuration
        self.set_config(
            mappings={},  # Field mapping rules
            jsonpath_enabled=True,  # Enable JSONPath (requires jsonpath-ng)
            drop_missing=True,  # Drop fields that don't exist
            keep_unmapped=False,  # Keep fields not in mappings
            default_value=None,  # Default for missing fields
        )

        # Define input slot
        self.add_slot("input")

        # Define output events
        self.add_event("output", ["mapped_data", "fields_mapped"])
        self.add_event("error", ["error", "original_data"])

        # Set up activation policy and logic
        self.set_activation_policy(self._activation_policy)
        self.set_logic(self._run_logic)

        # Cache for compiled JSONPath expressions
        self._jsonpath_cache: dict[str, Any] = {}

    def _activation_policy(self, slots: dict, worker_state: Any) -> tuple[bool, dict, str]:
        """Check if routine should activate based on input slot state."""
        slot = slots.get("input")
        if slot is None:
            return False, {}, "no_slot"

        has_new = len(slot.new_data) > 0
        if has_new:
            data_slice = {"input": slot.consume_all_new()}
            return True, data_slice, "slot_activated"
        return False, {}, "no_new_data"

    def _run_logic(self, **kwargs: Any) -> None:
        """Execute the mapping logic."""
        data_list = kwargs.get("input", [])
        items = data_list if isinstance(data_list, list) else [data_list]

        mappings = self.get_config("mappings", {})
        jsonpath_enabled = self.get_config("jsonpath_enabled", True) and HAS_JSONPATH
        drop_missing = self.get_config("drop_missing", True)
        keep_unmapped = self.get_config("keep_unmapped", False)
        default_value = self.get_config("default_value", None)

        for item in items:
            try:
                result, fields_mapped = self._map_item(
                    item,
                    mappings,
                    jsonpath_enabled,
                    drop_missing,
                    keep_unmapped,
                    default_value,
                )
                self.emit("output", mapped_data=result, fields_mapped=fields_mapped)
            except Exception as e:
                self.emit("error", error=str(e), original_data=item)

    def _map_item(
        self,
        data: Any,
        mappings: dict,
        jsonpath_enabled: bool,
        drop_missing: bool,
        keep_unmapped: bool,
        default_value: Any,
    ) -> tuple[dict, list[str]]:
        """Map a single data item.

        Args:
            data: Input data to map
            mappings: Field mapping rules
            jsonpath_enabled: Whether JSONPath is available
            drop_missing: Whether to drop missing fields
            keep_unmapped: Whether to keep unmapped fields
            default_value: Default value for missing fields

        Returns:
            Tuple of (mapped_data, list of mapped field names)
        """
        if not isinstance(data, dict):
            # If input is not a dict, wrap it
            data = {"value": data}

        result = {}
        fields_mapped = []

        # Process mappings
        for target_field, mapping in mappings.items():
            try:
                value, found = self._extract_value(data, mapping, jsonpath_enabled)

                if found:
                    result[target_field] = value
                    fields_mapped.append(target_field)
                elif not drop_missing:
                    result[target_field] = default_value
                    fields_mapped.append(target_field)
            except Exception:
                if not drop_missing:
                    result[target_field] = default_value

        # Keep unmapped fields if configured
        if keep_unmapped:
            for key, value in data.items():
                if key not in mappings and key not in result:
                    result[key] = value

        return result, fields_mapped

    def _extract_value(self, data: dict, mapping: Any, jsonpath_enabled: bool) -> tuple[Any, bool]:
        """Extract value from data using mapping rule.

        Args:
            data: Source data dict
            mapping: Mapping rule (string, dict, or callable)
            jsonpath_enabled: Whether JSONPath is available

        Returns:
            Tuple of (value, found)
        """
        # String mapping - could be rename, JSONPath, or dot-notation
        if isinstance(mapping, str):
            # Check if it's a JSONPath expression
            if mapping.startswith("$.") and jsonpath_enabled:
                return self._extract_jsonpath(data, mapping)
            # Check if it's dot-notation
            elif "." in mapping:
                return self._extract_dot_path(data, mapping)
            # Simple field rename
            elif mapping in data:
                return data[mapping], True
            else:
                return None, False

        # Dict mapping with options
        elif isinstance(mapping, dict):
            path = mapping.get("path", "")
            transform = mapping.get("transform")
            default = mapping.get("default")

            # Extract value using path
            if path:
                if path.startswith("$.") and jsonpath_enabled:
                    value, found = self._extract_jsonpath(data, path)
                elif "." in path:
                    value, found = self._extract_dot_path(data, path)
                elif path in data:
                    value, found = data[path], True
                else:
                    value, found = default, False
            else:
                value, found = data, True

            # Apply transform if provided
            if found and transform and callable(transform):
                try:
                    value = transform(value)
                except Exception:
                    value = default
                    found = False

            return value, found

        # Callable mapping
        elif callable(mapping):
            try:
                return mapping(data), True
            except Exception:
                return None, False

        return None, False

    def _extract_jsonpath(self, data: dict, path: str) -> tuple[Any, bool]:
        """Extract value using JSONPath expression.

        Args:
            data: Source data
            path: JSONPath expression

        Returns:
            Tuple of (value, found)
        """
        if not HAS_JSONPATH:
            # Fallback to dot notation
            return self._extract_dot_path(data, path.lstrip("$."))

        # Use cached compiled expression
        if path not in self._jsonpath_cache:
            self._jsonpath_cache[path] = jsonpath_parse(path)

        expr = self._jsonpath_cache[path]
        matches = expr.find(data)

        if matches:
            # Return first match, or list if multiple
            if len(matches) == 1:
                return matches[0].value, True
            return [m.value for m in matches], True

        return None, False

    def _extract_dot_path(self, data: dict, path: str) -> tuple[Any, bool]:
        """Extract value using dot-notation path.

        Args:
            data: Source data
            path: Dot-notation path (e.g., "user.profile.name")

        Returns:
            Tuple of (value, found)
        """
        # Remove leading $. if present
        if path.startswith("$."):
            path = path[2:]

        parts = path.split(".")
        current = data

        for part in parts:
            # Handle array index notation: items[0]
            if "[" in part and part.endswith("]"):
                field_name = part[: part.index("[")]
                index = int(part[part.index("[") + 1 : -1])

                if field_name not in current:
                    return None, False
                current = current[field_name]
                if not isinstance(current, list) or index >= len(current):
                    return None, False
                current = current[index]
            else:
                if not isinstance(current, dict) or part not in current:
                    return None, False
                current = current[part]

        return current, True

    def add_mapping(
        self, target: str, source: str | dict, transform: Callable | None = None
    ) -> None:
        """Add a field mapping.

        Args:
            target: Target field name
            source: Source field path or mapping dict
            transform: Optional transform function
        """
        mappings = self.get_config("mappings", {})
        if transform:
            if isinstance(source, str):
                mappings[target] = {"path": source, "transform": transform}
            else:
                source["transform"] = transform
                mappings[target] = source
        else:
            mappings[target] = source
        self.set_config(mappings=mappings)


# Backward compatibility alias
DataTransformer = Mapper
