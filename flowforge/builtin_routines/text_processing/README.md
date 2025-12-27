# Text Processing Routines

This package provides routines for text manipulation, formatting, and extraction.

## Routines

### TextClipper

Clips text to a maximum length while preserving important information like tracebacks.

**Features:**
- Preserves tracebacks completely
- Clips text line by line
- Provides informative truncation messages
- Configurable maximum length

**Usage:**
```python
from flowforge.builtin_routines.text_processing import TextClipper
from flowforge import Flow

clipper = TextClipper()
clipper.set_config(max_length=1000, preserve_tracebacks=True)

flow = Flow()
flow.add_routine(clipper, "clipper")
```

**Configuration:**
- `max_length` (int): Maximum text length (default: 1000)
- `preserve_tracebacks` (bool): Whether to preserve tracebacks (default: True)
- `truncation_message` (str): Message to append when text is clipped

**Input:**
- `text` (str): Text to clip

**Output:**
- `clipped_text` (str): Clipped text
- `was_clipped` (bool): Whether text was clipped
- `original_length` (int): Original text length

### TextRenderer

Renders objects into formatted text with XML-like tags or markdown format.

**Features:**
- Renders dictionaries, lists, and nested structures
- Supports XML and markdown formats
- Configurable indentation

**Usage:**
```python
from flowforge.builtin_routines.text_processing import TextRenderer

renderer = TextRenderer()
renderer.set_config(tag_format="xml", indent="  ")

flow = Flow()
flow.add_routine(renderer, "renderer")
```

**Configuration:**
- `tag_format` (str): Format type - "xml" or "markdown" (default: "xml")
- `indent` (str): Indentation string (default: "  ")

**Input:**
- `data` (Any): Data to render

**Output:**
- `rendered_text` (str): Formatted text

### ResultExtractor

Extracts and formats results from various output formats with extensible architecture.

**Features:**
- Extracts JSON from code blocks and plain strings
- Extracts code blocks of various languages
- Formats interpreter output
- Supports custom extractors
- Multiple extraction strategies

**Usage:**
```python
from flowforge.builtin_routines.text_processing import ResultExtractor

extractor = ResultExtractor()
extractor.set_config(
    strategy="auto",
    extract_json_blocks=True,
    extract_code_blocks=True
)

flow = Flow()
flow.add_routine(extractor, "extractor")
```

**Configuration:**
- `strategy` (str): Extraction strategy - "auto", "first_match", "all", "priority" (default: "auto")
- `extract_json_blocks` (bool): Extract JSON from code blocks (default: True)
- `extract_code_blocks` (bool): Extract code blocks (default: True)
- `format_interpreter_output` (bool): Format interpreter output (default: True)
- `continue_on_error` (bool): Continue on extraction errors (default: True)
- `return_original_on_failure` (bool): Return original data on failure (default: True)

**Input:**
- `data` (Any): Data to extract from

**Output:**
- `extracted_result` (Any): Extracted result
- `format` (str): Detected format type
- `metadata` (dict): Extraction metadata
- `confidence` (float): Confidence score (0.0-1.0)
- `extraction_path` (list): Path of extraction methods used

## Installation

This package can be used standalone or as part of FlowForge:

```python
# Standalone usage
import sys
sys.path.insert(0, '/path/to/flowforge/builtin_routines/text_processing')
from text_processing import TextClipper

# As part of FlowForge
from flowforge.builtin_routines.text_processing import TextClipper
```

## Testing

Run tests from the package directory:

```bash
cd flowforge/builtin_routines/text_processing
python -m unittest tests.test_text_processing -v
```

## Examples

See `tests/test_text_processing.py` for comprehensive examples.

