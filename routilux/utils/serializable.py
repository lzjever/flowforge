"""
Serialization utilities and base classes.

Generic serialization/deserialization for objects and callable types.
"""

import importlib
import inspect
from typing import Any, Dict, List, Optional, Callable, Type, Union


class SerializableRegistry:
    """Registry for serializable classes to facilitate class lookup and instantiation."""

    registry = {}

    @classmethod
    def register_class(cls, class_name: str, class_ref: type):
        """Register a class for serialization purposes by adding it to the registry.

        Args:
            class_name: The name of the class to register.
            class_ref: A reference to the class being registered.
        """
        cls.registry[class_name] = class_ref

    @classmethod
    def get_class(cls, class_name: str):
        """Retrieve a class reference from the registry by its name.

        Args:
            class_name: The name of the class to retrieve.

        Returns:
            The class reference if found, None otherwise.
        """
        return cls.registry.get(class_name)


def check_serializable_constructability(obj: "Serializable") -> None:
    """Check if a Serializable object can be constructed without arguments.

    This function validates that the object's class can be instantiated
    without arguments, which is required for proper deserialization.

    Args:
        obj: Serializable object to check.

    Raises:
        TypeError: If the object's class cannot be initialized without arguments.
            This includes detailed information about which class failed and
            what parameters are required.
    """
    obj_class = type(obj)
    init_signature = inspect.signature(obj_class.__init__)
    parameters = init_signature.parameters.values()

    required_params = []
    for param in parameters:
        if (
            param.name != "self"
            and param.default == inspect.Parameter.empty
            and param.kind != inspect.Parameter.VAR_KEYWORD
            and param.kind != inspect.Parameter.VAR_POSITIONAL
        ):
            required_params.append(param.name)

    if required_params:
        error_message = (
            f"Serialization Error: {obj_class.__name__} cannot be deserialized because "
            f"its __init__ method requires parameters: {', '.join(required_params)}\n"
            f"Serializable classes must support initialization with no arguments.\n"
            f"For Routine subclasses, use _config dictionary instead of constructor parameters.\n"
            f"Example:\n"
            f"  # ❌ Wrong:\n"
            f"  class MyRoutine(Routine):\n"
            f"      def __init__(self, param1, param2):\n"
            f"          super().__init__()\n"
            f"          self.param1 = param1\n"
            f"\n"
            f"  # ✅ Correct:\n"
            f"  class MyRoutine(Routine):\n"
            f"      def __init__(self):\n"
            f"          super().__init__()\n"
            f"          # Set config after creation:\n"
            f"          # routine.set_config(param1=value1, param2=value2)"
        )
        raise TypeError(error_message)


def validate_serializable_tree(obj: "Serializable", visited: Optional[set] = None) -> None:
    """Recursively validate that all Serializable objects in a tree can be constructed.

    This function traverses all Serializable objects referenced by the given object
    and checks that each one can be instantiated without arguments. This is useful
    for validating a Flow before serialization to catch issues early.

    Args:
        obj: Root Serializable object to validate.
        visited: Set of object IDs already visited (to avoid infinite loops).

    Raises:
        TypeError: If any Serializable object in the tree cannot be constructed
            without arguments. The error message includes the path to the problematic
            object.
    """
    if visited is None:
        visited = set()

    # Use object ID to track visited objects (avoid infinite loops)
    obj_id = id(obj)
    if obj_id in visited:
        return
    visited.add(obj_id)

    # Check the object itself
    try:
        check_serializable_constructability(obj)
    except TypeError as e:
        # Enhance error message with object information
        obj_class = type(obj).__name__
        obj_repr = repr(obj) if hasattr(obj, "__repr__") else f"{obj_class} instance"
        raise TypeError(
            f"Found non-constructable Serializable object: {obj_repr}\n" f"{str(e)}"
        ) from e

    # Recursively check all Serializable fields
    if hasattr(obj, "fields_to_serialize"):
        for field_name in obj.fields_to_serialize:
            try:
                field_value = getattr(obj, field_name, None)
            except AttributeError:
                continue

            # Import Serializable here to avoid circular import
            # Use forward reference since we're in the same module
            SerializableClass = Serializable

            if isinstance(field_value, SerializableClass):
                try:
                    validate_serializable_tree(field_value, visited)
                except TypeError as e:
                    raise TypeError(
                        f"In field '{field_name}' of {type(obj).__name__}: {str(e)}"
                    ) from e
            elif isinstance(field_value, list):
                for i, item in enumerate(field_value):
                    if isinstance(item, SerializableClass):
                        try:
                            validate_serializable_tree(item, visited)
                        except TypeError as e:
                            raise TypeError(
                                f"In field '{field_name}[{i}]' of {type(obj).__name__}: {str(e)}"
                            ) from e
            elif isinstance(field_value, dict):
                for key, value in field_value.items():
                    if isinstance(value, SerializableClass):
                        try:
                            validate_serializable_tree(value, visited)
                        except TypeError as e:
                            raise TypeError(
                                f"In field '{field_name}[\"{key}\"]' of {type(obj).__name__}: {str(e)}"
                            ) from e


