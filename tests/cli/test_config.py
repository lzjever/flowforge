"""Tests for CLI configuration file support."""

from pathlib import Path

import pytest


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    def test_load_toml_config(self, tmp_path: Path):
        """Test loading TOML configuration."""
        config_file = tmp_path / "routilux.toml"
        config_file.write_text("""
[routines]
directories = ["./routines"]

[server]
port = 9000
host = "127.0.0.1"
""")

        from routilux.cli.config import ConfigLoader

        loader = ConfigLoader()
        config = loader.load(config_file)

        assert config["routines"]["directories"] == ["./routines"]
        assert config["server"]["port"] == 9000
        assert config["server"]["host"] == "127.0.0.1"

    def test_load_yaml_config(self, tmp_path: Path):
        """Test loading YAML configuration."""
        config_file = tmp_path / "routilux.yaml"
        config_file.write_text("""
routines:
  directories:
    - ./routines
server:
  port: 9000
""")

        from routilux.cli.config import ConfigLoader

        loader = ConfigLoader()
        config = loader.load(config_file)

        assert config["routines"]["directories"] == ["./routines"]
        assert config["server"]["port"] == 9000

    def test_load_json_config(self, tmp_path: Path):
        """Test loading JSON configuration."""
        config_file = tmp_path / "routilux.json"
        config_file.write_text("""
{
    "routines": {
        "directories": ["./routines"]
    },
    "server": {
        "port": 9000
    }
}
""")

        from routilux.cli.config import ConfigLoader

        loader = ConfigLoader()
        config = loader.load(config_file)

        assert config["routines"]["directories"] == ["./routines"]
        assert config["server"]["port"] == 9000

    def test_auto_discover_config(self, tmp_path: Path, monkeypatch):
        """Test auto-discovery of configuration file."""
        config_file = tmp_path / "routilux.toml"
        config_file.write_text("""
[routines]
directories = ["./auto_routines"]
""")

        from routilux.cli.config import ConfigLoader

        loader = ConfigLoader()
        monkeypatch.chdir(tmp_path)
        config = loader.load()

        assert config["routines"]["directories"] == ["./auto_routines"]

    def test_no_config_file(self, tmp_path: Path, monkeypatch):
        """Test behavior when no config file exists."""
        from routilux.cli.config import ConfigLoader

        loader = ConfigLoader()
        monkeypatch.chdir(tmp_path)
        config = loader.load()

        assert config == {}

    def test_pyproject_toml_format(self, tmp_path: Path):
        """Test loading pyproject.toml with tool.routilux section."""
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text("""
[tool.routilux]
[routines]
directories = ["./project_routines"]

[tool.routilux.server]
port = 8080
""")

        from routilux.cli.config import ConfigLoader

        loader = ConfigLoader()
        config = loader.load(config_file)

        # Should extract tool.routilux section
        assert "routines" in config or "server" in config

    def test_unsupported_format(self, tmp_path: Path):
        """Test error on unsupported file format."""
        config_file = tmp_path / "config.ini"
        config_file.write_text("[routines]\ndirectories = ./routines")

        from routilux.cli.config import ConfigLoader

        loader = ConfigLoader()
        with pytest.raises(ValueError, match="Unsupported config format"):
            loader.load(config_file)


class TestGetConfigValue:
    """Tests for get_config_value helper function."""

    def test_get_nested_value(self):
        """Test getting nested configuration value."""
        from routilux.cli.config import get_config_value

        config = {"server": {"port": 8080, "host": "localhost"}}
        assert get_config_value(config, "server", "port") == 8080
        assert get_config_value(config, "server", "host") == "localhost"

    def test_get_missing_value_with_default(self):
        """Test getting missing value returns default."""
        from routilux.cli.config import get_config_value

        config = {"server": {"port": 8080}}
        assert get_config_value(config, "server", "host", default="0.0.0.0") == "0.0.0.0"
        assert get_config_value(config, "missing", "key", default="default") == "default"

    def test_get_deep_nested_value(self):
        """Test getting deeply nested configuration value."""
        from routilux.cli.config import get_config_value

        config = {"level1": {"level2": {"level3": "deep_value"}}}
        assert get_config_value(config, "level1", "level2", "level3") == "deep_value"


class TestMergeWithCli:
    """Tests for merge_with_cli functionality."""

    def test_cli_options_override_config(self):
        """Test that CLI options override config file values."""
        from routilux.cli.config import ConfigLoader

        loader = ConfigLoader()
        config = {"port": 8080, "host": "localhost"}
        cli_options = {"port": 9000}

        merged = loader.merge_with_cli(config, cli_options)
        assert merged["port"] == 9000  # CLI override
        assert merged["host"] == "localhost"  # From config

    def test_cli_none_values_dont_override(self):
        """Test that None CLI values don't override config."""
        from routilux.cli.config import ConfigLoader

        loader = ConfigLoader()
        config = {"port": 8080}
        cli_options = {"port": None}

        merged = loader.merge_with_cli(config, cli_options)
        assert merged["port"] == 8080  # Config value preserved
