# AST Analyzer Tool

This tool analyzes the FlowForge codebase's AST (Abstract Syntax Tree) and generates a compact API reference document optimized for LLM consumption.

## Usage

```bash
python tools/analyze_codebase_ast.py
```

The tool will:
1. Parse core FlowForge Python files
2. Extract class definitions, methods, and functions
3. Extract type annotations, parameters, and docstrings
4. Generate a compact markdown document at `docs/source/api_reference_compact.md`

## Output Format

The generated document includes:
- Class definitions with base classes
- Method signatures with type annotations
- Function signatures with type annotations
- Brief docstrings (first line only for compactness)

## Core Files Analyzed

- `flowforge/routine.py` - Routine base class
- `flowforge/flow.py` - Flow manager
- `flowforge/slot.py` - Slot class
- `flowforge/event.py` - Event class
- `flowforge/connection.py` - Connection class
- `flowforge/error_handler.py` - ErrorHandler class
- `flowforge/job_state.py` - JobState class
- `flowforge/execution_tracker.py` - ExecutionTracker class
- `flowforge/utils/serializable.py` - Serializable base class
- `flowforge/serialization_utils.py` - Serialization utilities

## Purpose

This compact reference is designed for:
- LLM code generation assistants
- Quick API lookup
- Understanding the codebase structure
- Generating code that uses FlowForge

The document is intentionally compact to fit within LLM context windows while providing essential API information.

