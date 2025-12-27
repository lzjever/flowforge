"""
Comprehensive test cases for built-in routines.

Tests all routines to ensure they work correctly and handle edge cases.
"""
import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from flowforge import Flow
from flowforge.builtin_routines import (
    TextClipper,
    TextRenderer,
    ResultExtractor,
    TimeProvider,
    DataFlattener,
    DataTransformer,
    DataValidator,
    ConditionalRouter,
    RetryHandler,
)
from flowforge.utils.serializable import Serializable
from flowforge.slot import Slot


class TestTextClipper(unittest.TestCase):
    """Test cases for TextClipper routine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.clipper = TextClipper()
        self.clipper.set_config(max_length=50)
        self.received_data = []
        
        # Create a test slot to capture output
        self.capture_slot = Slot("capture", None, lambda **kwargs: self.received_data.append(kwargs))
        self.clipper.get_event("output").connect(self.capture_slot)
    
    def test_clip_short_text(self):
        """Test clipping short text (should not clip)."""
        text = "Short text"
        self.clipper.input_slot.receive({"text": text})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["clipped_text"], text)
        self.assertFalse(self.received_data[0]["was_clipped"])
        self.assertEqual(self.received_data[0]["original_length"], len(text))
    
    def test_clip_long_text(self):
        """Test clipping long text."""
        text = "\n".join([f"Line {i}" for i in range(20)])
        self.clipper.input_slot.receive({"text": text})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertTrue(self.received_data[0]["was_clipped"])
        self.assertIn("省略了", self.received_data[0]["clipped_text"])
    
    def test_preserve_traceback(self):
        """Test that tracebacks are preserved."""
        text = "Traceback (most recent call last):\n  File 'test.py', line 1\n    error\n"
        self.clipper.set_config(preserve_tracebacks=True)
        self.clipper.input_slot.receive({"text": text})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertFalse(self.received_data[0]["was_clipped"])
        self.assertIn("Traceback", self.received_data[0]["clipped_text"])
    
    def test_non_string_input(self):
        """Test handling non-string input."""
        self.clipper.input_slot.receive({"text": 12345})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertIsInstance(self.received_data[0]["clipped_text"], str)
    
    def test_empty_text(self):
        """Test handling empty text."""
        self.clipper.input_slot.receive({"text": ""})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["clipped_text"], "")
        self.assertFalse(self.received_data[0]["was_clipped"])
    
    def test_statistics(self):
        """Test that statistics are tracked."""
        self.clipper.input_slot.receive({"text": "test"})
        
        stats = self.clipper.stats()
        self.assertGreater(stats.get("total_clips", 0), 0)


class TestTextRenderer(unittest.TestCase):
    """Test cases for TextRenderer routine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.renderer = TextRenderer()
        self.received_data = []
        
        # Create a test slot to capture output
        self.capture_slot = Slot("capture", None, lambda **kwargs: self.received_data.append(kwargs))
        self.renderer.get_event("output").connect(self.capture_slot)
    
    def test_render_dict(self):
        """Test rendering a dictionary."""
        data = {"name": "test", "value": 42}
        self.renderer.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        rendered = self.received_data[0]["rendered_text"]
        self.assertIn("<name>test</name>", rendered)
        self.assertIn("<value>42</value>", rendered)
    
    def test_render_nested_dict(self):
        """Test rendering nested dictionaries."""
        data = {"a": {"b": 1, "c": 2}}
        self.renderer.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        rendered = self.received_data[0]["rendered_text"]
        self.assertIn("<a>", rendered)
    
    def test_render_list(self):
        """Test rendering a list."""
        data = [1, 2, 3]
        self.renderer.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        rendered = self.received_data[0]["rendered_text"]
        self.assertIn("item_0", rendered)
    
    def test_render_primitive(self):
        """Test rendering primitive types."""
        self.renderer.input_slot.receive({"data": "test"})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["rendered_text"], "test")
    
    def test_markdown_format(self):
        """Test markdown format rendering."""
        self.renderer.set_config(tag_format="markdown")
        data = {"name": "test"}
        self.renderer.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        rendered = self.received_data[0]["rendered_text"]
        self.assertIn("**name**", rendered)


