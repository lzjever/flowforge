"""Tests for 'routilux completion' command."""

from click.testing import CliRunner


def test_completion_bash():
    """Test generating bash completion script."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "bash"])

    assert result.exit_code == 0
    assert "_routilux" in result.output
    assert "complete" in result.output.lower()


def test_completion_zsh():
    """Test generating zsh completion script."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "zsh"])

    assert result.exit_code == 0
    assert "#compdef routilux" in result.output


def test_completion_fish():
    """Test generating fish completion script."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "fish"])

    assert result.exit_code == 0
    assert "complete -c routilux" in result.output


def test_completion_invalid_shell():
    """Test completion with invalid shell."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "invalid_shell"])

    assert result.exit_code != 0
    assert "invalid" in result.output.lower() or "error" in result.output.lower()


def test_completion_help():
    """Test completion command help."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "--help"])

    assert result.exit_code == 0
    assert "shell" in result.output.lower()


def test_completion_bash_contains_commands():
    """Test that bash completion includes main commands."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "bash"])

    assert result.exit_code == 0
    # Should include main commands
    assert "init" in result.output
    assert "run" in result.output
    assert "list" in result.output
    assert "server" in result.output


def test_completion_zsh_contains_commands():
    """Test that zsh completion includes main commands."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "zsh"])

    assert result.exit_code == 0
    # Should include main commands
    assert "init" in result.output
    assert "run" in result.output
    assert "server" in result.output


def test_completion_fish_contains_commands():
    """Test that fish completion includes main commands."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["completion", "fish"])

    assert result.exit_code == 0
    # Should include main commands
    assert "init" in result.output
    assert "run" in result.output
    assert "server" in result.output
