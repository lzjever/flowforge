"""List command implementation."""

from pathlib import Path
from typing import Optional

import click

from routilux.cli.discovery import discover_routines, get_default_routines_dirs
from routilux.tools.factory.factory import ObjectFactory

# Optional rich support
try:
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def _create_console():
    """Create a rich console if available."""
    if HAS_RICH:
        return Console()
    return None


@click.command()
@click.argument("resource", type=click.Choice(["routines", "flows"]))
@click.option(
    "--category",
    "-c",
    help="Filter by category",
)
@click.option(
    "--routines-dir",
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help="Additional directories to scan for routines",
)
@click.option(
    "--dir",
    type=click.Path(exists=True, path_type=Path),
    help="Directory to scan for flows (local DSL files)",
)
@click.option(
    "--server",
    help="Server URL to list flows from (e.g. http://localhost:20555). If set, lists flows from API instead of local files.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["table", "json", "plain"]),
    default="table",
    help="Output format (default: table)",
)
@click.pass_context
def list_cmd(ctx, resource, category, routines_dir, dir, server, output_format):
    """List available resources.

    List either discovered routines or available flow DSL files.
    For flows, use --server to list from a running Routilux API server instead of local files.

    \b
    Examples:
        # List all routines
        $ routilux list routines

        # List routines in a category
        $ routilux list routines --category example

        # List routines as JSON
        $ routilux list routines --format json

        # List available flows (from local DSL files)
        $ routilux list flows

        # List flows from a running server
        $ routilux list flows --server http://localhost:20555

        # List flows from specific directory
        $ routilux list flows --dir ./my_flows
    """
    quiet = ctx.obj.get("quiet", False)

    if resource == "routines":
        _list_routines(category, routines_dir, output_format, quiet)
    elif resource == "flows":
        if server:
            _list_flows_from_server(server, output_format, quiet)
        else:
            _list_flows(dir, output_format, quiet)


def _list_routines(category: Optional[str], routines_dirs: tuple, output_format: str, quiet: bool):
    """List discovered routines."""

    # Gather routines directories
    all_dirs = list(routines_dirs)
    all_dirs.extend(get_default_routines_dirs())

    # Discover routines
    if all_dirs:
        discover_routines(all_dirs, on_error="warn")

    # List routines
    factory = ObjectFactory.get_instance()
    routines = factory.list_available(category=category)

    if output_format == "json":
        import json

        click.echo(json.dumps(routines, indent=2))
    elif output_format == "plain":
        for routine in routines:
            click.echo(routine["name"])
    else:  # table
        if not routines:
            if not quiet:
                click.echo("No routines found.")
            return

        # Use rich table if available
        if HAS_RICH:
            console = _create_console()
            table = Table(title="Available Routines")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Type", style="green")
            table.add_column("Category", style="yellow")
            table.add_column("Description", style="dim")

            for routine in routines:
                name = routine["name"][:30]
                obj_type = routine["object_type"][:10]
                cat = (routine.get("category") or "")[:15]
                desc = (routine.get("description") or "")[:50]
                table.add_row(name, obj_type, cat, desc)

            console.print(table)
        else:
            # Fallback to basic table
            click.echo(f"{'Name':<30} {'Type':<10} {'Category':<15} {'Description'}")
            click.echo("-" * 100)
            for routine in routines:
                name = routine["name"][:30]
                obj_type = routine["object_type"][:10]
                cat = (routine.get("category") or "")[:15]
                desc = (routine.get("description") or "")[:40]
                click.echo(f"{name:<30} {obj_type:<10} {cat:<15} {desc}")


def _list_flows_from_server(server_url: str, output_format: str, quiet: bool):
    """List flows from a running Routilux API server."""
    import json
    import urllib.error
    import urllib.request

    url = f"{server_url.rstrip('/')}/api/v1/flows"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        raise click.ClickException(f"Server error {e.code}: {body}")
    except OSError as e:
        raise click.ClickException(f"Cannot reach server: {e}")

    flows = data.get("flows") or []
    rows = [{"flow_id": f.get("flow_id", ""), "source": "api"} for f in flows]

    if output_format == "json":
        click.echo(json.dumps(rows, indent=2))
    elif output_format == "plain":
        for row in rows:
            click.echo(row["flow_id"])
    else:
        if not rows and not quiet:
            click.echo("No flows found on server.")
            return
        if HAS_RICH:
            console = _create_console()
            table = Table(title="Flows (from server)")
            table.add_column("Flow ID", style="cyan", no_wrap=True)
            table.add_column("Source", style="green")
            for row in rows:
                table.add_row(row["flow_id"][:50], row.get("source", ""))
            console.print(table)
        else:
            click.echo(f"{'Flow ID':<50} {'Source'}")
            click.echo("-" * 60)
            for row in rows:
                click.echo(f"{row['flow_id'][:50]:<50} {row.get('source', '')}")


def _list_flows(directory: Optional[Path], output_format: str, quiet: bool):
    """List available flow DSL files."""
    import yaml

    dirs = []
    if directory:
        dirs.append(directory)

    # Add default locations
    dirs.append(Path.cwd() / "flows")
    dirs.append(Path.cwd())

    flows = []
    for flow_dir in dirs:
        if not flow_dir.exists():
            continue
        for ext in ("*.yaml", "*.yml", "*.json"):
            for flow_file in flow_dir.glob(ext):
                try:
                    # Parse to get flow_id
                    content = flow_file.read_text()
                    if flow_file.suffix in (".yaml", ".yml"):
                        data = yaml.safe_load(content)
                    else:
                        import json

                        data = json.loads(content)

                    flow_id = data.get("flow_id", flow_file.stem)
                    flows.append(
                        {
                            "flow_id": flow_id,
                            "file": str(flow_file),
                        }
                    )
                except Exception:
                    # Skip invalid files
                    flows.append(
                        {
                            "flow_id": f"<parse error: {flow_file.stem}>",
                            "file": str(flow_file),
                        }
                    )

    if output_format == "json":
        import json

        click.echo(json.dumps(flows, indent=2))
    elif output_format == "plain":
        for flow in flows:
            click.echo(flow["flow_id"])
    else:  # table
        if not flows:
            if not quiet:
                click.echo("No flows found.")
            return

        # Use rich table if available
        if HAS_RICH:
            console = _create_console()
            table = Table(title="Available Flows")
            table.add_column("Flow ID", style="cyan", no_wrap=True)
            table.add_column("File", style="green")

            for flow in flows:
                flow_id = flow["flow_id"][:30]
                file_path = flow["file"]
                table.add_row(flow_id, file_path)

            console.print(table)
        else:
            # Fallback to basic table
            click.echo(f"{'Flow ID':<30} {'File'}")
            click.echo("-" * 80)
            for flow in flows:
                flow_id = flow["flow_id"][:30]
                file_path = flow["file"]
                click.echo(f"{flow_id:<30} {file_path}")
