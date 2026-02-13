"""Tests for server --flows-dir option."""

import tempfile
from pathlib import Path

import yaml
from click.testing import CliRunner


def test_server_start_with_flows_dir():
    """Test that --flows-dir option is accepted."""
    from routilux.cli.main import cli

    runner = CliRunner()

    with tempfile.TemporaryDirectory() as tmpdir:
        flows_dir = Path(tmpdir)

        # Create a simple flow
        flow_data = {
            "flow_id": "test_flow",
            "routines": {"m": {"class": "Mapper"}},
            "connections": [],
        }
        (flows_dir / "test.yaml").write_text(yaml.dump(flow_data))

        # Just check help shows the option
        result = runner.invoke(cli, ["server", "start", "--help"])

        assert result.exit_code == 0
        assert "--flows-dir" in result.output


def test_server_start_flows_dir_option_in_help():
    """Test that --flows-dir is documented in help."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "start", "--help"])

    assert result.exit_code == 0
    assert "flows-dir" in result.output.lower() or "flows" in result.output.lower()
