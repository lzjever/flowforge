"""
Global Object Factory for creating Flow and Routine objects from prototypes.
"""

import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union

from routilux.factory.metadata import ObjectMetadata

if TYPE_CHECKING:
    from routilux.error_handler import ErrorHandler
    from routilux.flow.flow import Flow
    from routilux.routine import Routine


class ObjectFactory:
    """Global factory for creating objects from registered prototypes.

    Supports both class-based and instance-based prototypes:
    - Class prototypes: Store the class, create new instances on demand
    - Instance prototypes: Store class + config/policy/logic, clone on demand

    Thread-safe singleton pattern.

    Examples:
        Register a class prototype:
            >>> factory = ObjectFactory.get_instance()
            >>> factory.register("data_processor", DataProcessor, description="Processes data")

        Register an instance prototype:
            >>> base = DataProcessor()
            >>> base.set_config(timeout=30)
            >>> base.set_activation_policy(immediate_policy())
            >>> factory.register("fast_processor", base, description="Fast processing")

        Create objects:
            >>> routine = factory.create("data_processor")
            >>> routine = factory.create("fast_processor", config={"timeout": 60})
    """

    _instance: Optional["ObjectFactory"] = None
    _lock = threading.Lock()

    def __init__(self):
        """Initialize factory (private - use get_instance())."""
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._registry_lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "ObjectFactory":
        """Get the global factory instance (singleton).

        Returns:
            ObjectFactory instance.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def register(
        self,
        name: str,
        prototype: Union[Type, Any],
        description: str = "",
        metadata: Optional[ObjectMetadata] = None,
    ) -> None:
        """Register a prototype (class or instance).

        Args:
            name: Unique name for the prototype.
            prototype: Class or instance to register.
            description: Human-readable description.
            metadata: Optional ObjectMetadata object. If provided, overrides description.

        Raises:
            ValueError: If name is already registered or prototype is invalid.
        """
        with self._registry_lock:
            if name in self._registry:
                raise ValueError(f"Prototype '{name}' is already registered")

            # Validate prototype is not None
            if prototype is None:
                raise ValueError("Prototype cannot be None")

            # Determine if prototype is a class or instance
            if isinstance(prototype, type):
                # Class prototype
                self._registry[name] = {
                    "type": "class",
                    "prototype": prototype,
                    "config": {},
                    "activation_policy": None,
                    "logic": None,
                    "error_handler": None,
                    "metadata": metadata or ObjectMetadata(name=name, description=description),
                }
            else:
                # Instance prototype - extract class and configuration
                prototype_class = prototype.__class__

                # Check if it's a Flow - Flows need special handling (clone routines/connections)
                from routilux.flow.flow import Flow

                if isinstance(prototype, Flow):
                    # For Flow instances, store the original instance for cloning
                    # We'll clone it when creating new instances
                    # Note: Flow doesn't have _config like Routine, so we don't extract it
                    self._registry[name] = {
                        "type": "instance",
                        "prototype": prototype_class,
                        "original_instance": prototype,  # Store original for cloning
                        "config": {},  # Flow doesn't use _config
                        "activation_policy": None,
                        "logic": None,
                        "error_handler": getattr(prototype, "error_handler", None),
                        "metadata": metadata or ObjectMetadata(name=name, description=description),
                    }
                else:
                    # Routine instance - extract config, policy, logic, slots, events
                    config = getattr(prototype, "_config", {}).copy()
                    activation_policy = getattr(prototype, "_activation_policy", None)
                    logic = getattr(prototype, "_logic", None)
                    error_handler = getattr(prototype, "_error_handler", None)
                    # Preserve slots and events for cloning
                    slots = getattr(prototype, "_slots", {}).copy()
                    events = getattr(prototype, "_events", {}).copy()

                    self._registry[name] = {
                        "type": "instance",
                        "prototype": prototype_class,
                        "config": config,
                        "activation_policy": activation_policy,
                        "logic": logic,
                        "error_handler": error_handler,
                        "slots": slots,
                        "events": events,
                        "metadata": metadata or ObjectMetadata(name=name, description=description),
                    }

    def create(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None,
        override_policy: Optional[Callable] = None,
        override_logic: Optional[Callable] = None,
    ) -> Any:
        """Create an object from a registered prototype.

        Args:
            name: Name of the registered prototype.
            config: Optional configuration dictionary to merge with prototype config.
            override_policy: Optional activation policy to override prototype policy.
            override_logic: Optional logic function to override prototype logic.

        Returns:
            New object instance (Routine or Flow).

        Raises:
            ValueError: If prototype is not found.
        """
        with self._registry_lock:
            if name not in self._registry:
                raise ValueError(f"Prototype '{name}' not found. Available: {list(self._registry.keys())}")

            proto = self._registry[name]
            proto_class = proto["prototype"]

            # Create instance based on prototype type
            if proto["type"] == "instance":
                # Check if we have an original Flow instance to clone
                if "original_instance" in proto:
                    # Flow instance prototype - clone it
                    from routilux.factory.cloning import clone_flow

                    original_flow = proto["original_instance"]
                    instance = clone_flow(original_flow)
                else:
                    # Routine instance - create new and apply config
                    instance = proto_class()
                    instance._config = proto["config"].copy()

                    # Clone slots from prototype
                    if "slots" in proto:
                        for slot_name, slot in proto["slots"].items():
                            # Clone slot by redefining it with same parameters
                            from routilux.slot import Slot
                            cloned_slot = Slot(
                                slot.name,
                                instance,
                                max_queue_length=slot.max_queue_length,
                                watermark=slot.watermark,
                            )
                            instance._slots[slot_name] = cloned_slot

                    # Clone events from prototype
                    if "events" in proto:
                        for event_name, event in proto["events"].items():
                            # Clone event by redefining it with same parameters
                            from routilux.event import Event
                            cloned_event = Event(
                                event.name,
                                instance,
                                output_params=event.output_params.copy() if event.output_params else None,
                            )
                            instance._events[event_name] = cloned_event

                    # Apply prototype policy/logic if not overridden
                    if override_policy is None and proto.get("activation_policy"):
                        instance.set_activation_policy(proto["activation_policy"])
                    if override_logic is None and proto.get("logic"):
                        instance.set_logic(proto["logic"])
                    if proto.get("error_handler"):
                        instance.set_error_handler(proto["error_handler"])
            else:
                # Class prototype - just create instance
                instance = proto_class()

            # Merge override config (overrides prototype config)
            # Note: Flow doesn't have set_config, only Routine does
            if config and hasattr(instance, "set_config"):
                instance.set_config(**config)

            # Apply overrides (only for Routine)
            if override_policy and hasattr(instance, "set_activation_policy"):
                instance.set_activation_policy(override_policy)
            if override_logic and hasattr(instance, "set_logic"):
                instance.set_logic(override_logic)

            return instance

    def list_available(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available prototypes.

        Args:
            category: Optional category filter.

        Returns:
            List of dictionaries with prototype information.
        """
        with self._registry_lock:
            results = []
            for name, proto in self._registry.items():
                metadata = proto.get("metadata", ObjectMetadata(name=name))
                if category and metadata.category != category:
                    continue

                results.append(
                    {
                        "name": name,
                        "type": proto["type"],
                        "description": metadata.description,
                        "category": metadata.category,
                        "tags": metadata.tags,
                        "example_config": metadata.example_config,
                        "version": metadata.version,
                    }
                )
            return results

    def get_metadata(self, name: str) -> Optional[ObjectMetadata]:
        """Get metadata for a registered prototype.

        Args:
            name: Prototype name.

        Returns:
            ObjectMetadata or None if not found.
        """
        with self._registry_lock:
            if name not in self._registry:
                return None
            return self._registry[name].get("metadata")

    def unregister(self, name: str) -> None:
        """Unregister a prototype.

        Args:
            name: Prototype name to unregister.

        Raises:
            ValueError: If prototype is not found.
        """
        with self._registry_lock:
            if name not in self._registry:
                raise ValueError(f"Prototype '{name}' not found")
            del self._registry[name]

    def clear(self) -> None:
        """Clear all registered prototypes."""
        with self._registry_lock:
            self._registry.clear()
