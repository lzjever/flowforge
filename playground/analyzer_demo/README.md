# Routine and Workflow Analyzer Demo

## Overview

This demo provides comprehensive analysis and export functionality for routilux routines and workflows. Simply run it without any parameters, and it will automatically:

- Analyze routine Python files using AST parsing
- Generate beautiful Markdown documentation cards for routines
- Analyze Flow objects dynamically at runtime
- Export analysis results to JSON format
- Generate both standard and ultimate D2 format files for workflow visualization
- Combine static and dynamic analysis for complete workflow documentation

**No configuration needed** - just run it and get all the analysis files!

## Features

### Routine Analysis

- **AST-based Analysis**: Extracts routine structure from Python source files
- **Slot Detection**: Identifies input slots and their handlers
- **Event Detection**: Identifies output events and their parameters
- **Configuration Analysis**: Extracts routine configuration settings
- **Method Analysis**: Analyzes handler methods and their emit calls
- **Documentation Extraction**: Extracts docstrings and comments

### Workflow Analysis

- **Flow Metadata**: Extracts flow ID, execution strategy, timeouts, etc.
- **Routine Information**: Combines runtime state with source analysis
- **Connection Mapping**: Maps all connections between routines
- **Dependency Graph**: Builds dependency graph for workflow
- **Entry Point Detection**: Identifies workflow entry points
- **Visualization Export**: Generates D2 format for diagram generation

### Export Formats

- **JSON**: Structured data for programmatic use
- **D2**: Diagram format for visualization (use D2 CLI to generate SVG/PNG)

## Quick Start

Simply run the demo without any parameters. It will automatically:

1. Analyze all demo routines
2. Generate routine analysis JSON and Markdown cards
3. Analyze both complex and simple workflows
4. Generate standard and ultimate D2 diagrams for both workflows

```bash
cd /home/percy/works/mygithub/routilux
conda activate mbos
python -m playground.analyzer_demo.analyzer_demo
```

That's it! All analysis files will be generated in the `exports/` directory.

## Demo Routines

The demo includes several example routines in `demo_routines.py`:

- **DataCollector**: Entry point routine with trigger slot and multiple output events
- **DataProcessor**: Processes data with configurable transformations
- **DataValidator**: Validates data with multiple input slots and conditional outputs
- **DataAggregator**: Aggregates data with custom merge strategy
- **DataRouter**: Routes data based on conditions to multiple outputs
- **DataSink**: Final destination with multiple input slots

## Demo Workflows

### Complex Workflow

A multi-stage workflow demonstrating:
- Multiple routine connections
- Conditional routing
- Parallel execution paths
- Error handling paths

Structure:
```
DataCollector → DataProcessor → DataValidator → DataAggregator → DataRouter
                                                                    ├→ DataSink (high)
                                                                    ├→ DataSink (medium)
                                                                    └→ DataSink (low)
```

### Simple Workflow

A linear workflow demonstrating:
- Basic routine connections
- Sequential execution

Structure:
```
DataCollector → DataProcessor → DataSink
```

## Output Files

The demo automatically generates the following files in the `exports/` directory:

### Routine Analysis
- `demo_routines_analysis.json`: Complete routine analysis in JSON format
- `demo_routines_cards.md`: Beautiful Markdown documentation cards for all routines

### Complex Workflow Analysis
- `complex_demo_workflow_analysis.json`: Complete workflow analysis in JSON format
- `complex_demo_workflow.d2`: Standard D2 format for visualization
- `complex_demo_workflow_ultimate.d2`: Ultimate D2 format with enhanced styling and detailed information

### Simple Workflow Analysis
- `simple_demo_workflow_analysis.json`: Complete workflow analysis in JSON format
- `simple_demo_workflow.d2`: Standard D2 format for visualization
- `simple_demo_workflow_ultimate.d2`: Ultimate D2 format with enhanced styling and detailed information

### D2 Export Modes

- **standard**: Basic D2 visualization with routine nodes and connections
- **ultimate**: Enhanced D2 visualization with:
  - Professional styling and colors
  - Detailed node information (docstrings, config, methods)
  - Enhanced slot and event information
  - Better visual hierarchy
  - Animated connections
  - Entry point highlighting
  - Uses routine analysis data for enriched node details

## Using D2 for Visualization

After generating D2 files, you can create diagrams using the D2 CLI:

