#!/usr/bin/env python
"""
Complex Routine Demo

This file contains a highly complex routine with extensive documentation
to demonstrate the capabilities of the routine analyzer.
"""

from routilux import Routine


class ComplexDataProcessor(Routine):
    """Complex data processing routine with multiple input/output channels.
    
    This routine demonstrates advanced workflow patterns including:
    - Multiple input slots with different merge strategies
    - Conditional event emission based on data validation
    - Complex configuration management
    - Error handling and recovery
    - Data transformation pipelines
    - Aggregation and filtering
    
    The routine processes data through multiple stages:
    1. Data collection from multiple sources (slots)
    2. Validation and filtering
    3. Transformation and enrichment
    4. Aggregation
    5. Output routing based on priority
    
    Example Usage:
        >>> processor = ComplexDataProcessor()
        >>> processor.set_config(
        ...     max_batch_size=1000,
        ...     enable_caching=True,
        ...     validation_rules=["required", "type_check", "range_check"]
        ... )
        >>> flow.add_routine(processor, "processor")
        >>> flow.connect(source1_id, "output", "processor", "primary_input")
        >>> flow.connect(source2_id, "output", "processor", "secondary_input")
    """
    
    def __init__(self):
        """Initialize the complex data processor.
        
        Sets up all slots, events, and default configuration.
        """
        super().__init__()
        
        # Configuration with detailed defaults
        self.set_config(
            # Processing parameters
            max_batch_size=500,              # Maximum items to process in one batch
            batch_timeout=30.0,              # Timeout in seconds for batch processing
            enable_caching=True,              # Enable result caching
            cache_ttl=3600,                   # Cache time-to-live in seconds
            
            # Validation settings
            validation_rules=[               # List of validation rules to apply
                "required",                  # Check required fields
                "type_check",                # Validate data types
                "range_check"                # Check value ranges
            ],
            strict_validation=True,          # Fail on first validation error
            allow_partial_results=False,      # Require all validations to pass
            
            # Transformation settings
            transformation_pipeline=[        # Ordered list of transformations
                "normalize",                 # Normalize data format
                "enrich",                    # Add metadata
                "deduplicate"                # Remove duplicates
            ],
            enable_parallel_transform=False,  # Use parallel processing
            
            # Aggregation settings
            aggregation_mode="weighted_mean", # Aggregation method
            aggregation_window=60,           # Time window in seconds
            min_samples=5,                   # Minimum samples for aggregation
            
            # Output routing
            priority_thresholds={             # Priority routing thresholds
                "high": 0.8,                 # High priority threshold
                "medium": 0.5,               # Medium priority threshold
                "low": 0.0                   # Low priority threshold
            },
            default_priority="medium",        # Default priority if no match
            
            # Error handling
            max_retries=3,                   # Maximum retry attempts
            retry_backoff=2.0,               # Exponential backoff multiplier
            error_threshold=0.1              # Error rate threshold (10%)
        )
        
        # Primary input slot - receives main data stream
        # Uses append strategy to accumulate data from multiple sources
        self.primary_input = self.define_slot(
            "primary_input",
            handler=self._handle_primary_input,
            merge_strategy="append"  # Accumulate data from multiple sources
        )
        
        # Secondary input slot - receives supplementary data
        # Uses override strategy to replace previous data
        self.secondary_input = self.define_slot(
            "secondary_input",
            handler=self._handle_secondary_input,
            merge_strategy="override"  # Latest data replaces previous
        )
        
        # Metadata input slot - receives metadata updates
        # Uses custom merge strategy for deep merging
        self.metadata_input = self.define_slot(
            "metadata_input",
            handler=self._handle_metadata_input,
            merge_strategy=self._merge_metadata  # Custom deep merge
        )
        
        # Control input slot - receives control commands
        # Used for runtime configuration updates
        self.control_input = self.define_slot(
            "control_input",
            handler=self._handle_control_input,
            merge_strategy="override"  # Latest command takes precedence
        )
        
        # Output events
        # High priority output - for urgent data
        self.high_priority_output = self.define_event(
            "high_priority_output",
            [
                "processed_data",      # The processed data
                "metadata",            # Associated metadata
                "priority_score",      # Calculated priority score (0.0-1.0)
                "processing_time",     # Time taken to process (seconds)
                "batch_id"             # Unique batch identifier
            ]
        )
        
        # Medium priority output - for normal data
        self.medium_priority_output = self.define_event(
            "medium_priority_output",
            [
                "processed_data",      # The processed data
                "metadata",            # Associated metadata
                "priority_score",      # Calculated priority score
                "processing_time",     # Time taken to process
                "batch_id"             # Unique batch identifier
            ]
        )
        
        # Low priority output - for background processing
        self.low_priority_output = self.define_event(
            "low_priority_output",
            [
                "processed_data",      # The processed data
                "metadata",            # Associated metadata
                "priority_score",      # Calculated priority score
                "processing_time",     # Time taken to process
                "batch_id"             # Unique batch identifier
            ]
        )
        
        # Error output - for processing errors
        self.error_output = self.define_event(
            "error_output",
            [
                "error_type",          # Type of error (validation, transform, etc.)
                "error_message",        # Human-readable error message
                "error_code",           # Machine-readable error code
                "failed_data",          # The data that failed processing
                "retry_count",          # Number of retry attempts
                "stack_trace"           # Error stack trace (if available)
            ]
        )
        
        # Status output - for processing status updates
        self.status_output = self.define_event(
            "status_output",
            [
                "status",              # Current status (processing, completed, failed)
                "progress",             # Progress percentage (0-100)
                "items_processed",      # Number of items processed
                "items_failed",         # Number of items that failed
                "current_batch_id"     # Current batch being processed
            ]
        )
    
    def _handle_primary_input(self, data=None, source=None, timestamp=None, **kwargs):
        """Handle primary input data stream.
        
        This is the main data processing handler. It receives data from
        the primary input slot and processes it through the complete pipeline:
        validation -> transformation -> aggregation -> routing.
        
        Args:
            data: The main data payload. Can be a single item or a list of items.
            source: Optional source identifier for tracking data origin.
            timestamp: Optional timestamp for the data.
            **kwargs: Additional metadata and parameters.
        
        Processing Flow:
            1. Extract and normalize input data
            2. Validate data according to configured rules
            3. Apply transformation pipeline
            4. Calculate priority score
            5. Route to appropriate output event
        
        Emits:
            - high_priority_output: If priority_score >= high threshold
            - medium_priority_output: If priority_score >= medium threshold
            - low_priority_output: Otherwise
            - error_output: If processing fails
            - status_output: Periodic status updates
        """
        # Extract data
        if isinstance(data, dict):
            data_value = data.get("data", data)
        else:
            data_value = data
        
        # Process through pipeline
        try:
            validated_data = self._validate_data(data_value)
            transformed_data = self._transform_data(validated_data)
            priority_score = self._calculate_priority(transformed_data)
            
            # Route based on priority
            if priority_score >= self.get_config("priority_thresholds", {}).get("high", 0.8):
                self.emit("high_priority_output",
                         processed_data=transformed_data,
                         metadata={"source": source, "timestamp": timestamp},
                         priority_score=priority_score,
                         processing_time=0.1,
                         batch_id="batch_001")
            elif priority_score >= self.get_config("priority_thresholds", {}).get("medium", 0.5):
                self.emit("medium_priority_output",
                         processed_data=transformed_data,
                         metadata={"source": source, "timestamp": timestamp},
                         priority_score=priority_score,
                         processing_time=0.1,
                         batch_id="batch_001")
            else:
                self.emit("low_priority_output",
                         processed_data=transformed_data,
                         metadata={"source": source, "timestamp": timestamp},
                         priority_score=priority_score,
                         processing_time=0.1,
                         batch_id="batch_001")
        except Exception as e:
            self.emit("error_output",
                     error_type="processing",
                     error_message=str(e),
                     error_code="PROC_001",
                     failed_data=data_value,
                     retry_count=0,
                     stack_trace=None)
    
    def _handle_secondary_input(self, data=None, source=None, **kwargs):
        """Handle secondary input data stream.
        
        Processes supplementary data that complements the primary input.
        This data is merged with primary data during aggregation.
        
        Args:
            data: Supplementary data payload.
            source: Source identifier.
            **kwargs: Additional parameters.
        
        Emits:
            - status_output: Status updates
        """
        # Process secondary data
        self.emit("status_output",
                 status="processing",
                 progress=50,
                 items_processed=1,
                 items_failed=0,
                 current_batch_id="batch_001")
    
    def _handle_metadata_input(self, data=None, metadata=None, **kwargs):
        """Handle metadata input updates.
        
        Receives metadata updates that are deep-merged with existing metadata.
        Used for enriching data with additional context.
        
        Args:
            data: Optional data payload.
            metadata: Metadata dictionary to merge.
            **kwargs: Additional metadata fields.
        
        Emits:
            - status_output: Metadata update confirmation
        """
        # Merge metadata
        merged_metadata = self._merge_metadata(
            self.get_config("metadata", {}),
            metadata or kwargs
        )
        self.set_config(metadata=merged_metadata)
    
    def _handle_control_input(self, command=None, **kwargs):
        """Handle control commands for runtime configuration.
        
        Allows dynamic reconfiguration of the processor at runtime.
        Supported commands: pause, resume, update_config, reset_stats.
        
        Args:
            command: Control command name.
            **kwargs: Command-specific parameters.
        
        Emits:
            - status_output: Command execution status
        """
        if command == "pause":
            self.set_config(paused=True)
        elif command == "resume":
            self.set_config(paused=False)
        elif command == "update_config":
            self.set_config(**kwargs)
    
    def _validate_data(self, data):
        """Validate input data according to configured rules.
        
        Args:
            data: Data to validate.
        
        Returns:
            Validated data.
        
        Raises:
            ValueError: If validation fails.
        """
        rules = self.get_config("validation_rules", [])
        if "required" in rules:
            if data is None:
                raise ValueError("Data is required")
        return data
    
    def _transform_data(self, data):
        """Transform data through the configured pipeline.
        
        Args:
            data: Data to transform.
        
        Returns:
            Transformed data.
        """
        pipeline = self.get_config("transformation_pipeline", [])
        result = data
        for transform in pipeline:
            if transform == "normalize":
                result = str(result).lower() if isinstance(result, str) else result
            elif transform == "enrich":
                result = {"data": result, "enriched": True}
            elif transform == "deduplicate":
                # Simple deduplication
                if isinstance(result, list):
                    result = list(dict.fromkeys(result))
        return result
    
    def _calculate_priority(self, data):
        """Calculate priority score for data routing.
        
        Args:
            data: Data to score.
        
        Returns:
            Priority score between 0.0 and 1.0.
        """
        # Simple priority calculation
        if isinstance(data, dict):
            return 0.7
        elif isinstance(data, list):
            return 0.5
        else:
            return 0.3
    
    def _merge_metadata(self, old_data, new_data):
        """Custom merge strategy for metadata.
        
        Performs deep merge of metadata dictionaries, combining
        nested structures intelligently.
        
        Args:
            old_data: Existing metadata dictionary.
            new_data: New metadata to merge.
        
        Returns:
            Merged metadata dictionary.
        """
        if not old_data:
            return new_data.copy() if isinstance(new_data, dict) else {}
        if not isinstance(new_data, dict):
            return old_data
        
        merged = old_data.copy()
        for key, value in new_data.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_metadata(merged[key], value)
            else:
                merged[key] = value
        return merged

