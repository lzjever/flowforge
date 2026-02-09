# Routilux CLI Usage Guide

## Installation

Install the CLI with:

```bash
pip install routilux[cli]
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

### routilux server

Start the HTTP server:

```bash
routilux server start --host 0.0.0.0 --port 8080
```

With custom routines:

```bash
routilux server start --routines-dir ./routines --routines-dir ./lib/routines
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

List available flows:

```bash
routilux list flows
```

### routilux validate

Validate a DSL file:

```bash
routilux validate --workflow flows/my_flow.yaml
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

Create a `routilux.toml` file:

```toml
[routines]
directories = ["./routines", "./lib/routines"]

[server]
host = "0.0.0.0"
port = 8080
```
