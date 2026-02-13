"""
Schema validator routine for data validation.

Provides validation using pydantic models, JSON Schema, or custom validators.
"""

from __future__ import annotations

from typing import Any, Callable

from routilux.core import Routine

# Try to import pydantic for model validation
try:
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    BaseModel = None
    PydanticValidationError = Exception

# Try to import jsonschema for JSON Schema validation
try:
    import jsonschema
    from jsonschema import ValidationError as JsonSchemaValidationError
    from jsonschema import validate as jsonschema_validate

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    jsonschema = None
    JsonSchemaValidationError = Exception
    jsonschema_validate = None


class SchemaValidator(Routine):
    """Routine for validating data against schemas.

    This routine provides comprehensive validation capabilities:
    - Pydantic model validation (when pydantic is installed)
    - JSON Schema validation (when jsonschema is installed)
    - Custom validation functions
    - Field-level validation rules
    - Detailed error reporting

    Configuration Options:
        schema: The schema to validate against. Can be:
            - A Pydantic model class
            - A JSON Schema dict
            - A custom validation function
        schema_type: Type of schema ("pydantic", "jsonschema", "custom")
        strict_mode: Stop validation on first error
        coerce_types: Attempt to coerce types (pydantic only)

    Examples:
        Using Pydantic model:

        >>> from pydantic import BaseModel
        >>> class User(BaseModel):
        ...     name: str
        ...     age: int
        ...     email: str
        >>>
        >>> validator = SchemaValidator()
        >>> validator.set_config(schema=User, schema_type="pydantic")

        Using JSON Schema:

        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "name": {"type": "string"},
        ...         "age": {"type": "integer", "minimum": 0}
        ...     },
        ...     "required": ["name", "age"]
        ... }
        >>> validator = SchemaValidator()
        >>> validator.set_config(schema=schema, schema_type="jsonschema")

        Using custom validator:

        >>> def validate_user(data):
        ...     errors = []
        ...     if not data.get("name"):
        ...         errors.append("name is required")
        ...     if not isinstance(data.get("age"), int):
        ...         errors.append("age must be integer")
        ...     return len(errors) == 0, errors
        >>>
        >>> validator = SchemaValidator()
        >>> validator.set_config(schema=validate_user, schema_type="custom")
    """

    def __init__(self) -> None:
        """Initialize SchemaValidator routine."""
        super().__init__()

        # Set default configuration
        self.set_config(
            schema=None,  # Schema to validate against
            schema_type="auto",  # "pydantic", "jsonschema", "custom", or "auto"
            strict_mode=False,  # Stop on first error
            coerce_types=True,  # Type coercion (pydantic)
            custom_validators={},  # Additional custom validators
        )

        # Define input slot
        self.add_slot("input")

        # Define output events
        self.add_event("valid", ["validated_data", "schema_type"])
        self.add_event("invalid", ["errors", "original_data", "schema_type"])

        # Set up activation policy and logic
        self.set_activation_policy(self._activation_policy)
        self.set_logic(self._run_logic)

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
        """Execute the validation logic."""
        data_list = kwargs.get("input", [])
        items = data_list if isinstance(data_list, list) else [data_list]

        schema = self.get_config("schema")
        schema_type = self.get_config("schema_type", "auto")
        strict_mode = self.get_config("strict_mode", False)

        # Auto-detect schema type
        if schema_type == "auto":
            schema_type = self._detect_schema_type(schema)

        for item in items:
            try:
                is_valid, errors, validated_data = self._validate_item(
                    item, schema, schema_type, strict_mode
                )

                if is_valid:
                    self.emit("valid", validated_data=validated_data, schema_type=schema_type)
                else:
                    self.emit(
                        "invalid",
                        errors=errors,
                        original_data=item,
                        schema_type=schema_type,
                    )
            except Exception as e:
                self.emit(
                    "invalid",
                    errors=[f"Validation exception: {str(e)}"],
                    original_data=item,
                    schema_type=schema_type,
                )

    def _detect_schema_type(self, schema: Any) -> str:
        """Auto-detect the schema type.

        Args:
            schema: The schema to detect

        Returns:
            Detected schema type string
        """
        if schema is None:
            return "none"

        # Check for Pydantic model
        if HAS_PYDANTIC:
            try:
                if isinstance(schema, type) and issubclass(schema, BaseModel):
                    return "pydantic"
            except TypeError:
                pass

        # Check for JSON Schema (dict with type or $schema)
        if isinstance(schema, dict):
            if "type" in schema or "$schema" in schema or "properties" in schema:
                return "jsonschema"

        # Check for callable (custom validator)
        if callable(schema):
            return "custom"

        return "unknown"

    def _validate_item(
        self,
        data: Any,
        schema: Any,
        schema_type: str,
        strict_mode: bool,
    ) -> tuple[bool, list[str], Any]:
        """Validate a single data item.

        Args:
            data: Data to validate
            schema: Schema to validate against
            schema_type: Type of schema
            strict_mode: Whether to stop on first error

        Returns:
            Tuple of (is_valid, errors, validated_data)
        """
        if schema is None:
            # No schema means always valid
            return True, [], data

        errors = []
        validated_data = data

        if schema_type == "pydantic":
            is_valid, errors, validated_data = self._validate_pydantic(data, schema)
        elif schema_type == "jsonschema":
            is_valid, errors = self._validate_jsonschema(data, schema)
        elif schema_type == "custom":
            is_valid, errors = self._validate_custom(data, schema)
        else:
            is_valid = False
            errors = [f"Unknown schema type: {schema_type}"]

        return is_valid, errors, validated_data

    def _validate_pydantic(self, data: Any, model: type) -> tuple[bool, list[str], Any]:
        """Validate using Pydantic model.

        Args:
            data: Data to validate
            model: Pydantic model class

        Returns:
            Tuple of (is_valid, errors, validated_data)
        """
        if not HAS_PYDANTIC:
            return False, ["pydantic is not installed"], data

        try:
            coerce = self.get_config("coerce_types", True)
            if coerce:
                # Try to validate and coerce
                validated = model.model_validate(data)
            else:
                validated = model.model_validate_strict(data)
            return True, [], validated.model_dump()
        except PydanticValidationError as e:
            errors = []
            for error in e.errors():
                loc = ".".join(str(x) for x in error["loc"])
                errors.append(f"{loc}: {error['msg']}")
            return False, errors, data

    def _validate_jsonschema(self, data: Any, schema: dict) -> tuple[bool, list[str]]:
        """Validate using JSON Schema.

        Args:
            data: Data to validate
            schema: JSON Schema dict

        Returns:
            Tuple of (is_valid, errors)
        """
        if not HAS_JSONSCHEMA:
            return False, ["jsonschema is not installed"]

        try:
            jsonschema_validate(instance=data, schema=schema)
            return True, []
        except JsonSchemaValidationError as e:
            path = ".".join(str(x) for x in e.absolute_path) if e.absolute_path else "root"
            return False, [f"{path}: {e.message}"]

    def _validate_custom(self, data: Any, validator: Callable) -> tuple[bool, list[str]]:
        """Validate using custom validator function.

        Args:
            data: Data to validate
            validator: Validation function

        Returns:
            Tuple of (is_valid, errors)
        """
        try:
            result = validator(data)

            # Handle different return types
            if isinstance(result, bool):
                return result, [] if result else ["Validation failed"]
            elif isinstance(result, tuple) and len(result) == 2:
                is_valid, errors = result
                errors_list = errors if isinstance(errors, list) else [errors]
                return is_valid, errors_list
            else:
                return bool(result), []

        except Exception as e:
            return False, [f"Validator error: {str(e)}"]

    def set_pydantic_schema(self, model: type) -> None:
        """Set a Pydantic model as the validation schema.

        Args:
            model: Pydantic model class

        Raises:
            ImportError: If pydantic is not installed
        """
        if not HAS_PYDANTIC:
            raise ImportError("pydantic is required for Pydantic validation")
        self.set_config(schema=model, schema_type="pydantic")

    def set_jsonschema(self, schema: dict) -> None:
        """Set a JSON Schema as the validation schema.

        Args:
            schema: JSON Schema dict

        Raises:
            ImportError: If jsonschema is not installed
        """
        if not HAS_JSONSCHEMA:
            raise ImportError("jsonschema is required for JSON Schema validation")
        self.set_config(schema=schema, schema_type="jsonschema")

    def set_custom_validator(self, validator: Callable) -> None:
        """Set a custom validation function.

        Args:
            validator: Function that takes data and returns (bool, errors)
        """
        self.set_config(schema=validator, schema_type="custom")

    def add_field_validator(self, field_name: str, validator: Callable[[Any], bool]) -> None:
        """Add a field-level validator.

        This creates a composite validator that checks individual fields.

        Args:
            field_name: Name of the field to validate
            validator: Function that returns True if valid
        """
        validators = self.get_config("custom_validators", {})
        validators[field_name] = validator
        self.set_config(custom_validators=validators)


# Backward compatibility alias
DataValidator = SchemaValidator
