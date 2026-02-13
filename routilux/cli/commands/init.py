"""Init command implementation."""

import re

import click


def _validate_project_name(ctx, param, value):
    """Validate project name.

    Args:
        ctx: Click context
        param: Parameter object
        value: The project name to validate

    Returns:
        Validated project name

    Raises:
        click.BadParameter: If project name is invalid
    """
    if value is None or value == ".":
        return "."

    # Check for invalid characters
    if not re.match(r"^[a-zA-Z0-9_\-./]+$", value):
        raise click.BadParameter(
            f"'{value}' contains invalid characters.\n"
            f"Project names can only contain letters, numbers, underscores, hyphens, dots, and slashes.\n"
            f"Example: routilux init my-project",
        )

    # Check for reserved names
    reserved_names = (
        ["con", "prn", "aux", "nul"]
        + [f"com{i}" for i in range(1, 10)]
        + [f"lpt{i}" for i in range(1, 10)]
    )
    if value.lower() in reserved_names:
        raise click.BadParameter(f"'{value}' is a reserved name.\nPlease choose a different name.")

    return value


@click.command()
@click.argument("name", default=".", callback=_validate_project_name)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing files",
)
@click.pass_context
def initialize(ctx, name, force):
    """Initialize a new routilux project.

    Creates the directory structure and example files for a routilux project,
    including routines/, flows/ directories and example files.

    \b
    Examples:
        # Initialize in current directory
        $ routilux init

        # Create a named project
        $ routilux init my-project

        # Overwrite existing files
        $ routilux init my-project --force
    """
    quiet = ctx.obj.get("quiet", False)

    from pathlib import Path

    project_dir = Path(name).resolve()

    if not quiet:
        click.echo(f"Initializing routilux project: {project_dir}")

    # Create directories
    routines_dir = project_dir / "routines"
    flows_dir = project_dir / "flows"

    routines_dir.mkdir(parents=True, exist_ok=True)
    flows_dir.mkdir(parents=True, exist_ok=True)

    if not quiet:
        click.echo(f"Created: {routines_dir}")
        click.echo(f"Created: {flows_dir}")

    # Create example routine
    example_routine = routines_dir / "example_routine.py"
    if not example_routine.exists() or force:
        example_routine.write_text('''"""Example routine for routilux."""

from routilux.cli.decorators import register_routine


@register_routine(
    "example_processor",
    category="example",
    tags=["demo"],
    description="An example routine that processes data"
)
def example_logic(data, **kwargs):
    """Process input data and return result.

    Args:
        data: Input data to process
        **kwargs: Additional keyword arguments

    Returns:
        Processed data
    """
    # Your processing logic here
    result = data

    # Emit output
    return result
''')
        if not quiet:
            click.echo(f"Created: {example_routine}")

    # Create example flow
    example_flow = flows_dir / "example_flow.yaml"
    if not example_flow.exists() or force:
        example_flow.write_text("""# Example flow definition

flow_id: example_flow

routines:
  processor:
    class: example_processor
    config:
      # Add configuration here

connections:
  # Add connections here
  # Example:
  # - from: processor.output
  #   to: next_routine.input

execution:
  timeout: 300.0
""")
        if not quiet:
            click.echo(f"Created: {example_flow}")

    # Create config file
    config_file = project_dir / "routilux.toml"
    if not config_file.exists() or force:
        config_file.write_text("""# Routilux configuration file

[routines]
directories = ["./routines"]

[server]
host = "0.0.0.0"
port = 8080

[discovery]
auto_reload = true
ignore_patterns = ["*_test.py", "test_*.py"]
""")
        if not quiet:
            click.echo(f"Created: {config_file}")

    if not quiet:
        click.echo("\n✓ Project initialized successfully!")
        click.echo("\nNext steps:")
        click.echo("  1. Add your routines to the routines/ directory")
        click.echo("  2. Define your flows in the flows/ directory")
        click.echo("  3. Run with: routilux run --workflow flows/your_flow.yaml")
        click.echo("  4. Or start server: routilux server start")
