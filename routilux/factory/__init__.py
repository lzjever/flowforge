"""
Object Factory module for Routilux.

Provides a global factory for creating Flow and Routine objects from registered prototypes.
"""

from routilux.factory.factory import ObjectFactory
from routilux.factory.metadata import ObjectMetadata

__all__ = ["ObjectFactory", "ObjectMetadata"]
