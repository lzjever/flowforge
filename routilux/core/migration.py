"""Migration framework for Flow serialization version management.

This module provides a framework for migrating Flow serialization data
between different versions of the serialization format.

The MigrationRegistry allows registration of migration functions that
can convert serialized data from one version to another.
"""

from __future__ import annotations

from typing import Any, Callable


class MigrationRegistry:
    """Registry for Flow serialization migration functions.

    Migration functions are registered to handle conversion between
    different versions of the Flow serialization format.

    Each migration function has the signature:
        (data: dict[str, Any]) -> dict[str, Any]

    The function takes the serialized data dictionary and returns
    the migrated dictionary with the version field updated.

    Examples:
        >>> def migrate_v1_to_v2(data):
        ...     # Add new field with default value
        ...     data["new_field"] = "default"
        ...     return data
        ...
        >>> registry = MigrationRegistry()
        >>> registry.register_migration(1, 2, migrate_v1_to_v2)
    """

    _instance: MigrationRegistry | None = None

    def __init__(self) -> None:
        """Initialize MigrationRegistry."""
        self._migrations: dict[tuple[int, int], Callable[[dict[str, Any]], dict[str, Any]]] = {}

    @classmethod
    def get_instance(cls) -> MigrationRegistry:
        """Get the singleton instance of MigrationRegistry.

        Returns:
            The singleton MigrationRegistry instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None

    def register_migration(
        self,
        from_version: int,
        to_version: int,
        migration_func: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Register a migration function.

        Args:
            from_version: Source version number
            to_version: Target version number
            migration_func: Function that migrates data from from_version to to_version

        Raises:
            ValueError: If from_version >= to_version or migration already registered
        """
        if from_version >= to_version:
            raise ValueError(
                f"from_version ({from_version}) must be less than to_version ({to_version})"
            )

        key = (from_version, to_version)
        if key in self._migrations:
            raise ValueError(f"Migration from {from_version} to {to_version} already registered")

        self._migrations[key] = migration_func

    def get_migration(
        self, from_version: int, to_version: int
    ) -> Callable[[dict[str, Any]], dict[str, Any]] | None:
        """Get a migration function.

        Args:
            from_version: Source version number
            to_version: Target version number

        Returns:
            Migration function or None if not found
        """
        return self._migrations.get((from_version, to_version))

    def has_migration(self, from_version: int, to_version: int) -> bool:
        """Check if a migration function exists.

        Args:
            from_version: Source version number
            to_version: Target version number

        Returns:
            True if migration exists, False otherwise
        """
        return (from_version, to_version) in self._migrations

    def migrate(self, data: dict[str, Any], target_version: int) -> dict[str, Any]:
        """Migrate serialized data to a target version.

        This method will apply migrations step-by-step if no direct
        migration exists.

        Args:
            data: Serialized data dictionary (must have 'version' key)
            target_version: Target version number

        Returns:
            Migrated data dictionary

        Raises:
            ValueError: If version information is missing or migration path not found
        """
        if "version" not in data:
            raise ValueError("Serialized data must contain 'version' field for migration")

        current_version = data["version"]

        if current_version == target_version:
            return data

        if current_version < target_version:
            return self._migrate_forward(data, current_version, target_version)
        else:
            return self._migrate_backward(data, current_version, target_version)

    def _migrate_forward(
        self, data: dict[str, Any], from_version: int, to_version: int
    ) -> dict[str, Any]:
        """Migrate data forward (upgrade) through versions.

        Args:
            data: Serialized data dictionary
            from_version: Starting version
            to_version: Target version

        Returns:
            Migrated data dictionary

        Raises:
            ValueError: If migration path not found
        """
        current_data = data
        current_v = from_version

        while current_v < to_version:
            # Try direct migration
            migration = self.get_migration(current_v, current_v + 1)
            if migration is None:
                raise ValueError(
                    f"No migration path from version {from_version} to {to_version}. "
                    f"Missing migration from {current_v} to {current_v + 1}"
                )

            current_data = migration(current_data)
            current_data["version"] = current_v + 1
            current_v += 1

        return current_data

    def _migrate_backward(
        self, data: dict[str, Any], from_version: int, to_version: int
    ) -> dict[str, Any]:
        """Migrate data backward (downgrade) through versions.

        Args:
            data: Serialized data dictionary
            from_version: Starting version
            to_version: Target version

        Returns:
            Migrated data dictionary

        Raises:
            ValueError: If migration path not found
        """
        current_data = data
        current_v = from_version

        while current_v > to_version:
            # Try direct migration
            migration = self.get_migration(current_v, current_v - 1)
            if migration is None:
                raise ValueError(
                    f"No migration path from version {from_version} to {to_version}. "
                    f"Missing migration from {current_v} to {current_v - 1}"
                )

            current_data = migration(current_data)
            current_data["version"] = current_v - 1
            current_v -= 1

        return current_data

    def get_supported_versions(self) -> set[int]:
        """Get all versions that have registered migrations.

        Returns:
            Set of version numbers
        """
        versions = set()
        for from_v, to_v in self._migrations.keys():
            versions.add(from_v)
            versions.add(to_v)
        return versions

    def clear(self) -> None:
        """Clear all registered migrations (useful for testing)."""
        self._migrations.clear()


def get_migration_registry() -> MigrationRegistry:
    """Get the singleton MigrationRegistry instance.

    Returns:
        The MigrationRegistry instance
    """
    return MigrationRegistry.get_instance()


def reset_migration_registry() -> None:
    """Reset the singleton MigrationRegistry instance (useful for testing)."""
    MigrationRegistry.reset_instance()


__all__ = [
    "MigrationRegistry",
    "get_migration_registry",
    "reset_migration_registry",
]