def register_serializable(cls):
    """Decorator to register a class as serializable in the registry.

    This decorator ensures that the class can be instantiated without arguments,
    which is required for proper deserialization. It validates that __init__
    either accepts no parameters (except self) or all parameters have default values.

    Args:
        cls: Class to be registered.

    Returns:
        The same class with registration completed.

    Raises:
        TypeError: If the class cannot be initialized without arguments.
            This happens when __init__ has required parameters (without defaults)
            other than 'self'. For Routine subclasses, use _config dictionary
            instead of constructor parameters.

    Note:
        For Routine subclasses, all configuration should be stored in _config
        dictionary and set after object creation, not passed as constructor
        parameters. This ensures proper serialization/deserialization support.
    """
    init_signature = inspect.signature(cls.__init__)
    parameters = init_signature.parameters.values()

    for param in parameters:
        if (
            param.name != "self"
            and param.default == inspect.Parameter.empty
            and param.kind != inspect.Parameter.VAR_KEYWORD
            and param.kind != inspect.Parameter.VAR_POSITIONAL
        ):
            error_message = (
                f"Error: {cls.__name__} cannot be initialized without parameters. "
                f"Serializable classes must support initialization with no arguments.\n"
                f"For Routine subclasses, use _config dictionary instead of constructor parameters.\n"
                f"Example: routine.set_config(key=value) or routine._config['key'] = value"
            )
            print(error_message)
            raise TypeError(error_message)
    SerializableRegistry.register_class(cls.__name__, cls)
    return cls