```bash
# Install D2 (if not already installed)
# See: https://d2lang.com/install

# Generate SVG diagrams
d2 exports/complex_demo_workflow.d2 exports/complex_demo_workflow.svg
d2 exports/complex_demo_workflow_ultimate.d2 exports/complex_demo_workflow_ultimate.svg
d2 exports/simple_demo_workflow.d2 exports/simple_demo_workflow.svg
d2 exports/simple_demo_workflow_ultimate.d2 exports/simple_demo_workflow_ultimate.svg

# Generate PNG diagrams
d2 exports/complex_demo_workflow.d2 exports/complex_demo_workflow.png
d2 exports/complex_demo_workflow_ultimate.d2 exports/complex_demo_workflow_ultimate.png
d2 exports/simple_demo_workflow.d2 exports/simple_demo_workflow.png
d2 exports/simple_demo_workflow_ultimate.d2 exports/simple_demo_workflow_ultimate.png
```

## Analysis Results Structure

### Routine Analysis JSON

```json
{
  "file_path": "path/to/file.py",
  "routines": [
    {
      "name": "RoutineName",
      "line_number": 12,
      "docstring": "Routine description",
      "slots": [
        {
          "name": "input",
          "handler": "process",
          "merge_strategy": "append"
        }
      ],
      "events": [
        {
          "name": "output",
          "output_params": ["data", "status"]
        }
      ],
      "config": {
        "key": "value"
      },
      "methods": [
        {
          "name": "process",
          "emits": ["output"]
        }
      ]
    }
  ]
}
```

### Workflow Analysis JSON

```json
{
  "flow_id": "demo_workflow",
  "execution_strategy": "concurrent",
  "max_workers": 3,
  "execution_timeout": 60.0,
  "routines": [
    {
      "routine_id": "collector",
      "class_name": "DataCollector",
      "slots": [...],
      "events": [...],
      "source_info": {...}
    }
  ],
  "connections": [
    {
      "source_routine_id": "collector",
      "source_event": "data",
      "target_routine_id": "processor",
      "target_slot": "input",
      "param_mapping": null
    }
  ],
  "dependency_graph": {
    "collector": [],
    "processor": ["collector"],
    "sink": ["processor"]
  },
  "entry_points": ["collector"]
}
```

## Integration Examples

### Analyze Your Own Routines

```python
from routilux import analyze_routine_file
from pathlib import Path

# Analyze a routine file
result = analyze_routine_file(Path("my_routines.py"))
print(f"Found {len(result['routines'])} routines")
```

### Analyze Your Own Workflows

```python
from routilux import Flow, analyze_workflow

# Create your workflow
flow = Flow(flow_id="my_workflow")
# ... add routines and connections ...

# Analyze the workflow
result = analyze_workflow(flow, include_source_analysis=True)

# Export to JSON
from routilux import WorkflowAnalyzer
analyzer = WorkflowAnalyzer()
analyzer.save_json(result, "my_workflow_analysis.json")

# Export to D2
analyzer.save_d2(result, "my_workflow.d2")
```

## Use Cases

1. **Documentation Generation**: Automatically generate documentation from code
2. **Workflow Visualization**: Create diagrams of complex workflows
3. **Code Analysis**: Understand routine structure and dependencies
4. **Migration Planning**: Analyze workflow dependencies before refactoring
5. **Quality Assurance**: Verify workflow structure and connections

## Files

- `analyzer_demo.py`: Main demo script with CLI interface
- `demo_routines.py`: Example routines for demonstration
- `README.md`: This file

## Key Insights

1. **Static vs Dynamic Analysis**: 
   - AST-based analysis extracts structure from source code
   - Runtime analysis captures actual workflow connections
   - Combined analysis provides complete picture

2. **Export Formats**:
   - JSON for programmatic use and integration
   - D2 for human-readable visualizations

3. **Workflow Understanding**:
   - Dependency graphs help understand execution order
   - Entry points identify workflow starting points
   - Connection mapping shows data flow

## Troubleshooting

### File Not Found

If you get a "file not found" error:
- Use absolute paths or paths relative to the demo directory
- Ensure the file exists and is readable

### Import Errors

If you get import errors:
- Ensure you're in the routilux root directory
- Activate the conda environment: `conda activate mbos`
- Install routilux in development mode: `pip install -e .`

### D2 Visualization

If D2 files don't render:
- Install D2 CLI: https://d2lang.com/install
- Check D2 syntax in the generated file
- Use D2 CLI to validate: `d2 check file.d2`

## Next Steps

1. Analyze your own routine files
2. Create workflows and analyze them
3. Generate visualizations using D2
4. Integrate analyzers into your documentation pipeline
5. Customize export formats for your needs

