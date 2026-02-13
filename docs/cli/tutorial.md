# Routilux CLI Tutorial

## Getting Started

### 1. Initialize a Project

```bash
mkdir my_workflow_project
cd my_workflow_project
routilux init
```

This creates:
- `routines/` - Directory for your routine scripts
- `flows/` - Directory for workflow DSL files
- `routilux.toml` - Configuration file
- Example files to get started

### 2. Write Your First Routine

Create `routines/hello.py`:

```python
from routilux.cli.decorators import register_routine

@register_routine("hello_world")
def hello(data, **kwargs):
    name = data.get("name", "World")
    return f"Hello, {name}!"
```

### 3. Create a Workflow

Create `flows/hello_flow.yaml`:

```yaml
flow_id: hello_flow
routines:
  hello:
    class: hello_world
connections: []
```

### 4. Run the Workflow

```bash
routilux run --workflow flows/hello_flow.yaml --param name=Claude
```

### 5. Start the Server

```bash
routilux server start
```

Now you can access the API at `http://localhost:8080`.

## Advanced Topics

### Multiple Routines

```yaml
flow_id: pipeline
routines:
  source:
    class: data_source
  processor:
    class: my_processor
  sink:
    class: data_sink
connections:
  - from: source.output
    to: processor.input
  - from: processor.output
    to: sink.input
```

### Error Handling

```python
@register_routine("safe_processor")
def safe_process(data, **kwargs):
    try:
        return process(data)
    except Exception as e:
        # Handle error
        return {"error": str(e)}
```

### Configuration

```python
@register_routine("configurable_processor")
def process_with_config(data, **kwargs):
    config = kwargs.get("config", {})
    timeout = config.get("timeout", 30)
    # Use configuration
    return result
```

## Shell Completion

Enable shell completion for easier command-line usage:

### Bash

```bash
# Generate and save
routilux completion bash > /etc/bash_completion.d/routilux

# Or install automatically
routilux completion bash --install

# Then reload your shell or run:
source ~/.bash_completion.d/routilux
```

### Zsh

```bash
# Generate and save
routilux completion zsh > ~/.zsh/completion/_routilux

# Then reload completions
autoload -U compinit && compinit
```

### Fish

```bash
# Generate and save
routilux completion fish > ~/.config/fish/completions/routilux.fish

# Completions are available in new fish sessions
```

## Server Management

### Starting the Server

```bash
# Start with default settings
routilux server start

# Start with custom port
routilux server start --port 3000

# Development mode with auto-reload
routilux server start --reload --log-level debug
```

### Checking Server Status

```bash
# Check status
routilux server status

# JSON output
routilux server status --json

# Check specific port
routilux server status --port 3000
```

### Stopping the Server

```bash
# Graceful stop
routilux server stop

# Force kill
routilux server stop --force

# Stop specific port
routilux server stop --port 3000
```
