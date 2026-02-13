"""Tests for 'routilux server' command."""

from click.testing import CliRunner


def test_server_start_command():
    """Test that server start command is available."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "start", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.output
    assert "--port" in result.output


def test_server_with_custom_port():
    """Test server with custom port option."""
    from routilux.cli.main import cli

    runner = CliRunner()
    # Would actually start server, so we just check help
    result = runner.invoke(cli, ["server", "start", "--help"])
    assert "--port" in result.output


def test_server_stop_command():
    """Test that server stop command is available."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "stop", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
    assert "--force" in result.output


def test_server_stop_no_server():
    """Test stopping server when none is running."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "stop", "--port", "9999"])

    # Should fail since no server is running
    assert result.exit_code != 0
    assert "No server found" in result.output


def test_server_status_command():
    """Test that server status command is available."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "status", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output
    assert "--json" in result.output


def test_server_status_not_running():
    """Test status when server is not running."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "status", "--port", "9999"])

    # Should show server not running
    assert result.exit_code == 0
    assert "not running" in result.output.lower()


def test_server_status_json_output():
    """Test status with JSON output."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "status", "--port", "9999", "--json"])

    assert result.exit_code == 0
    # Should contain JSON structure
    assert '"port"' in result.output
    assert "9999" in result.output


def test_server_port_validation():
    """Test port validation."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "start", "--port", "99999"])

    # Should fail validation
    assert result.exit_code != 0
    assert "Port" in result.output or "65535" in result.output


def test_server_negative_port():
    """Test negative port validation."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "start", "--port", "-1"])

    # Should fail validation
    assert result.exit_code != 0


def test_server_group_help():
    """Test server group help shows all commands."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["server", "--help"])

    assert result.exit_code == 0
    assert "start" in result.output
    assert "stop" in result.output
    assert "status" in result.output
