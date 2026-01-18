"""
DSL loader for creating Flow objects from specifications.
"""

from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from routilux.flow.flow import Flow


def load_flow_from_spec(spec: Dict[str, Any]) -> "Flow":
    """Create Flow from specification dictionary.

    **DEPRECATED**: This function now delegates to ObjectFactory.load_flow_from_dsl().
    Use ObjectFactory.load_flow_from_dsl() directly for new code.

    This function is kept for backward compatibility but all DSL loading now goes
    through the factory to enforce factory-only component usage.

    Args:
        spec: Flow specification dictionary with structure:
            {
                "flow_id": "optional_flow_id",
                "routines": {
                    "routine_id": {
                        "class": "factory_name",  # Must be factory name, not class path
                        "config": {...},
                        "error_handler": {...}
                    }
                },
                "connections": [
                    {"from": "r1.output", "to": "r2.input"}
                ],
                "execution": {
                    "timeout": 300.0
                }
            }

    Returns:
        Constructed Flow object.

    Raises:
        ValueError: If DSL references unregistered components or is invalid.
    """
    from routilux.tools.factory.factory import ObjectFactory

    factory = ObjectFactory.get_instance()
    return factory.load_flow_from_dsl(spec)
