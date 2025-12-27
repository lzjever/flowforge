"""
Retry handler routine.

Handles retry logic for operations that may fail.
"""
from __future__ import annotations
from typing import Dict, Any, Callable, Optional, List
import time
from flowforge.routine import Routine


class RetryHandler(Routine):
    """Routine for handling retry logic.
    
    This routine wraps operations with retry logic, useful for handling
    transient failures and network operations.
    
    Features:
    - Configurable retry attempts
    - Exponential backoff
    - Custom retry conditions
    - Detailed retry statistics
    
    Examples:
        >>> retry_handler = RetryHandler()
        >>> retry_handler.set_config(
        ...     max_retries=3,
        ...     retry_delay=1.0,
        ...     backoff_multiplier=2.0
        ... )
        >>> retry_handler.define_slot("input", handler=retry_handler.execute_with_retry)
        >>> retry_handler.define_event("success", ["result", "attempts"])
        >>> retry_handler.define_event("failure", ["error", "attempts"])
    """
    
    def __init__(self):
        """Initialize RetryHandler routine."""
        super().__init__()
        
        # Set default configuration
        self.set_config(
            max_retries=3,
            retry_delay=1.0,  # Initial delay in seconds
            backoff_multiplier=2.0,  # Exponential backoff multiplier
            retryable_exceptions=[Exception],  # List of exception types to retry
            retry_condition=None  # Optional function to determine if should retry
        )
        
        # Define input slot
        self.input_slot = self.define_slot("input", handler=self._handle_input)
        
        # Define output events
        self.success_event = self.define_event("success", ["result", "attempts", "total_time"])
        self.failure_event = self.define_event("failure", ["error", "attempts", "total_time"])
    
    def _handle_input(self, operation: Callable = None, **kwargs):
        """Handle input operation and execute with retry logic.
        
        Args:
            operation: Callable to execute. Can be:
                - A function
                - A dict with "func" key and optional "args"/"kwargs"
            **kwargs: Additional data from slot. Can contain:
                - "operation" or "func": The callable to execute
                - "args": List of positional arguments
                - "kwargs": Dict of keyword arguments for the operation
        """
        # Extract operation from kwargs if not provided directly
        if operation is None:
            if "operation" in kwargs:
                operation = kwargs["operation"]
            elif "func" in kwargs:
                operation = kwargs["func"]
            elif len(kwargs) == 1:
                operation = list(kwargs.values())[0]
            else:
                operation = kwargs.get("operation") or kwargs.get("func")
        
        # Track statistics
        self._track_operation("retry_operations")
        
        max_retries = self.get_config("max_retries", 3)
        retry_delay = self.get_config("retry_delay", 1.0)
        backoff_multiplier = self.get_config("backoff_multiplier", 2.0)
        retryable_exceptions = self.get_config("retryable_exceptions", [Exception])
        retry_condition = self.get_config("retry_condition", None)
        
        # Parse operation if it's a dict
        if isinstance(operation, dict):
            op_func = operation.get("func")
            op_args = operation.get("args", [])
            op_kwargs = operation.get("kwargs", {})
            # Merge with kwargs if provided
            if "args" in kwargs:
                op_args.extend(kwargs["args"])
            if "kwargs" in kwargs:
                op_kwargs.update(kwargs["kwargs"])
        else:
            op_func = operation
            op_args = kwargs.get("args", [])
            op_kwargs = {k: v for k, v in kwargs.items() if k not in ["args", "operation", "func"]}
        
        if not callable(op_func):
            self.emit("failure",
                error="Operation is not callable",
                attempts=0,
                total_time=0.0
            )
            return
        
        # Execute with retry
        attempts = 0
        start_time = time.time()
        
        while attempts <= max_retries:
            attempts += 1
            try:
                # Execute operation
                result = op_func(*op_args, **op_kwargs)
                
                # Check retry condition if provided
                if retry_condition and callable(retry_condition):
                    should_retry = retry_condition(result)
                    if should_retry and attempts <= max_retries:
                        # Retry based on condition
                        delay = retry_delay * (backoff_multiplier ** (attempts - 1))
                        time.sleep(delay)
                        continue
                
                # Success
                total_time = time.time() - start_time
                self._track_operation("retry_operations", success=True, attempts=attempts, total_time=total_time)
                self.set_stat("last_success_attempts", attempts)
                
                self.emit("success",
                    result=result,
                    attempts=attempts,
                    total_time=total_time
                )
                return
            
            except Exception as e:
                error_type = type(e).__name__
                
                # Check if exception is retryable
                is_retryable = any(isinstance(e, exc_type) for exc_type in retryable_exceptions)
                
                if not is_retryable or attempts > max_retries:
                    # Don't retry or max retries reached
                    total_time = time.time() - start_time
                    self._track_operation("retry_operations", success=False, 
                                         attempts=attempts, error=str(e), 
                                         error_type=error_type, total_time=total_time)
                    self.set_stat("last_failure_attempts", attempts)
                    
                    self.emit("failure",
                        error=str(e),
                        attempts=attempts,
                        total_time=total_time
                    )
                    return
                
                # Calculate delay and retry
                delay = retry_delay * (backoff_multiplier ** (attempts - 1))
                self._track_operation("retry_attempts", success=False,
                                    attempt=attempts, error=str(e),
                                    error_type=error_type, delay=delay)
                
                if attempts <= max_retries:
                    time.sleep(delay)

