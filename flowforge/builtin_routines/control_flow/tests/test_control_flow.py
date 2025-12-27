"""
Comprehensive test cases for built-in routines.

Tests all routines to ensure they work correctly and handle edge cases.
"""
import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from flowforge import Flow
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from flowforge.builtin_routines.control_flow import (
    ConditionalRouter,
    RetryHandler,
)
from flowforge.utils.serializable import Serializable
from flowforge.slot import Slot


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


