"""
Object Factory module for Routilux.

Provides a global factory for creating Flow and Routine objects from registered prototypes.
"""

from routilux.tools.factory.factory import ObjectFactory
from routilux.tools.factory.metadata import ObjectMetadata

__all__ = ["ObjectFactory", "ObjectMetadata"]