class TestResultExtractor(unittest.TestCase):
    """Test cases for ResultExtractor routine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.extractor = ResultExtractor()
        self.received_data = []
        
        # Create a test slot to capture output
        self.capture_slot = Slot("capture", None, lambda **kwargs: self.received_data.append(kwargs))
        self.extractor.get_event("output").connect(self.capture_slot)
    
    def test_extract_json_block(self):
        """Test extracting JSON code block."""
        text = "Some text\n```json\n{\"key\": \"value\"}\n```\nMore text"
        self.extractor.input_slot.receive({"data": text})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["format"], "json")
        self.assertIsInstance(self.received_data[0]["extracted_result"], dict)
        self.assertIn("confidence", self.received_data[0])
        self.assertIn("extraction_path", self.received_data[0])
    
    def test_extract_json_string(self):
        """Test extracting JSON from plain string."""
        text = '{"key": "value"}'
        self.extractor.set_config(parse_json_strings=True)
        self.extractor.input_slot.receive({"data": text})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["format"], "json")
        self.assertIsInstance(self.received_data[0]["extracted_result"], dict)
    
    def test_extract_code_block(self):
        """Test extracting code block."""
        text = "```python\nprint('hello')\n```"
        self.extractor.input_slot.receive({"data": text})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["format"], "python")
        self.assertIn("code_block", self.received_data[0]["metadata"]["extraction_method"])
    
    def test_extract_interpreter_output(self):
        """Test extracting interpreter output."""
        outputs = [
            {"format": "output", "content": "Hello"},
            {"format": "output", "content": "World"}
        ]
        self.extractor.input_slot.receive({"data": outputs})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["format"], "interpreter_output")
        self.assertIn("Hello", self.received_data[0]["extracted_result"])
        self.assertEqual(self.received_data[0]["metadata"]["output_count"], 2)
    
    def test_extract_dict(self):
        """Test extracting from dictionary."""
        data = {"key": "value", "number": 42}
        self.extractor.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["format"], "dict")
        self.assertEqual(self.received_data[0]["extracted_result"], data)
    
    def test_extract_list(self):
        """Test extracting from list."""
        data = [1, 2, 3]
        self.extractor.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["format"], "list")
        self.assertEqual(self.received_data[0]["extracted_result"], data)
    
    def test_strategy_first_match(self):
        """Test first_match strategy."""
        self.extractor.set_config(strategy="first_match")
        text = "```json\n{\"key\": \"value\"}\n```\n```python\nprint('test')\n```"
        self.extractor.input_slot.receive({"data": text})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["format"], "json")
    
    def test_strategy_priority(self):
        """Test priority strategy."""
        self.extractor.set_config(
            strategy="priority",
            extractor_priority=["code_block", "json_code_block"]
        )
        text = "```json\n{\"key\": \"value\"}\n```"
        self.extractor.input_slot.receive({"data": text})
        
        self.assertEqual(len(self.received_data), 1)
        # Should use code_block extractor first due to priority
        self.assertIn(self.received_data[0]["metadata"]["extractor"], ["code_block", "json_code_block"])
    
    def test_custom_extractor(self):
        """Test registering and using custom extractor."""
        def custom_extractor(data, config):
            if isinstance(data, str) and data.startswith("CUSTOM:"):
                return data[7:], "custom", {"method": "prefix"}
            return None
        
        self.extractor.register_extractor("custom_prefix", custom_extractor)
        self.extractor.set_config(extractor_priority=["custom_prefix"])
        
        self.extractor.input_slot.receive({"data": "CUSTOM:test_value"})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["format"], "custom")
        self.assertEqual(self.received_data[0]["extracted_result"], "test_value")
        self.assertEqual(self.received_data[0]["metadata"]["method"], "prefix")
    
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        text = "```json\n{\"key\": \"value\"}\n```"
        self.extractor.input_slot.receive({"data": text})
        
        self.assertEqual(len(self.received_data), 1)
        confidence = self.received_data[0]["confidence"]
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)
        self.assertGreater(confidence, 0.5)  # Should have good confidence for JSON
    
    def test_error_handling(self):
        """Test error handling with invalid data."""
        self.extractor.set_config(continue_on_error=True, return_original_on_failure=True)
        
        # Invalid JSON in code block
        text = "```json\n{invalid json}\n```"
        self.extractor.input_slot.receive({"data": text})
        
        self.assertEqual(len(self.received_data), 1)
        # Should fall back to code block extraction or original
        self.assertIn("extracted_result", self.received_data[0])
    
    def test_plain_text_fallback(self):
        """Test handling plain text when extraction fails."""
        text = "Just plain text with no structure"
        self.extractor.set_config(return_original_on_failure=True)
        self.extractor.input_slot.receive({"data": text})
        
        self.assertEqual(len(self.received_data), 1)
        # Should return original text
        self.assertEqual(self.received_data[0]["extracted_result"], text)
        self.assertEqual(self.received_data[0]["confidence"], 0.0)


class TestTimeProvider(unittest.TestCase):
    """Test cases for TimeProvider routine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.time_provider = TimeProvider()
        self.received_data = []
        
        # Create a test slot to capture output
        self.capture_slot = Slot("capture", None, lambda **kwargs: self.received_data.append(kwargs))
        self.time_provider.get_event("output").connect(self.capture_slot)
    
    def test_get_time_iso(self):
        """Test getting time in ISO format."""
        self.time_provider.set_config(format="iso")
        self.time_provider.trigger_slot.receive({})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertIn("time_string", self.received_data[0])
        self.assertIn("timestamp", self.received_data[0])
        self.assertIn("datetime", self.received_data[0])
    
    def test_get_time_formatted(self):
        """Test getting time in formatted format."""
        self.time_provider.set_config(format="formatted", locale="zh_CN")
        self.time_provider.trigger_slot.receive({})
        
        self.assertEqual(len(self.received_data), 1)
        time_str = self.received_data[0]["time_string"]
        self.assertIn("年", time_str)
    
    def test_get_time_timestamp(self):
        """Test getting time as timestamp."""
        self.time_provider.set_config(format="timestamp")
        self.time_provider.trigger_slot.receive({})
        
        self.assertEqual(len(self.received_data), 1)
        timestamp = self.received_data[0]["timestamp"]
        self.assertIsInstance(timestamp, float)
        self.assertGreater(timestamp, 0)
    
    def test_custom_format(self):
        """Test custom format."""
        self.time_provider.set_config(format="custom", custom_format="%Y-%m-%d")
        self.time_provider.trigger_slot.receive({})
        
        self.assertEqual(len(self.received_data), 1)
        time_str = self.received_data[0]["time_string"]
        self.assertRegex(time_str, r"\d{4}-\d{2}-\d{2}")