class Serializable:
    """A base class for objects that can be serialized and deserialized."""

    def __init__(self) -> None:
        """Initialize a serializable object with no specific fields."""
        self.fields_to_serialize = []


    def add_serializable_fields(self, fields: List[str]) -> None:
        """Add field names to the list that should be included in serialization.

        Args:
            fields: List of field names to be serialized.

        Raises:
            ValueError: If any provided field is not a string.
        """
        if not all(isinstance(field, str) for field in fields):
            raise ValueError("All fields must be strings")
        self.fields_to_serialize.extend(fields)
        self.fields_to_serialize = list(set(self.fields_to_serialize))

    def remove_serializable_fields(self, fields: List[str]) -> None:
        """Remove field names from the list that should be included in serialization.

        Args:
            fields: List of field names to be removed.
        """
        self.fields_to_serialize = [x for x in self.fields_to_serialize if x not in fields]

    def serialize(self) -> Dict[str, Any]:
        """Serialize the object to a dictionary.

        Automatically handles:
        - Serializable objects
        - Lists and dicts containing Serializable objects
        - Callable objects (functions, methods, builtins)
        - Lists and dicts containing callable objects

        Returns:
            Dictionary containing all serializable fields.
        """
        data = {"_type": type(self).__name__}
        for field in self.fields_to_serialize:
            value = getattr(self, field, None)
            if isinstance(value, Serializable):
                data[field] = value.serialize()
            elif isinstance(value, list):
                data[field] = [
                    self._serialize_value(item) for item in value
                ]
            elif isinstance(value, dict):
                data[field] = {
                    k: self._serialize_value(v) for k, v in value.items()
                }
            else:
                data[field] = self._serialize_value(value)
        return data

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a single value, handling callables automatically.
        
        Args:
            value: Value to serialize.
            
        Returns:
            Serialized value.
        """
        if isinstance(value, Serializable):
            return value.serialize()
        elif callable(value) and not isinstance(value, type):
            # Automatically serialize callables (functions, methods, etc.)
            # For methods, validate they belong to the object that owns this field
            # For functions, no validation needed
            owner = None
            if inspect.ismethod(value):
                # For methods, use the method's owner (the object the method belongs to)
                # This ensures we serialize the method correctly
                owner = value.__self__
            # Don't pass owner for functions - they're always serializable
            serialized = serialize_callable(value, owner=owner)
            if serialized is not None:
                return serialized
            # If serialization fails, return None (callable cannot be serialized)
            return None
        else:
            return value

    def deserialize(
        self, 
        data: Dict[str, Any], 
        strict: bool = False,
        registry: Optional[Any] = None
    ) -> None:
        """Deserialize the object from a dictionary, restoring its state.

        Automatically handles:
        - Serializable objects
        - Lists and dicts containing Serializable objects (with two-phase deserialization)
        - Callable objects (functions, methods, builtins)
        - Lists and dicts containing callable objects
        - Automatic ObjectRegistry creation and propagation for callable deserialization

        Args:
            data: Dictionary containing all serializable fields.
            strict: If True, raise error for unknown fields. If False, ignore them (default).
            registry: Optional ObjectRegistry for deserializing callables. If None,
                creates a new registry automatically.
        
        Raises:
            ValueError: If strict=True and unknown field is found, or if deserialization fails.
        """
        # Create registry if not provided (needed for callable deserialization)
        if registry is None:
            registry = ObjectRegistry()
        
        # Two-phase deserialization for containers (dict/list) containing Serializable objects:
        # Phase 1: Create all Serializable instances and register them in registry
        # Phase 2: Deserialize all instances (so callables can reference them)
        
        # Phase 1: Pre-create and register Serializable objects in containers
        pre_created = {}  # Track pre-created objects by field name
        unknown_fields = []
        
        for key, value in data.items():
            if key == "_type":
                continue
            
            # Validate field is in fields_to_serialize (security: prevent setting arbitrary attributes)
            if key not in self.fields_to_serialize:
                if strict:
                    unknown_fields.append(key)
                else:
                    # Silently ignore unknown fields for backward compatibility
                    continue
            
            # Phase 1: Pre-create Serializable objects in containers
            if isinstance(value, dict):
                # Check if it's a dict of Serializable objects (like routines: {id: data})
                if "_type" not in value:
                    # Regular dict - check if values are Serializable objects
                    pre_created[key] = {}
                    for k, v in value.items():
                        if isinstance(v, dict) and "_type" in v and v.get("_type") != "callable":
                            # Get class from registry
                            attr_class = SerializableRegistry.get_class(v["_type"])
                            
                            # If class not found, raise error
                            if attr_class is None:
                                raise ValueError(
                                    f"Cannot deserialize object of type '{v['_type']}' in field '{key}': "
                                    f"class not found in registry. "
                                    f"This usually means the class was not registered with @register_serializable."
                                )
                            
                            obj = attr_class()
                            # Register in registry if it has an _id or we can use the key
                            object_id = v.get("_id") or k
                            if hasattr(obj, "_id") or k:
                                registry.register(obj, object_id=object_id if isinstance(object_id, str) else k)
                            pre_created[key][k] = obj
            elif isinstance(value, list):
                # Check if it's a list of Serializable objects (like connections: [data, ...])
                pre_created[key] = []
                for i, item in enumerate(value):
                    if isinstance(item, dict) and "_type" in item and item.get("_type") != "callable":
                        attr_class = SerializableRegistry.get_class(item["_type"])
                        if attr_class is None:
                            raise ValueError(
                                f"Cannot deserialize object of type '{item['_type']}' in list field '{key}': "
                                f"class not found in registry. "
                                f"This usually means the class was not registered with @register_serializable."
                            )
                        obj = attr_class()
                        # Register in registry if it has an _id
                        object_id = item.get("_id")
                        if object_id or hasattr(obj, "_id"):
                            registry.register(obj, object_id=object_id)
                        pre_created[key].append(obj)
        
        # Phase 2: Deserialize all fields (including pre-created objects)
        for key, value in data.items():
            if key == "_type" or (strict and key not in self.fields_to_serialize):
                continue
            
            if key not in self.fields_to_serialize:
                continue
            
            try:
                if isinstance(value, dict):
                    if "_type" in value:
                        # Check if it's a callable serialization (callable or lambda_expression)
                        if value.get("_type") == "callable" or value.get("_type") == "lambda_expression":
                            attr = deserialize_callable(value, registry=registry)
                        else:
                            # Try to deserialize as Serializable object
                            attr_class = SerializableRegistry.get_class(value["_type"])
                            if attr_class is None:
                                raise ValueError(
                                    f"Cannot deserialize object of type '{value['_type']}' in field '{key}': "
                                    f"class not found in registry. "
                                    f"This usually means the class was not registered with @register_serializable."
                                )
                            attr: Serializable = attr_class()
                            # Check if deserialize accepts registry parameter
                            import inspect
                            deserialize_sig = inspect.signature(attr.deserialize)
                            if 'registry' in deserialize_sig.parameters:
                                attr.deserialize(value, registry=registry)
                            else:
                                attr.deserialize(value)
                    else:
                        # Regular dict - use pre-created objects if available
                        if key in pre_created:
                            attr = {}
                            for k, v in value.items():
                                if k in pre_created[key]:
                                    # Use pre-created object and deserialize it
                                    obj = pre_created[key][k]
                                    # Check if deserialize accepts registry parameter
                                    import inspect
                                    deserialize_sig = inspect.signature(obj.deserialize)
                                    if 'registry' in deserialize_sig.parameters:
                                        obj.deserialize(v, registry=registry)
                                    else:
                                        obj.deserialize(v)
                                    attr[k] = obj
                                else:
                                    # Not in pre_created - deserialize normally
                                    attr[k] = Serializable.deserialize_item(v, registry=registry)
                        else:
                            attr = {k: Serializable.deserialize_item(v, registry=registry) for k, v in value.items()}
                elif isinstance(value, list):
                    # List - use pre-created objects if available
                    if key in pre_created:
                        attr = []
                        for i, item in enumerate(value):
                            if i < len(pre_created[key]):
                                # Use pre-created object and deserialize it
                                obj = pre_created[key][i]
                                # Check if deserialize accepts registry parameter
                                import inspect
                                deserialize_sig = inspect.signature(obj.deserialize)
                                if 'registry' in deserialize_sig.parameters:
                                    obj.deserialize(item, registry=registry)
                                else:
                                    obj.deserialize(item)
                                attr.append(obj)
                            else:
                                # Not a Serializable object, deserialize normally
                                attr.append(Serializable.deserialize_item(item, registry=registry))
                    else:
                        attr = [Serializable.deserialize_item(item, registry=registry) for item in value]
                else:
                    attr = value
                setattr(self, key, attr)
            except Exception as e:
                raise ValueError(
                    f"Failed to deserialize field '{key}' of {type(self).__name__}: {str(e)}"
                ) from e
        
        if unknown_fields and strict:
            raise ValueError(
                f"Unknown fields in {type(self).__name__}: {', '.join(unknown_fields)}. "
                f"Expected fields: {', '.join(self.fields_to_serialize)}"
            )

    @staticmethod
    def deserialize_item(item: Any, registry: Optional[Any] = None) -> Any:
        """Deserialize an item (dict, list, or primitive type).

        Automatically handles callable deserialization.

        Args:
            item: Item to deserialize (can be dict, list, or primitive type).
            registry: Optional ObjectRegistry for deserializing callables.

        Returns:
            Deserialized item.
        """
        
        if isinstance(item, dict):
            if "_type" in item:
                # Check if it's a callable serialization (callable or lambda_expression)
                if item.get("_type") == "callable" or item.get("_type") == "lambda_expression":
                    return deserialize_callable(item, registry=registry)
                
                # Get class from registry
                attr_class = SerializableRegistry.get_class(item["_type"])
                
                # If class not found, raise error
                if attr_class is None:
                    raise ValueError(
                        f"Cannot deserialize object of type '{item['_type']}': "
                        f"class not found in registry. "
                        f"This usually means the class was not registered with @register_serializable."
                    )
                
                obj: Serializable = attr_class()
                # Check if deserialize accepts registry parameter
                import inspect
                deserialize_sig = inspect.signature(obj.deserialize)
                if 'registry' in deserialize_sig.parameters:
                    obj.deserialize(item, registry=registry)
                else:
                    obj.deserialize(item)
                return obj
            else:
                return {k: Serializable.deserialize_item(v, registry=registry) for k, v in item.items()}
        elif isinstance(item, list):
            # Fixed: variable name conflict (was: for item in item)
            return [Serializable.deserialize_item(sub_item, registry=registry) for sub_item in item]
        else:
            return item


# ============================================================================
# Callable Serialization Utilities
# ============================================================================

class ObjectRegistry:
    """Generic registry for looking up objects by ID and class name.
    
    This registry allows deserialization to find objects by their ID without
    hardcoding specific object types (like "routines"). It supports multiple
    lookup strategies:
    - By ID: Find object with matching _id attribute
    - By class name: Find objects of a specific class
    - Custom lookup: Register custom lookup functions
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._objects_by_id: Dict[str, Any] = {}
        self._objects_by_class: Dict[str, list] = {}
        self._custom_lookups: Dict[str, Callable[[str, str], Optional[Any]]] = {}
    
    def register(self, obj: Any, object_id: Optional[str] = None) -> None:
        """Register an object in the registry.
        
        Args:
            obj: Object to register.
            object_id: Optional ID to use. If None, uses obj._id if available.
        """
        if object_id is None:
            object_id = getattr(obj, "_id", None)
        
        if object_id:
            self._objects_by_id[object_id] = obj
        
        # Also register by class name
        class_name = obj.__class__.__name__
        if class_name not in self._objects_by_class:
            self._objects_by_class[class_name] = []
        if obj not in self._objects_by_class[class_name]:
            self._objects_by_class[class_name].append(obj)
    
    def register_many(self, objects: Dict[str, Any]) -> None:
        """Register multiple objects from a dictionary.
        
        Args:
            objects: Dictionary mapping IDs to objects.
        """
        for obj_id, obj in objects.items():
            self.register(obj, object_id=obj_id)
    
    def find_by_id(self, object_id: str) -> Optional[Any]:
        """Find an object by its ID.
        
        Args:
            object_id: Object ID to look up.
            
        Returns:
            Object if found, None otherwise.
        """
        return self._objects_by_id.get(object_id)
    
    def find_by_class_and_id(self, class_name: str, object_id: str) -> Optional[Any]:
        """Find an object by class name and ID.
        
        Args:
            class_name: Class name to filter by.
            object_id: Object ID to look up.
            
        Returns:
            Object if found, None otherwise.
        """
        # First try direct ID lookup
        obj = self._objects_by_id.get(object_id)
        if obj and obj.__class__.__name__ == class_name:
            return obj
        
        # Then try class-based lookup
        if class_name in self._objects_by_class:
            for obj in self._objects_by_class[class_name]:
                if hasattr(obj, "_id") and obj._id == object_id:
                    return obj
        
        # Try custom lookups
        if class_name in self._custom_lookups:
            return self._custom_lookups[class_name](class_name, object_id)
        
        return None
    
    def register_custom_lookup(self, class_name: str, lookup_func: Callable[[str, str], Optional[Any]]) -> None:
        """Register a custom lookup function for a specific class.
        
        Args:
            class_name: Class name to register lookup for.
            lookup_func: Function that takes (class_name, object_id) and returns object or None.
        """
        self._custom_lookups[class_name] = lookup_func
    
    def clear(self) -> None:
        """Clear all registered objects."""
        self._objects_by_id.clear()
        self._objects_by_class.clear()
        self._custom_lookups.clear()


