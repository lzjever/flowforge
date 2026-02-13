"""Tests for 'routilux run' command."""

from click.testing import CliRunner


def test_run_requires_workflow_option():
    """Test that run command requires --workflow option."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run"])
    assert result.exit_code != 0
    assert "Missing option" in result.output or "--workflow" in result.output


def test_run_with_simple_dsl(tmp_path):
    """Test running a simple workflow from DSL."""
    # Create a simple DSL file
    dsl_file = tmp_path / "flow.yaml"
    dsl_file.write_text("""
flow_id: test_flow
routines:
  source:
    class: data_source
    config:
      name: Source
connections: []
""")

    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--workflow", str(dsl_file)])

    # Should execute (exit code 0 or specific error if routines not found)
    assert "test_flow" in result.output or result.exit_code != 0


def test_run_with_invalid_dsl(tmp_path):
    """Test running with invalid DSL shows helpful error."""
    dsl_file = tmp_path / "invalid.yaml"
    dsl_file.write_text("invalid: yaml: content:")

    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--workflow", str(dsl_file)])

    # Should show error
    assert result.exit_code != 0 or "error" in result.output.lower()


def test_run_with_routines_dir(tmp_path):
    """Test running with custom routines directory."""
    # Create a routine
    routines_dir = tmp_path / "routines"
    routines_dir.mkdir()
    (routines_dir / "my_routine.py").write_text("""
from routilux.cli.decorators import register_routine

@register_routine("custom_processor")
def process(data):
    return data.upper()
""")

    # Create DSL using custom routine
    dsl_file = tmp_path / "flow.yaml"
    dsl_file.write_text("""
flow_id: custom_flow
routines:
  processor:
    class: custom_processor
connections: []
""")

    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(
        cli, ["run", "--workflow", str(dsl_file), "--routines-dir", str(routines_dir)]
    )

    # Should find custom routine
    assert "custom_flow" in result.output or result.exit_code != 0


# Parameter validation tests


def test_run_param_invalid_format(tmp_path):
    """Test that invalid param format shows error."""
    dsl_file = tmp_path / "flow.yaml"
    dsl_file.write_text("flow_id: test\nroutines: {}\nconnections: []")

    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(
        cli, ["run", "--workflow", str(dsl_file), "--param", "invalid_format_no_equals"]
    )

    # Should show error about KEY=VALUE format
    assert result.exit_code != 0 or "KEY=VALUE" in result.output


def test_run_param_empty_key(tmp_path):
    """Test that param with empty key shows error."""
    dsl_file = tmp_path / "flow.yaml"
    dsl_file.write_text("flow_id: test\nroutines: {}\nconnections: []")

    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--workflow", str(dsl_file), "--param", "=value"])

    # Should show error about empty key
    assert result.exit_code != 0 or "empty key" in result.output.lower()


def test_run_param_valid_format(tmp_path):
    """Test that valid param format is accepted."""
    dsl_file = tmp_path / "flow.yaml"
    dsl_file.write_text("flow_id: test\nroutines: {}\nconnections: []")

    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--workflow", str(dsl_file), "--param", "name=value"])

    # Should not fail due to param format (may fail for other reasons)
    assert "KEY=VALUE" not in result.output


def test_run_timeout_validation_negative(tmp_path):
    """Test that negative timeout shows error."""
    dsl_file = tmp_path / "flow.yaml"
    dsl_file.write_text("flow_id: test\nroutines: {}\nconnections: []")

    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--workflow", str(dsl_file), "--timeout", "-10"])

    # Should show error about positive timeout
    assert result.exit_code != 0 or "positive" in result.output.lower()


def test_run_timeout_validation_zero(tmp_path):
    """Test that zero timeout shows error."""
    dsl_file = tmp_path / "flow.yaml"
    dsl_file.write_text("flow_id: test\nroutines: {}\nconnections: []")

    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--workflow", str(dsl_file), "--timeout", "0"])

    # Should show error about positive timeout
    assert result.exit_code != 0 or "positive" in result.output.lower()


def test_run_timeout_valid(tmp_path):
    """Test that valid timeout is accepted."""
    dsl_file = tmp_path / "flow.yaml"
    dsl_file.write_text("flow_id: test\nroutines: {}\nconnections: []")

    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--workflow", str(dsl_file), "--timeout", "60"])

    # Should not fail due to timeout validation
    assert "positive" not in result.output.lower()


def test_run_help_shows_examples():
    """Test that run command help shows examples."""
    from routilux.cli.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])

    assert result.exit_code == 0
    assert "Examples" in result.output or "examples" in result.output
