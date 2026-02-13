"""Tests for flow loading functionality."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml


def test_load_flows_from_directory():
    """Test loading flows from a directory."""
    from routilux.builtin_routines import register_all_builtins
    from routilux.cli.server_wrapper import load_flows_from_directory
    from routilux.tools.factory.factory import ObjectFactory

    factory = ObjectFactory()
    register_all_builtins(factory)

    with tempfile.TemporaryDirectory() as tmpdir:
        flows_dir = Path(tmpdir)

        # Create a simple flow
        flow_data = {
            "flow_id": "test_flow",
            "routines": {"mapper": {"class": "Mapper"}},
            "connections": [],
        }
        (flows_dir / "test.yaml").write_text(yaml.dump(flow_data))

        flows = load_flows_from_directory(flows_dir, factory)

        assert "test_flow" in flows
        assert flows["test_flow"].flow_id == "test_flow"


def test_load_flows_detects_duplicate_flow_id():
    """Test that duplicate flow_ids cause an error."""
    from routilux.builtin_routines import register_all_builtins
    from routilux.cli.server_wrapper import load_flows_from_directory
    from routilux.tools.factory.factory import ObjectFactory

    factory = ObjectFactory()
    register_all_builtins(factory)

    with tempfile.TemporaryDirectory() as tmpdir:
        flows_dir = Path(tmpdir)

        # Create two flows with same flow_id
        flow_data = {
            "flow_id": "duplicate_flow",
            "routines": {"m1": {"class": "Mapper"}},
            "connections": [],
        }
        (flows_dir / "flow1.yaml").write_text(yaml.dump(flow_data))
        (flows_dir / "flow2.yaml").write_text(yaml.dump(flow_data))

        with pytest.raises(ValueError, match="Duplicate flow_id"):
            load_flows_from_directory(flows_dir, factory)


def test_load_flows_empty_directory():
    """Test loading from empty directory returns empty dict."""
    from routilux.cli.server_wrapper import load_flows_from_directory
    from routilux.tools.factory.factory import ObjectFactory

    factory = ObjectFactory()

    with tempfile.TemporaryDirectory() as tmpdir:
        flows = load_flows_from_directory(Path(tmpdir), factory)
        assert flows == {}


def test_load_flows_from_json_file():
    """Test loading flows from JSON files."""
    from routilux.builtin_routines import register_all_builtins
    from routilux.cli.server_wrapper import load_flows_from_directory
    from routilux.tools.factory.factory import ObjectFactory

    factory = ObjectFactory()
    register_all_builtins(factory)

    with tempfile.TemporaryDirectory() as tmpdir:
        flows_dir = Path(tmpdir)

        # Create a flow in JSON format
        flow_data = {
            "flow_id": "json_flow",
            "routines": {"filter": {"class": "Filter"}},
            "connections": [],
        }
        (flows_dir / "test.json").write_text(json.dumps(flow_data))

        flows = load_flows_from_directory(flows_dir, factory)

        assert "json_flow" in flows
        assert flows["json_flow"].flow_id == "json_flow"