def extract_callable_expression(source: str) -> Optional[str]:
    """Extract lambda expression or function body from source code.

    This function can extract expressions from both lambda functions and regular
    function definitions, making them suitable for serialization as lambda_expression.

    Args:
        source: Source code string (e.g., "f = lambda x: x.get('priority') == 'high'"
                or "def test_lambda(x):\n    return x.get('priority') == 'high'").

    Returns:
        Expression string (e.g., "x.get('priority') == 'high'"), or None if extraction fails.
    """
    source = source.strip()
    
    # Try lambda expression first
    lambda_pos = source.find("lambda")
    if lambda_pos != -1:
        # Find the colon after lambda
        colon_pos = source.find(":", lambda_pos)
        if colon_pos != -1:
            # Extract expression after colon
            expr = source[colon_pos + 1 :].strip()
            # Remove trailing comma or semicolon if present
            expr = expr.rstrip(",;")
            return expr
    
    # Try function definition
    if source.startswith("def "):
        # Find the colon after function signature
        colon_pos = source.find(":")
        if colon_pos != -1:
            # Extract function body
            body = source[colon_pos + 1 :].strip()
            # Remove leading/trailing whitespace and dedent
            lines = body.split("\n")
            if lines:
                # Find minimum indentation (excluding first line if it's empty)
                non_empty_lines = [line for line in lines if line.strip()]
                if non_empty_lines:
                    min_indent = min(len(line) - len(line.lstrip()) for line in non_empty_lines)
                    # Dedent all lines
                    dedented_lines = [line[min_indent:] if len(line) > min_indent else line for line in lines]
                    body = "\n".join(dedented_lines).strip()
                    
                    # If body starts with 'return', extract the expression
                    if body.startswith("return "):
                        expr = body[7:].strip()  # Remove "return "
                        # Remove trailing semicolon if present
                        expr = expr.rstrip(";")
                        return expr
                    # Otherwise, return the whole body as expression
                    return body
    
    return None


