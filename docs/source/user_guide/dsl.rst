DSL (Domain Specific Language)
================================

The DSL (Domain Specific Language) module allows you to define workflows declaratively using YAML or JSON. This is useful for:

* **Workflow as Code**: Define workflows in configuration files
* **Dynamic Loading**: Load workflows from external sources
* **Version Control**: Track workflow definitions separately from code
* **No-Code/Low-Code**: Enable non-developers to create workflows

**Important**: All routines in DSL must be registered in the ObjectFactory before use. 
The DSL uses factory names (e.g., "data_source") instead of class paths for security and portability.

Basic Usage
------------

YAML Workflow Definition:

.. code-block:: yaml

   flow_id: "data_processing_pipeline"
   execution:
     timeout: 300.0
   routines:
     extractor:
       class: "data_extractor"  # Factory name, not class path
       config:
         source: "database"
         batch_size: 100
     validator:
       class: "data_validator"  # Factory name
       config:
         rules:
           - "data is not None"
           - "data.get('id') is not None"
     transformer:
       class: "data_transformer"  # Factory name
       config:
         transformations:
           - "normalize"
           - "validate"
     exporter:
       class: "data_exporter"  # Factory name
       config:
         destination: "s3://my-bucket/data"
   connections:
     - from: "extractor.output"
       to: "validator.input"
     - from: "validator.valid"
       to: "transformer.input"
     - from: "transformer.output"
       to: "exporter.input"

Loading Workflow from YAML:

.. code-block:: python

   import yaml
   from routilux.factory.factory import ObjectFactory

   # Register routines in factory first
   factory = ObjectFactory.get_instance()
   factory.register("data_extractor", DataExtractor)
   factory.register("data_validator", DataValidator)
   # ... register other routines ...

   # Load YAML file
   with open("workflow.yaml") as f:
       spec = yaml.safe_load(f)

   # Create flow from spec (uses factory)
   flow = factory.load_flow_from_dsl(spec)

   # Execute
   job_state = flow.execute("extractor", entry_params={"data": "test"})

JSON Workflow Definition:

.. code-block:: json

   {
     "flow_id": "data_processing_pipeline",
     "execution": {
       "strategy": "concurrent",
       "timeout": 300.0
     },
     "routines": {
       "extractor": {
         "class": "data_extractor",
         "config": {
           "source": "database",
           "batch_size": 100
         }
       },
       "validator": {
         "class": "data_validator",
         "config": {
           "rules": [
             "data is not None",
             "data.get('id') is not None"
           ]
         }
       }
     },
     "connections": [
       {
         "from": "extractor.output",
         "to": "validator.input"
       }
     ]
   }

Loading Workflow from JSON:

.. code-block:: python

   import json
   from routilux.factory.factory import ObjectFactory

   # Register routines in factory first
   factory = ObjectFactory.get_instance()
   factory.register("data_extractor", DataExtractor)
   factory.register("data_validator", DataValidator)

   # Load JSON file
   with open("workflow.json") as f:
       spec = json.load(f)

   # Create flow from spec (uses factory)
   flow = factory.load_flow_from_dsl(spec)

   # Execute
   job_state = flow.execute("extractor", entry_params={"data": "test"})

Spec Format
-----------

Flow Specification:

.. code-block:: python

   spec = {
       "flow_id": "my_flow",  # Optional: auto-generated if not provided
       "execution": {
           "strategy": "sequential" | "concurrent",  # Optional: "sequential" (default)
           "timeout": 300.0,  # Optional: default timeout in seconds
           "max_workers": 5  # Optional: for concurrent mode
       },
       "routines": {
           "routine_id": {  # Routine identifier
               "class": "factory_name",  # Factory name (must be registered)
               "config": {  # Optional: configuration for routine
                   "key": "value"
               },
               "error_handler": {  # Optional: error handler configuration
                   "strategy": "stop" | "continue" | "retry" | "skip",
                   "max_retries": 3,
                   "retry_delay": 1.0,
                   "retry_backoff": 2.0,
                   "is_critical": false
               }
           }
       },
       "connections": [
           {
               "from": "source_routine.event_name",
               "to": "target_routine.slot_name",
               "param_mapping": {  # Optional: parameter mapping
                   "target_param": "source_param",
                   "other_param": "static_value"
               }
           }
       ]
   }

Factory Name Reference:

**All routines must be registered in ObjectFactory before use in DSL.**

The `class` field in DSL must be a factory name (string), not a class path:

.. code-block:: python

   from routilux.factory.factory import ObjectFactory
   from myapp.routines import DataProcessor

   # Register routine in factory first
   factory = ObjectFactory.get_instance()
   factory.register("data_processor", DataProcessor, description="Processes data")

   # Then use factory name in DSL
   spec = {
       "routines": {
           "processor": {
               "class": "data_processor",  # Factory name, not class path
               "config": {"threshold": 10}
           }
       }
   }

.. code-block:: yaml

   routines:
     processor:
       class: "data_processor"  # Factory name (must be registered)
       config:
         threshold: 10

