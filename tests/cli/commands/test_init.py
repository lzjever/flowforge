"""Tests for 'routilux init' command."""

from click.testing import CliRunner


def test_init_creates_project_structure(tmp_path):
    """Test that init creates project structure."""
    from routilux.cli.main import cli

    runner = CliRunner()
    with runner.isolated_filesystem():
        # Change to the temp directory for the test
        import os

        os.chdir(tmp_path)

        result = runner.invoke(cli, ["init"])

        assert result.exit_code == 0
        assert (tmp_path / "routines").exists()
        assert (tmp_path / "flows").exists()


def test_init_with_custom_name(tmp_path):
    """Test init with custom project name."""
    from routilux.cli.main import cli

    runner = CliRunner()
    with runner.isolated_filesystem():
        # Change to the temp directory for the test
        import os

        os.chdir(tmp_path)

        # Use positional argument (new syntax)
        result = runner.invoke(cli, ["init", "my_project"])

        assert result.exit_code == 0
        assert (tmp_path / "my_project" / "routines").exists()