def serialize_callable_with_fallback(
    callable_obj: Optional[Callable], 
    owner: Optional[Any] = None,
    fallback_to_expression: bool = True
) -> Optional[Dict[str, Any]]:
    """Serialize a callable object with automatic fallback to expression extraction.

    This function tries standard serialization first (for module functions, methods, builtins).
    If that fails and fallback_to_expression is True, it attempts to extract the source code
    and serialize as lambda_expression.

    Args:
        callable_obj: Callable object to serialize.
        owner: Optional object that owns this callable. If provided and callable_obj
            is a method, validates that the method belongs to this owner object.
        fallback_to_expression: If True, attempt to extract source code as lambda_expression
            when standard serialization fails or function is not accessible from module level.

    Returns:
        Serialized dictionary, or None if serialization is not possible.

    Raises:
        ValueError: If serialization fails and fallback also fails, with detailed error message.
    """
    if callable_obj is None:
        return None

    # First, try standard serialization
    condition_data = serialize_callable(callable_obj, owner=owner)
    
    if condition_data:
        # Check if the function can be deserialized (i.e., accessible from module level)
        # For functions, verify they exist in the module
        if condition_data.get("callable_type") == "function":
            module_name = condition_data.get("module")
            function_name = condition_data.get("name")
            if module_name and function_name:
                try:
                    module = importlib.import_module(module_name)
                    if hasattr(module, function_name):
                        # Function is accessible from module level - use standard serialization
                        return condition_data
                    # Function not accessible from module level - try expression extraction
                except Exception:
                    # Module cannot be imported - try expression extraction
                    pass
        else:
            # Method or builtin - use standard serialization
            return condition_data
    
    # If standard serialization failed or function not accessible, try expression extraction
    if fallback_to_expression:
        if callable_obj.__name__ == "<lambda>" or (condition_data and condition_data.get("callable_type") == "function"):
            try:
                source = inspect.getsource(callable_obj)
                expr = extract_callable_expression(source)
                if expr:
                    return {
                        "_type": "lambda_expression",
                        "expression": expr,
                    }
                else:
                    # Expression extraction failed
                    raise ValueError(
                        f"Callable '{callable_obj.__name__}' cannot be serialized: "
                        f"failed to extract expression from source code. "
                        f"Consider using a module-level function or string expression instead."
                    )
            except (OSError, TypeError) as e:
                # Cannot get source (e.g., dynamically created lambda, no source file)
                raise ValueError(
                    f"Callable '{callable_obj.__name__}' cannot be serialized: "
                    f"cannot access source code ({type(e).__name__}: {e}). "
                    f"Callables defined at runtime or in interactive shells cannot be serialized. "
                    f"Consider using a module-level function or string expression instead."
                ) from e
            except Exception as e:
                # Other unexpected errors
                raise ValueError(
                    f"Callable '{callable_obj.__name__}' cannot be serialized: "
                    f"unexpected error during source code extraction ({type(e).__name__}: {e}). "
                    f"Consider using a module-level function or string expression instead."
                ) from e
    
    # If we get here and condition_data exists, it means function serialization succeeded
    # but function is not accessible - this shouldn't happen, but handle it
    if condition_data:
        return condition_data
    
    # No serialization method worked
    raise ValueError(
        f"Callable '{callable_obj.__name__}' cannot be serialized: "
        f"not a module-level function, method, builtin, or extractable lambda/function. "
        f"Consider using a module-level function or string expression instead."
    )


