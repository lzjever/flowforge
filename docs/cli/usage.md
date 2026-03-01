# Routilux CLI Usage Guide

## Installation

Install the CLI with:

```bash
pip install routilux[cli]
```

## Global Options

```bash
routilux [OPTIONS] COMMAND [ARGS]

Options:
  --routines-dir PATH  Additional directories to scan for routines
  --config PATH        Path to configuration file (supports TOML, YAML, JSON)
  -v, --verbose        Enable verbose output
  -q, --quiet          Minimal output
  --version            Show the version and exit
  --help               Show help message
```

## Commands

### routilux run

Execute a workflow from a DSL file:

```bash
routilux run --workflow flows/my_flow.yaml
```

With custom routines directory:

```bash
routilux run --workflow flow.yaml --routines-dir ./my_routines
```

With parameters:

```bash
routilux run --workflow flow.yaml --param name=value --param count=5
```

With timeout:

```bash
routilux run --workflow flow.yaml --timeout 60
```

Save output to file:

```bash
routilux run --workflow flow.yaml --output result.json
```

### routilux server

Manage the HTTP server:

Start the server:

```bash
routilux server start --host 0.0.0.0 --port 8080
```

With custom routines:

```bash
routilux server start --routines-dir ./routines --routines-dir ./lib/routines
```

Development mode with auto-reload:

```bash
routilux server start --reload
```

Check server status:

```bash
routilux server status
routilux server status --port 3000
routilux server status --json
```

Stop running server:

```bash
routilux server stop
routilux server stop --port 3000
routilux server stop --force  # Force kill
```

### routilux list

List available routines:

```bash
routilux list routines
```

Filter by category:

```bash
routilux list routines --category processing
```

List with different formats:

```bash
routilux list routines --format json
routilux list routines --format plain
```

List available flows (from local DSL files):

```bash
routilux list flows
```

List flows from a running server:

```bash
routilux list flows --server http://localhost:20555
```

### routilux validate

Validate a DSL file:

```bash
routilux validate --workflow flows/my_flow.yaml
```

With verbose output:

```bash
routilux -v validate --workflow flows/my_flow.yaml
```

### routilux init

Initialize a new project:

```bash
routilux init
```

With custom name:

```bash
routilux init --name my_project
```

Overwrite existing files:

```bash
routilux init --force
```

### routilux completion

Generate shell completion scripts:

```bash
# Bash
routilux completion bash > /etc/bash_completion.d/routilux

# Zsh
routilux completion zsh > ~/.zsh/completion/_routilux

# Fish
routilux completion fish > ~/.config/fish/completions/routilux.fish
```

Auto-install completion:

```bash
routilux completion bash --install
```

## Writing Routines

### Using Decorators

```python
from routilux.cli.decorators import register_routine

@register_routine("my_processor", category="processing", tags=["fast"])
def my_logic(data, **kwargs):
    # Process data
    return processed_data
```

### Using Classes

```python
from routilux.core.routine import Routine

class MyProcessor(Routine):
    factory_name = "my_processor"

    def setup(self):
        self.add_slot("input")
        self.add_event("output")
```

## DSL Format

### YAML

```yaml
flow_id: my_flow
routines:
  source:
    class: data_source
    config:
      name: Source
connections:
  - from: source.output
    to: processor.input
```

### JSON

```json
{
  "flow_id": "my_flow",
  "routines": {
    "source": {
      "class": "data_source",
      "config": {"name": "Source"}
    }
  },
  "connections": []
}
```

## Configuration

### Configuration File

Routilux CLI supports configuration files in TOML, YAML, or JSON format.
The CLI automatically looks for `routilux.toml` or `pyproject.toml` in the current directory.

Create a `routilux.toml` file:

```toml
[routines]
directories = ["./routines", "./lib/routines"]
ignore_patterns = ["*_test.py", "test_*.py"]

[server]
host = "0.0.0.0"
port = 8080
reload = false
log_level = "info"

[run]
default_timeout = 300.0
output_format = "json"

[discovery]
auto_reload = true
cache_enabled = true
```

For `pyproject.toml`, use the `[tool.routilux]` section:

```toml
[tool.routilux]
[routines]
directories = ["./routines"]

[tool.routilux.server]
port = 8080
```

### Configuration Priority

1. Command-line options (highest priority)
2. Configuration file values
3. Default values (lowest priority)

### Using a Specific Config File

```bash
routilux --config my-config.toml run --workflow flow.yaml
```

## Parameter Validation

The CLI validates parameters and provides helpful error messages:

```bash
# Invalid param format
$ routilux run -w flow.yaml -p invalid
Error: 'invalid' is not in KEY=VALUE format.
Example: --param name=value

# Invalid timeout
$ routilux run -w flow.yaml --timeout -10
Error: Timeout must be positive, got -10.
Example: --timeout 60

# Invalid port
$ routilux server start --port 99999
Error: Port must be between 0-65535, got 99999.
Example: --port 8080
```
