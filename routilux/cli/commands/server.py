"""Server command implementation."""

import os
from pathlib import Path

import click


def _validate_port(ctx, param, value):
    """Validate port number.

    Args:
        ctx: Click context
        param: Parameter object
        value: The port value to validate

    Returns:
        Validated port value

    Raises:
        click.BadParameter: If port is invalid
    """
    if value < 0 or value > 65535:
        raise click.BadParameter(
            f"Port must be between 0-65535, got {value}.\nExample: --port 8080", param_hint="--port"
        )
    if value < 1024:
        click.echo(
            click.style("Warning: ", fg="yellow") + f"Port {value} requires root privileges",
            err=True,
        )
    return value


@click.group()
def server():
    """Manage the routilux HTTP server.

    \b
    Examples:
        # Start server on default port
        $ routilux server start

        # Check server status
        $ routilux server status

        # Stop running server
        $ routilux server stop
    """
    pass


@server.command("start")
@click.option(
    "--host",
    default="0.0.0.0",
    help="Host to bind to (default: 0.0.0.0)",
)
@click.option(
    "--port",
    default=8080,
    type=int,
    callback=_validate_port,
    help="Port to bind to (default: 8080)",
)
@click.option(
    "--routines-dir",
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help="Additional directories to scan for routines",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error", "critical"]),
    help="Log level for uvicorn (default: info)",
)
@click.pass_context
def start(ctx, host, port, routines_dir, reload, log_level):
    """Start the routilux HTTP server.

    Starts the FastAPI server with REST and WebSocket endpoints.
    Routines are automatically discovered from specified directories.

    \b
    Examples:
        # Start server on default port
        $ routilux server start

        # Custom host and port
        $ routilux server start --host 127.0.0.1 --port 3000

        # Development mode with auto-reload
        $ routilux server start --reload

        # Custom routines directory
        $ routilux server start --routines-dir ./routines

        # Debug logging
        $ routilux server start --log-level debug
    """
    quiet = ctx.obj.get("quiet", False)

    # Gather routines directories
    routines_dirs = list(routines_dir)
    routines_dirs.extend(ctx.obj.get("routines_dirs", []))

    if not quiet:
        click.echo(f"Starting routilux server on {host}:{port}")
        if routines_dirs:
            click.echo(f"Routines directories: {routines_dirs}")

    from routilux.cli.server_wrapper import start_server

    try:
        start_server(
            host=host,
            port=port,
            routines_dirs=routines_dirs if routines_dirs else None,
            reload=reload,
            log_level=log_level,
        )
    except KeyboardInterrupt:
        if not quiet:
            click.echo("\nServer stopped")
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        raise click.Abort(1)


@server.command("stop")
@click.option(
    "--port", default=8080, type=int, callback=_validate_port, help="Port of the server to stop"
)
@click.option("--force", "-f", is_flag=True, help="Force kill the server")
@click.pass_context
def stop(ctx, port, force):
    """Stop a running routilux server.

    \b
    Examples:
        # Stop server on default port
        $ routilux server stop

        # Stop server on specific port
        $ routilux server stop --port 3000

        # Force kill
        $ routilux server stop --force
    """
    import signal

    from routilux.cli.server_wrapper import read_pid_file, remove_pid_file

    pid = read_pid_file(port)
    if pid is None:
        click.echo(click.style("Error: ", fg="red") + f"No server found on port {port}", err=True)
        raise click.Abort(1)

    try:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
        remove_pid_file(port)
        click.echo(click.style("Server stopped", fg="green"))
    except ProcessLookupError:
        click.echo(
            click.style("Warning: ", fg="yellow") + f"Process {pid} not found, cleaning up PID file"
        )
        remove_pid_file(port)
    except PermissionError:
        click.echo(
            click.style("Error: ", fg="red")
            + f"Permission denied to stop process {pid}. Try --force or run as root.",
            err=True,
        )
        raise click.Abort(1)


@server.command("status")
@click.option("--port", default=8080, type=int, callback=_validate_port, help="Port to check")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def status(ctx, port, output_json):
    """Check server status.

    \b
    Examples:
        $ routilux server status
        $ routilux server status --port 3000
        $ routilux server status --json
    """
    import json

    from routilux.cli.server_wrapper import read_pid_file

    pid = read_pid_file(port)

    result = {
        "port": port,
        "pid": pid,
        "running": False,
        "version": None,
        "uptime": None,
    }

    # Check if process exists
    if pid:
        try:
            os.kill(pid, 0)  # Check if process exists
            result["running"] = True
        except ProcessLookupError:
            result["running"] = False

    # Try to hit health endpoint
    if result["running"]:
        try:
            import urllib.error
            import urllib.request

            url = f"http://localhost:{port}/health"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    result["version"] = data.get("version")
                    result["uptime"] = data.get("uptime")
        except (urllib.error.URLError, json.JSONDecodeError, Exception):
            result["running"] = False

    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        if result["running"]:
            click.echo(click.style("● ", fg="green") + f"Server running on port {port}")
            click.echo(f"  PID: {result['pid']}")
            if result["version"]:
                click.echo(f"  Version: {result['version']}")
            if result["uptime"]:
                click.echo(f"  Uptime: {result['uptime']}")
        else:
            click.echo(click.style("○ ", fg="red") + f"Server not running on port {port}")