def serialize_callable(
    callable_obj: Optional[Callable], owner: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Serialize a callable object (function or method).

    Args:
        callable_obj: Callable object to serialize.
        owner: Optional object that owns this callable. If provided and callable_obj
            is a method, validates that the method belongs to this owner object.
            This ensures that only methods of the serialized object itself can be
            serialized, which is required for cross-process deserialization.

    Returns:
        Serialized dictionary, or None if serialization is not possible or
        validation fails.

    Raises:
        ValueError: If owner is provided and callable_obj is a method that doesn't
            belong to the owner object.
    """
    if callable_obj is None:
        return None

    try:
        # Try to get function information
        if inspect.ismethod(callable_obj):
            # Method - validate it belongs to owner if owner is provided
            method_owner = callable_obj.__self__
            
            if owner is not None:
                # Validate that the method belongs to the owner object
                # This ensures cross-process serialization safety
                if method_owner is not owner:
                    raise ValueError(
                        f"Cannot serialize method '{callable_obj.__name__}' from "
                        f"{method_owner.__class__.__name__}[{getattr(method_owner, '_id', 'unknown')}]. "
                        f"Only methods of the serialized object itself "
                        f"({owner.__class__.__name__}[{getattr(owner, '_id', 'unknown')}]) "
                        f"can be serialized for cross-process execution."
                    )
            
            return {
                "_type": "callable",
                "callable_type": "method",
                "class_name": callable_obj.__self__.__class__.__name__,
                "method_name": callable_obj.__name__,
                "object_id": getattr(callable_obj.__self__, "_id", None),
            }
        elif inspect.isfunction(callable_obj):
            # Function - no validation needed, functions are always serializable
            module = inspect.getmodule(callable_obj)
            if module:
                return {
                    "_type": "callable",
                    "callable_type": "function",
                    "module": module.__name__,
                    "name": callable_obj.__name__,
                }
        elif inspect.isbuiltin(callable_obj):
            # Builtin function - no validation needed
            return {
                "_type": "callable",
                "callable_type": "builtin",
                "name": callable_obj.__name__,
            }
    except ValueError:
        # Re-raise ValueError (validation errors)
        raise
    except Exception:
        # Other exceptions are silently ignored
        pass

    return None


def deserialize_callable(
    callable_data: Optional[Dict[str, Any]], 
    registry: Optional[ObjectRegistry] = None,
    context: Optional[Dict[str, Any]] = None
) -> Optional[Callable]:
    """Deserialize a callable object using a generic object registry.

    Args:
        callable_data: Serialized callable object data.
        registry: Optional ObjectRegistry for looking up objects by ID.
            If provided, uses this registry to find method owners.
        context: Optional context dictionary for backward compatibility.
            If registry is not provided, falls back to context-based lookup.
            Context can contain:
            - "routines": Dict mapping IDs to Routine objects (legacy support)
            - "registry": ObjectRegistry instance
            - Any other object collections

    Returns:
        Callable object, or None if deserialization is not possible.
    """
    if callable_data is None:
        return None

    # Determine if this is a callable serialization
    # Support both new format (_type="callable", callable_type="method"/"function"/"builtin")
    # and legacy format (_type="method"/"function"/"builtin" directly)
    # Also support lambda_expression format
    if callable_data.get("_type") == "lambda_expression":
        return deserialize_lambda_expression(callable_data)
    
    if callable_data.get("_type") == "callable":
        callable_type = callable_data.get("callable_type")
    else:
        # Legacy format support: _type directly indicates callable type
        callable_type = callable_data.get("_type")
        # Only treat as callable if it's a known callable type
        if callable_type not in ["method", "function", "builtin"]:
            return None

    # Get registry from context if not provided
    if registry is None and context:
        registry = context.get("registry")
        # Legacy support: create registry from "routines" if present
        if registry is None and "routines" in context:
            registry = ObjectRegistry()
            registry.register_many(context["routines"])

    try:
        if callable_type == "method":
            # Restore method using registry
            method_name = callable_data.get("method_name")
            object_id = callable_data.get("object_id")
            class_name = callable_data.get("class_name")

            if object_id and registry:
                # Find object from registry
                if class_name:
                    obj = registry.find_by_class_and_id(class_name, object_id)
                else:
                    obj = registry.find_by_id(object_id)
                
                if obj and hasattr(obj, method_name):
                    return getattr(obj, method_name)

        elif callable_type == "function":
            # Restore function
            module_name = callable_data.get("module")
            function_name = callable_data.get("name")

            if module_name and function_name:
                module = importlib.import_module(module_name)
                if hasattr(module, function_name):
                    return getattr(module, function_name)

        elif callable_type == "builtin":
            # Builtin function
            name = callable_data.get("name")
            if name:
                return __builtins__.get(name)

    except Exception:
        pass

    return None


def deserialize_lambda_expression(
    expression_data: Dict[str, Any],
    default_param_name: str = "data"
) -> Optional[Callable]:
    """Deserialize a lambda expression from serialized data.

    Args:
        expression_data: Dictionary containing "_type": "lambda_expression" and "expression".
        default_param_name: Default parameter name for the lambda (default: "data").

    Returns:
        Callable lambda function, or None if deserialization fails.

    Raises:
        ValueError: If deserialization fails with detailed error message.
    """
    if expression_data.get("_type") != "lambda_expression":
        return None
    
    expr = expression_data.get("expression")
    if not expr:
        raise ValueError(
            f"Failed to deserialize lambda expression: "
            f"missing 'expression' field in lambda_expression data."
        )
    
    try:
        import re as re_module

        # Remove 'return' keyword if present (for function bodies converted to lambda)
        expr = expr.strip()
        if expr.startswith("return "):
            expr = expr[7:].strip()  # Remove "return "
        
        # Replace common lambda parameter names with default_param_name
        # Pattern: word boundary + common param names + word boundary
        expr = re_module.sub(rf"\b(x|item|value|obj)\b", default_param_name, expr)

        # Safe evaluation to restore lambda
        safe_globals = {
            "__builtins__": {
                "isinstance": isinstance,
                "dict": dict,
                "list": list,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
            }
        }
        condition = eval(f"lambda {default_param_name}: {expr}", safe_globals)
        return condition
    except SyntaxError as e:
        raise ValueError(
            f"Failed to deserialize lambda expression: "
            f"syntax error in lambda expression '{expr}' ({type(e).__name__}: {e}). "
            f"The lambda expression may contain unsupported syntax or operations."
        ) from e
    except Exception as e:
        raise ValueError(
            f"Failed to deserialize lambda expression: "
            f"error evaluating lambda expression '{expr}' ({type(e).__name__}: {e})."
        ) from e


