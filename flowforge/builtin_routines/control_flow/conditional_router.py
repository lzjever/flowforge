"""
Conditional router routine.

Routes data to different outputs based on conditions.
"""
from __future__ import annotations
from typing import Dict, Any, Callable, Optional, List, Tuple, Union
from flowforge.routine import Routine


class ConditionalRouter(Routine):
    """Routine for routing data based on conditions.
    
    This routine evaluates conditions on input data and routes it to
    different output events based on which conditions are met.
    
    Features:
    - Multiple conditional routes
    - Configurable condition functions
    - Default route for unmatched cases
    - Priority-based routing
    
    Examples:
        >>> router = ConditionalRouter()
        >>> router.set_config(
        ...     routes=[
        ...         ("high_priority", lambda x: x.get("priority") == "high"),
        ...         ("low_priority", lambda x: x.get("priority") == "low"),
        ...     ],
        ...     default_route="normal"
        ... )
        >>> router.define_slot("input", handler=router.route)
        >>> router.define_event("high_priority", ["data"])
        >>> router.define_event("low_priority", ["data"])
        >>> router.define_event("normal", ["data"])
    """
    
    def __init__(self):
        """Initialize ConditionalRouter routine."""
        super().__init__()
        
        # Set default configuration
        self.set_config(
            routes=[],  # List of (route_name, condition_func) tuples
            default_route=None,  # Default route name if no condition matches
            route_priority="first_match"  # "first_match" or "all_matches"
        )
        
        # Define input slot
        self.input_slot = self.define_slot("input", handler=self._handle_input)
        
        # Default output event (will be created dynamically)
        self.default_output = self.define_event("output", ["data", "route"])
    
    def _handle_input(self, data: Any = None, **kwargs):
        """Handle input data and route it.
        
        Args:
            data: Data to route.
            **kwargs: Additional data from slot. If 'data' is not provided,
                will use kwargs or the first value.
        """
        # Extract data using Routine helper method
        data = self._extract_input_data(data, **kwargs)
        
        # Track statistics
        self._track_operation("routes")
        
        routes = self.get_config("routes", [])
        default_route = self.get_config("default_route", None)
        route_priority = self.get_config("route_priority", "first_match")
        
        matched_routes = []
        
        # Evaluate conditions
        for route_name, condition in routes:
            try:
                if callable(condition):
                    if condition(data):
                        matched_routes.append(route_name)
                        if route_priority == "first_match":
                            break
                elif isinstance(condition, dict):
                    # Dictionary-based condition (field matching)
                    if self._evaluate_dict_condition(data, condition):
                        matched_routes.append(route_name)
                        if route_priority == "first_match":
                            break
            except Exception as e:
                self._track_operation("routes", success=False, route=route_name, error=str(e))
        
        # Route data
        if matched_routes:
            for route_name in matched_routes:
                # Get or create event for this route
                event = self.get_event(route_name)
                if event is None:
                    event = self.define_event(route_name, ["data", "route"])
                
                self.emit(route_name,
                    data=data,
                    route=route_name
                )
                self.increment_stat(f"routes_to_{route_name}")
        else:
            # Use default route
            if default_route:
                event = self.get_event(default_route)
                if event is None:
                    event = self.define_event(default_route, ["data", "route"])
                self.emit(default_route,
                    data=data,
                    route=default_route
                )
                self.increment_stat(f"routes_to_{default_route}")
            else:
                # Emit to default output
                self.emit("output",
                    data=data,
                    route="unmatched"
                )
                self.increment_stat("unmatched_routes")
    
    def _evaluate_dict_condition(self, data: Any, condition: Dict[str, Any]) -> bool:
        """Evaluate a dictionary-based condition.
        
        Args:
            data: Data to evaluate.
            condition: Condition dictionary with field -> expected_value mappings.
        
        Returns:
            True if condition matches, False otherwise.
        """
        if not isinstance(data, dict):
            return False
        
        for field, expected_value in condition.items():
            if field not in data:
                return False
            
            actual_value = data[field]
            
            # Support callable expected values (custom comparison)
            if callable(expected_value):
                if not expected_value(actual_value):
                    return False
            elif actual_value != expected_value:
                return False
        
        return True
    
    def add_route(self, route_name: str, condition: Union[Callable, Dict[str, Any]]) -> None:
        """Add a routing condition.
        
        Args:
            route_name: Name of the route (will be used as event name).
            condition: Condition function or dictionary.
        """
        routes = self.get_config("routes", [])
        routes.append((route_name, condition))
        self.set_config(routes=routes)
        
        # Pre-create event for this route
        if self.get_event(route_name) is None:
            self.define_event(route_name, ["data", "route"])

