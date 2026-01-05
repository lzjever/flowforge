#!/usr/bin/env python
"""
Data Processing Example: Multi-stage data processing pipeline

This example demonstrates:
- Complex data flow with multiple stages
- Parameter mapping
- Statistics tracking
"""

from routilux import Flow, Routine


class InputReader(Routine):
    """Reads input data"""

    def __init__(self):
        super().__init__()
        # Define trigger slot for entry routine
        self.trigger_slot = self.define_slot("trigger", handler=self._handle_trigger)
        self.output_event = self.define_event("output", ["raw_data"])

    def _handle_trigger(self, filename=None, **kwargs):
        """Handle trigger and simulate reading from a file"""
        raw_data = filename or kwargs.get("filename", "sample_data.txt")
        # Execution state should be stored in JobState, not routine._stats
        self.emit("output", raw_data=raw_data)


class DataValidator(Routine):
    """Validates input data"""

    def __init__(self):
        super().__init__()
        self.input_slot = self.define_slot("input", handler=self.validate)
        self.output_event = self.define_event("output", ["validated_data"])
        self.error_event = self.define_event("error", ["error_message"])

    def validate(self, raw_data):
        """Validate the data"""
        if isinstance(raw_data, dict):
            data = raw_data.get("raw_data", raw_data)
        else:
            data = raw_data

        if data and len(str(data)) > 0:
            # Execution state should be stored in JobState, not routine._stats
            self.emit("output", validated_data=data)
        else:
            # Execution state should be stored in JobState, not routine._stats
            self.emit("error", error_message="Invalid data")


class DataTransformer(Routine):
    """Transforms validated data"""

    def __init__(self):
        super().__init__()
        self.input_slot = self.define_slot("input", handler=self.transform)
        self.output_event = self.define_event("output", ["transformed_data"])

    def transform(self, validated_data):
        """Transform the data"""
        if isinstance(validated_data, dict):
            data = validated_data.get("validated_data", validated_data)
        else:
            data = validated_data

        transformed = f"TRANSFORMED_{data.upper()}"
        # Execution state should be stored in JobState, not routine._stats
        self.emit("output", transformed_data=transformed)


class DataWriter(Routine):
    """Writes processed data"""

    def __init__(self):
        super().__init__()
        self.input_slot = self.define_slot("input", handler=self.write)
        self.written_data = []

    def write(self, transformed_data):
        """Write the data"""
        if isinstance(transformed_data, dict):
            data = transformed_data.get("transformed_data", transformed_data)
        else:
            data = transformed_data

        self.written_data.append(data)
        # Execution state should be stored in JobState, not routine._stats
        print(f"Written: {data}")


def main():
    """Main function"""
    # Create a flow
    flow = Flow(flow_id="data_processing")

    # Create routine instances
    reader = InputReader()
    validator = DataValidator()
    transformer = DataTransformer()
    writer = DataWriter()

    # Add routines to the flow
    reader_id = flow.add_routine(reader, "reader")
    validator_id = flow.add_routine(validator, "validator")
    transformer_id = flow.add_routine(transformer, "transformer")
    writer_id = flow.add_routine(writer, "writer")

    # Connect the pipeline
    flow.connect(reader_id, "output", validator_id, "input")
    flow.connect(validator_id, "output", transformer_id, "input")
    flow.connect(transformer_id, "output", writer_id, "input")

    # Execute the flow
    print("Executing data processing pipeline...")
    job_state = flow.execute(reader_id, entry_params={"filename": "data.txt"})

    # Check results
    print(f"\nExecution Status: {job_state.status}")
    print(f"Written Data: {writer.written_data}")
    # Execution state is tracked in JobState, not routine._stats
    print(f"Execution History: {len(job_state.execution_history)} records")

    assert job_state.status == "completed"
    assert len(writer.written_data) > 0


if __name__ == "__main__":
    main()