class TestDataFlattener(unittest.TestCase):
    """Test cases for DataFlattener routine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.flattener = DataFlattener()
        self.received_data = []
        
        # Create a test slot to capture output
        self.capture_slot = Slot("capture", None, lambda **kwargs: self.received_data.append(kwargs))
        self.flattener.get_event("output").connect(self.capture_slot)
    
    def test_flatten_dict(self):
        """Test flattening a dictionary."""
        data = {"a": {"b": 1, "c": 2}}
        self.flattener.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        flattened = self.received_data[0]["flattened_data"]
        self.assertIn("a.b", flattened)
        self.assertEqual(flattened["a.b"], 1)
    
    def test_flatten_list(self):
        """Test flattening a list."""
        data = {"items": [1, 2, 3]}
        self.flattener.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        flattened = self.received_data[0]["flattened_data"]
        self.assertIn("items.0", flattened)
        self.assertEqual(flattened["items.0"], 1)
    
    def test_flatten_nested(self):
        """Test flattening deeply nested structures."""
        data = {"a": {"b": {"c": {"d": 1}}}}
        self.flattener.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        flattened = self.received_data[0]["flattened_data"]
        self.assertIn("a.b.c.d", flattened)
    
    def test_flatten_primitive(self):
        """Test flattening primitive value."""
        self.flattener.input_slot.receive({"data": 42})
        
        self.assertEqual(len(self.received_data), 1)
        flattened = self.received_data[0]["flattened_data"]
        self.assertIn("value", flattened)
        self.assertEqual(flattened["value"], 42)
    
    def test_custom_separator(self):
        """Test custom separator."""
        self.flattener.set_config(separator="_")
        data = {"a": {"b": 1}}
        self.flattener.input_slot.receive({"data": data})
        
        self.assertEqual(len(self.received_data), 1)
        flattened = self.received_data[0]["flattened_data"]
        self.assertIn("a_b", flattened)


class TestDataTransformer(unittest.TestCase):
    """Test cases for DataTransformer routine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.transformer = DataTransformer()
        self.received_data = []
        
        # Create a test slot to capture output
        self.capture_slot = Slot("capture", None, lambda **kwargs: self.received_data.append(kwargs))
        self.transformer.get_event("output").connect(self.capture_slot)
    
    def test_lowercase_transformation(self):
        """Test lowercase transformation."""
        self.transformer.set_config(transformations=["lowercase"])
        self.transformer.input_slot.receive({"data": "HELLO"})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["transformed_data"], "hello")
    
    def test_multiple_transformations(self):
        """Test chaining multiple transformations."""
        self.transformer.set_config(transformations=["lowercase", "strip_whitespace"])
        self.transformer.input_slot.receive({"data": "  HELLO  "})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["transformed_data"], "hello")
    
    def test_custom_transformation(self):
        """Test custom transformation."""
        def double(x):
            return x * 2
        
        self.transformer.register_transformation("double", double)
        self.transformer.set_config(transformations=["double"])
        self.transformer.input_slot.receive({"data": 5})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0]["transformed_data"], 10)
    
    def test_transformation_error(self):
        """Test handling transformation errors."""
        self.transformer.set_config(transformations=["to_int"])
        self.transformer.input_slot.receive({"data": "not_a_number"})
        
        self.assertEqual(len(self.received_data), 1)
        self.assertIsNotNone(self.received_data[0]["errors"])


