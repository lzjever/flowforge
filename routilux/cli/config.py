"""Configuration file support for routilux CLI.

This module provides configuration loading from multiple file formats
(TOML, YAML, JSON) with automatic discovery and merging.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ConfigLoader:
    """Load and merge configuration from multiple sources.

    Supports automatic discovery of configuration files and loading
    from TOML, YAML, and JSON formats.

    Example:
        >>> loader = ConfigLoader()
        >>> config = loader.load()
        >>> print(config.get("server", {}).get("port", 8080))
    """

    DEFAULT_CONFIG_NAMES = ["routilux.toml", "pyproject.toml"]

    def __init__(self):
        """Initialize the configuration loader."""
        self._config: dict[str, Any] = {}

    def load(self, config_path: Path | None = None) -> dict[str, Any]:
        """Load configuration from file.

        Args:
            config_path: Explicit config path, or None to auto-discover

        Returns:
            Merged configuration dictionary
        """
        if config_path:
            return self._load_file(config_path)

        # Auto-discover
        for name in self.DEFAULT_CONFIG_NAMES:
            path = Path.cwd() / name
            if path.exists():
                return self._load_file(path)

        return {}

    def _load_file(self, path: Path) -> dict[str, Any]:
        """Load configuration from a specific file.

        Args:
            path: Path to configuration file

        Returns:
            Configuration dictionary

        Raises:
            ValueError: If file format is unsupported
        """
        if path.suffix == ".toml":
            return self._load_toml(path)
        elif path.suffix in (".yaml", ".yml"):
            return self._load_yaml(path)
        elif path.suffix == ".json":
            return self._load_json(path)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")

    def _load_toml(self, path: Path) -> dict[str, Any]:
        """Load TOML configuration.

        Args:
            path: Path to TOML file

        Returns:
            Configuration dictionary
        """
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(path, "rb") as f:
            data = tomllib.load(f)

        # Handle pyproject.toml format
        if "tool" in data and "routilux" in data["tool"]:
            return data["tool"]["routilux"]
        return data.get("routilux", data)

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        """Load YAML configuration.

        Args:
            path: Path to YAML file

        Returns:
            Configuration dictionary
        """
        import yaml

        content = path.read_text()
        return yaml.safe_load(content) or {}

    def _load_json(self, path: Path) -> dict[str, Any]:
        """Load JSON configuration.

        Args:
            path: Path to JSON file

        Returns:
            Configuration dictionary
        """
        import json

        content = path.read_text()
        return json.loads(content)

    def merge_with_cli(self, config: dict, cli_options: dict) -> dict:
        """Merge configuration with CLI options.

        CLI options take precedence over config file values.

        Args:
            config: Configuration from file
            cli_options: Options from CLI

        Returns:
            Merged options
        """
        result = config.copy()
        for key, value in cli_options.items():
            if value is not None:
                result[key] = value
        return result


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Convenience function to load configuration.

    Args:
        config_path: Explicit config path, or None to auto-discover

    Returns:
        Configuration dictionary
    """
    loader = ConfigLoader()
    return loader.load(config_path)


def get_config_value(config: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Get a nested value from configuration.

    Args:
        config: Configuration dictionary
        *keys: Nested keys to traverse
        default: Default value if key not found

    Returns:
        Configuration value or default

    Example:
        >>> config = {"server": {"port": 8080}}
        >>> get_config_value(config, "server", "port")
        8080
    """
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value