Error Handler Configuration:

.. code-block:: yaml

   routines:
     critical_task:
       class: "critical_task"  # Factory name
       error_handler:
         strategy: "retry"  # or "stop", "continue", "skip"
         max_retries: 3
         retry_delay: 1.0
         retry_backoff: 2.0
         is_critical: true

   routines:
     optional_task:
       class: "optional_task"  # Factory name
       error_handler:
         strategy: "continue"  # Continue on error
         is_critical: false

Parameter Mapping:

Map parameters when connecting events to slots:

.. code-block:: yaml

   connections:
     - from: "source.output"
       to: "target.input"
       param_mapping:
         input_data: "result"  # Map event.result to slot.input_data
         extra_param: "static_value"  # Pass static value

Connection Patterns:

.. code-block:: yaml

   # One-to-one
   connections:
     - from: "source.output"
       to: "target.input"

   # One-to-many (fan-out)
   connections:
     - from: "source.output"
       to: "processor1.input"
     - from: "source.output"
       to: "processor2.input"
     - from: "source.output"
       to: "processor3.input"

   # Many-to-one (fan-in)
   connections:
     - from: "source1.output"
       to: "aggregator.input"
     - from: "source2.output"
       to: "aggregator.input"
     - from: "source3.output"
       to: "aggregator.input"

Advanced Usage
-------------

Dynamic Workflow Loading:

.. code-block:: python

   import yaml
   import os
   from routilux.factory.factory import ObjectFactory

   # Register all routines in factory first
   factory = ObjectFactory.get_instance()
   # ... register routines ...

   # Load workflow from directory
   workflow_dir = "workflows"
   workflow_files = ["data_pipeline.yaml", "ml_pipeline.yaml"]

   flows = {}
   for filename in workflow_files:
       filepath = os.path.join(workflow_dir, filename)
       with open(filepath) as f:
           spec = yaml.safe_load(f)
           flow = factory.load_flow_from_dsl(spec)
           flows[flow.flow_id] = flow

   # Execute specific workflow
   job_state = flows["data_pipeline"].execute("extractor", entry_params={"data": "test"})

Workflow Validation:

.. code-block:: python

   from routilux.factory.factory import ObjectFactory

   # Register routines in factory first
   factory = ObjectFactory.get_instance()
   factory.register("data_processor", DataProcessor)

   # Validate DSL by attempting to load
   spec = {
       "routines": {
           "processor": {"class": "data_processor"}  # Factory name
       },
       "connections": []
   }

   try:
       flow = factory.load_flow_from_dsl(spec)
       print("Workflow spec is valid!")
   except ValueError as e:
       print(f"Validation errors: {e}")

Environment-Specific Workflows:

.. code-block:: python

   import yaml
   import os
   from routilux.factory.factory import ObjectFactory

   # Register routines in factory first
   factory = ObjectFactory.get_instance()
   # ... register routines ...

   # Load environment-specific config
   env = os.getenv("ENV", "development")
   config_file = f"workflow_{env}.yaml"

   with open(config_file) as f:
       spec = yaml.safe_load(f)

   flow = factory.load_flow_from_dsl(spec)

Exporting Workflows to DSL:

.. code-block:: python

   from routilux.factory.factory import ObjectFactory

   # Create flow programmatically
   flow = Flow(flow_id="my_workflow")
   # ... add routines and connections ...

   # Export to DSL using factory (uses factory names)
   factory = ObjectFactory.get_instance()
   dsl = factory.export_flow_to_dsl(flow, format="json")

   # Save to file
   with open("workflow_export.json", "w") as f:
       f.write(dsl)

Best Practices
--------------

1. **Version Control**: Store DSL files in version control alongside code

2. **Environment Separation**: Use different configs for dev/staging/prod

   .. code-block:: yaml

      # workflow_dev.yaml
      execution:
        strategy: "sequential"

      # workflow_prod.yaml
      execution:
        strategy: "concurrent"
        max_workers: 20

3. **Documentation**: Add comments to YAML files for clarity

   .. code-block:: yaml

      routines:
        # Extracts data from database
        extractor:
          class: "data_extractor"  # Factory name (must be registered)
          config:
            source: "database"  # Primary data source

4. **Validation**: Validate DSL specs before loading in production

   .. code-block:: python

      from routilux.factory.factory import ObjectFactory

      def load_workflow(spec_path):
          factory = ObjectFactory.get_instance()
          with open(spec_path) as f:
              spec = yaml.safe_load(f)

          try:
              return factory.load_flow_from_dsl(spec)
          except ValueError as e:
              raise ValueError(f"Invalid spec: {e}") from e

5. **Error Handling**: Configure error handlers in DSL

   .. code-block:: yaml

      routines:
        critical_task:
          error_handler:
            strategy: "retry"
            max_retries: 5
            is_critical: true

        optional_task:
          error_handler:
            strategy: "continue"

See Also
--------

* :doc:`flows` - Flow class documentation
* :doc:`serialization` - Serialization and persistence
* :doc:`../api_reference/index` - Complete API reference