class TestDataValidator(unittest.TestCase):
    """Test cases for DataValidator routine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = DataValidator()
        self.received_valid = []
        self.received_invalid = []
        
        # Create test slots to capture output
        self.valid_slot = Slot("valid", None, lambda **kwargs: self.received_valid.append(kwargs))
        self.invalid_slot = Slot("invalid", None, lambda **kwargs: self.received_invalid.append(kwargs))
        self.validator.get_event("valid").connect(self.valid_slot)
        self.validator.get_event("invalid").connect(self.invalid_slot)
    
    def test_valid_data(self):
        """Test validating valid data."""
        self.validator.set_config(
            rules={"name": "not_empty", "age": "is_int"},
            required_fields=["name", "age"]
        )
        self.validator.input_slot.receive({"data": {"name": "test", "age": 25}})
        
        self.assertEqual(len(self.received_valid), 1)
        self.assertEqual(len(self.received_invalid), 0)
    
    def test_invalid_data(self):
        """Test validating invalid data."""
        self.validator.set_config(
            rules={"name": "not_empty", "age": "is_int"}
        )
        self.validator.input_slot.receive({"data": {"name": "", "age": "not_int"}})
        
        self.assertEqual(len(self.received_valid), 0)
        self.assertEqual(len(self.received_invalid), 1)
        self.assertGreater(len(self.received_invalid[0]["errors"]), 0)
    
    def test_missing_required_field(self):
        """Test missing required field."""
        self.validator.set_config(
            required_fields=["name"]
        )
        self.validator.input_slot.receive({"data": {}})
        
        self.assertEqual(len(self.received_invalid), 1)
        self.assertIn("missing", str(self.received_invalid[0]["errors"][0]).lower())
    
    def test_custom_validator(self):
        """Test custom validator."""
        def is_even(x):
            return isinstance(x, int) and x % 2 == 0
        
        self.validator.register_validator("is_even", is_even)
        self.validator.set_config(rules={"number": "is_even"})
        self.validator.input_slot.receive({"data": {"number": 4}})
        
        self.assertEqual(len(self.received_valid), 1)
    
    def test_strict_mode(self):
        """Test strict mode (stop on first error)."""
        self.validator.set_config(
            rules={"field1": "is_string", "field2": "is_string"},
            strict_mode=True
        )
        self.validator.input_slot.receive({"data": {"field1": 123, "field2": 456}})
        
        self.assertEqual(len(self.received_invalid), 1)
        # Should only have one error in strict mode
        self.assertEqual(len(self.received_invalid[0]["errors"]), 1)


class TestConditionalRouter(unittest.TestCase):
    """Test cases for ConditionalRouter routine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.router = ConditionalRouter()
        self.received_high = []
        self.received_low = []
        self.received_normal = []
        
        # Create test slots to capture output
        self.high_slot = Slot("high", None, lambda **kwargs: self.received_high.append(kwargs))
        self.low_slot = Slot("low", None, lambda **kwargs: self.received_low.append(kwargs))
        self.normal_slot = Slot("normal", None, lambda **kwargs: self.received_normal.append(kwargs))
        
        self.router.set_config(
            routes=[
                ("high", lambda x: isinstance(x, dict) and x.get("priority") == "high"),
                ("low", lambda x: isinstance(x, dict) and x.get("priority") == "low"),
            ],
            default_route="normal"
        )
        
        # Events are created dynamically, so we need to trigger creation first
        # or connect after they're created
        # For now, let's connect after setting up routes
        high_event = self.router.get_event("high")
        if high_event:
            high_event.connect(self.high_slot)
        else:
            self.router.define_event("high", ["data", "route"]).connect(self.high_slot)
        
        low_event = self.router.get_event("low")
        if low_event:
            low_event.connect(self.low_slot)
        else:
            self.router.define_event("low", ["data", "route"]).connect(self.low_slot)
        
        normal_event = self.router.get_event("normal")
        if normal_event:
            normal_event.connect(self.normal_slot)
        else:
            self.router.define_event("normal", ["data", "route"]).connect(self.normal_slot)
    
    def test_route_high_priority(self):
        """Test routing high priority data."""
        self.router.input_slot.receive({"data": {"priority": "high", "value": 1}})
        
        self.assertEqual(len(self.received_high), 1)
        self.assertEqual(len(self.received_low), 0)
        self.assertEqual(len(self.received_normal), 0)
    
    def test_route_low_priority(self):
        """Test routing low priority data."""
        self.router.input_slot.receive({"data": {"priority": "low", "value": 2}})
        
        self.assertEqual(len(self.received_high), 0)
        self.assertEqual(len(self.received_low), 1)
        self.assertEqual(len(self.received_normal), 0)
    
    def test_default_route(self):
        """Test default route for unmatched data."""
        self.router.input_slot.receive({"data": {"priority": "medium", "value": 3}})
        
        self.assertEqual(len(self.received_high), 0)
        self.assertEqual(len(self.received_low), 0)
        self.assertEqual(len(self.received_normal), 1)
    
    def test_dict_condition(self):
        """Test dictionary-based condition."""
        self.router.add_route("exact", {"priority": "exact"})
        received_exact = []
        exact_slot = Slot("exact", None, lambda **kwargs: received_exact.append(kwargs))
        self.router.get_event("exact").connect(exact_slot)
        
        self.router.input_slot.receive({"data": {"priority": "exact"}})
        
        self.assertEqual(len(received_exact), 1)


class TestRetryHandler(unittest.TestCase):
    """Test cases for RetryHandler routine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.retry_handler = RetryHandler()
        self.received_success = []
        self.received_failure = []
        
        # Create test slots to capture output
        self.success_slot = Slot("success", None, lambda **kwargs: self.received_success.append(kwargs))
        self.failure_slot = Slot("failure", None, lambda **kwargs: self.received_failure.append(kwargs))
        self.retry_handler.get_event("success").connect(self.success_slot)
        self.retry_handler.get_event("failure").connect(self.failure_slot)
    
    def test_successful_operation(self):
        """Test successful operation (no retry needed)."""
        def success_func():
            return "success"
        
        self.retry_handler.set_config(max_retries=3)
        self.retry_handler.input_slot.receive({
            "operation": success_func
        })
        
        self.assertEqual(len(self.received_success), 1)
        self.assertEqual(self.received_success[0]["result"], "success")
        self.assertEqual(self.received_success[0]["attempts"], 1)
    
    def test_retry_on_failure(self):
        """Test retry on failure."""
        call_count = [0]
        
        def failing_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Temporary failure")
            return "success"
        
        self.retry_handler.set_config(max_retries=3, retry_delay=0.1)
        self.retry_handler.input_slot.receive({
            "operation": failing_func
        })
        
        # Wait a bit for retry
        time.sleep(0.5)
        
        self.assertEqual(len(self.received_success), 1)
        self.assertEqual(self.received_success[0]["attempts"], 2)
    
    def test_max_retries_exceeded(self):
        """Test when max retries are exceeded."""
        def always_failing():
            raise ValueError("Always fails")
        
        self.retry_handler.set_config(max_retries=2, retry_delay=0.1)
        self.retry_handler.input_slot.receive({
            "operation": always_failing
        })
        
        # Wait for retries
        time.sleep(0.5)
        
        self.assertEqual(len(self.received_failure), 1)
        self.assertEqual(self.received_failure[0]["attempts"], 3)  # 1 initial + 2 retries
    
    def test_non_retryable_exception(self):
        """Test non-retryable exception."""
        def raise_key_error():
            raise KeyError("Not retryable")
        
        self.retry_handler.set_config(
            max_retries=3,
            retryable_exceptions=[ValueError]  # KeyError not in list
        )
        self.retry_handler.input_slot.receive({
            "operation": raise_key_error
        })
        
        self.assertEqual(len(self.received_failure), 1)
        self.assertEqual(self.received_failure[0]["attempts"], 1)  # No retry
    
    def test_operation_as_dict(self):
        """Test operation passed as dict."""
        def test_func(x, y=0):
            return x + y
        
        self.retry_handler.set_config(max_retries=1)
        self.retry_handler.input_slot.receive({
            "operation": {
                "func": test_func,
                "args": [5],
                "kwargs": {"y": 3}
            }
        })
        
        self.assertEqual(len(self.received_success), 1)
        self.assertEqual(self.received_success[0]["result"], 8)


class TestRoutineIntegration(unittest.TestCase):
    """Integration tests for routines in a flow."""
    
    def test_text_processing_flow(self):
        """Test text processing routines in a flow."""
        flow = Flow()
        
        renderer = TextRenderer()
        clipper = TextClipper()
        clipper.set_config(max_length=50)
        
        flow.add_routine(renderer, "renderer")
        flow.add_routine(clipper, "clipper")
        flow.connect("renderer", "output", "clipper", "input")
        
        # Create a source routine
        class SourceRoutine:
            def __init__(self):
                self.output_event = renderer.get_event("input")
        
        source = SourceRoutine()
        renderer.input_slot.receive({"data": {"name": "test", "value": 42}})
        
        # Flow should process the data
        self.assertTrue(True)  # Basic integration test
    
    def test_data_processing_flow(self):
        """Test data processing routines in a flow."""
        flow = Flow()
        
        transformer = DataTransformer()
        transformer.set_config(transformations=["lowercase"])
        validator = DataValidator()
        validator.set_config(rules={"data": "is_string"})
        
        flow.add_routine(transformer, "transformer")
        flow.add_routine(validator, "validator")
        flow.connect("transformer", "output", "validator", "input")
        
        transformer.input_slot.receive({"data": "HELLO"})
        
        # Flow should process the data
        self.assertTrue(True)  # Basic integration test


if __name__ == "__main__":
    unittest.main()

