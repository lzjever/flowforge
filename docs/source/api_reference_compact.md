# FlowForge Core API Reference (Compact)
============================================================

Compact reference for LLM code generation. Extracted from AST analysis.

## flowforge/routine.py

### Routine
Bases: Serializable
Improved Routine base class with enhanced capabilities.
  __call__() -> None  # Execute routine
  __init__()  # Initialize Routine object
  __repr__() -> str  # Return string representation of the Routine
  _extract_input_data(data:Any=None) -> Any  # Extract input data from slot parameters
  _track_operation(operation_name:str, success:bool=True) -> None  # Track operation statistics with metadata
  config() -> Dict[str, Any]  # Get a copy of the configuration dictionary
  define_event(name:str, output_params:Optional[List[str]]=None) -> Event  # Define an output event for transmitting data to other routines
  define_slot(name:str, handler:Optional[Callable]=None, merge_strategy:str='override') -> Slot  # Define an input slot for receiving data from other routines
  deserialize(data:Dict[str, Any]) -> None  # Deserialize Routine
  emit(event_name:str, flow:Optional['Flow']=None) -> None  # Emit an event and send data to all connected slots
  get_config(key:str, default:Any=None) -> Any  # Get a configuration value from the _config dictionary
  get_error_handler() -> Optional['ErrorHandler']  # Get error handler for this routine
  get_event(name:str) -> Optional['Event']  # Get specified event
  get_slot(name:str) -> Optional['Slot']  # Get specified slot
  get_stat(key:str, default:Any=None) -> Any  # Get a statistics value from the _stats dictionary
  increment_stat(key:str, amount:int=1) -> int  # Increment a numeric statistics value
  reset_stats(keys:Optional[List[str]]=None) -> None  # Reset statistics values
  serialize() -> Dict[str, Any]  # Serialize Routine, including class information and state
  set_as_critical(max_retries:int=3, retry_delay:float=1.0, retry_backoff:float=2.0) -> None  # Mark this routine as critical (must succeed, retry on failure)
  set_as_optional(strategy:ErrorStrategy=None) -> None  # Mark this routine as optional (failures are tolerated)
  set_config() -> None  # Set configuration values in the _config dictionary
  set_error_handler(error_handler:ErrorHandler) -> None  # Set error handler for this routine
  set_stat(key:str, value:Any) -> None  # Set a statistics value in the _stats dictionary
  stats() -> Dict[str, Any]  # Return a copy of the statistics dictionary

### Functions

## flowforge/flow.py

### Flow
Bases: Serializable
Flow manager for orchestrating workflow execution.
  __init__(flow_id:Optional[str]=None, execution_strategy:str='sequential', max_workers:int=5)  # Initialize Flow
  __repr__() -> str  # Return string representation of the Flow
  _build_dependency_graph() -> Dict[str, Set[str]]  # Build routine dependency graph
  _execute_concurrent(entry_routine_id:str, entry_params:Optional[Dict[str, Any]]=None) -> JobState  # Execute Flow concurrently
  _execute_routine_safe(routine_id:str, routine:Routine, params:Dict[str, Any], start_time:datetime) -> Tuple[str, Any, Optional[Exception], float]  # Execute routine in a thread-safe manner
  _execute_sequential(entry_routine_id:str, entry_params:Optional[Dict[str, Any]]=None) -> JobState  # Execute Flow sequentially (original logic)
  _find_connection(event:Event, slot:Slot) -> Optional['Connection']  # Find Connection from event to slot
  _get_error_handler_for_routine(routine:Routine, routine_id:str) -> Optional['ErrorHandler']  # Get error handler for a routine
  _get_executor() -> ThreadPoolExecutor  # Get or create thread pool executor
  _get_ready_routines(completed:Set[str], dependency_graph:Dict[str, Set[str]], running:Set[str]) -> List[str]  # Get routines ready for execution (all dependencies completed and not running)
  _get_routine_id(routine:Routine) -> Optional[str]  # Find the ID of a Routine object within this Flow
  add_routine(routine:Routine, routine_id:Optional[str]=None) -> str  # Add a routine to the flow
  cancel(reason:str='') -> None  # Cancel execution
  connect(source_routine_id:str, source_event:str, target_routine_id:str, target_slot:str, param_mapping:Optional[Dict[str, str]]=None) -> Connection  # Connect two routines by linking a source event to a target slot
  deserialize(data:Dict[str, Any]) -> None  # Deserialize Flow, restoring all routines and connections
  execute(entry_routine_id:str, entry_params:Optional[Dict[str, Any]]=None, execution_strategy:Optional[str]=None) -> JobState  # Execute the flow starting from the specified entry routine
  pause(reason:str='', checkpoint:Optional[Dict[str, Any]]=None) -> None  # Pause execution
  resume(job_state:Optional['JobState']=None) -> JobState  # Resume execution from paused or saved state
  serialize() -> Dict[str, Any]  # Serialize Flow, including all routines and connections
  set_error_handler(error_handler:ErrorHandler) -> None  # Set error handler for the flow
  set_execution_strategy(strategy:str, max_workers:Optional[int]=None) -> None  # Set execution strategy
  shutdown(wait:bool=True, timeout:Optional[float]=None) -> None  # Shutdown Flow's concurrent executor
  wait_for_completion(timeout:Optional[float]=None) -> bool  # Wait for all concurrent tasks to complete

### Functions

## flowforge/slot.py

### Slot
Bases: Serializable
Input slot for receiving data from other routines.
  __init__(name:str='', routine:Optional['Routine']=None, handler:Optional[Callable]=None, merge_strategy:str='override')  # Initialize Slot
  __repr__() -> str  # Return string representation of the Slot
  _is_kwargs_handler(handler:Callable) -> bool  # Check if handler accepts **kwargs
  _merge_data(new_data:Dict[str, Any]) -> Dict[str, Any]  # Merge new data into existing data according to merge_strategy
  connect(event:Event, param_mapping:Optional[Dict[str, str]]=None) -> None  # Connect to an event
  deserialize(data:Dict[str, Any]) -> None  # Deserialize Slot
  disconnect(event:Event) -> None  # Disconnect from an event
  receive(data:Dict[str, Any]) -> None  # Receive data, merge with existing data, and call handler
  serialize() -> Dict[str, Any]  # Serialize Slot

### Functions

## flowforge/event.py

### Event
Bases: Serializable
Output event for transmitting data to other routines.
  __init__(name:str='', routine:Optional['Routine']=None, output_params:Optional[List[str]]=None)  # Initialize an Event
  __repr__() -> str  # Return string representation of the Event
  connect(slot:Slot, param_mapping:Optional[Dict[str, str]]=None) -> None  # Connect to a slot
  deserialize(data:Dict[str, Any]) -> None  # Deserialize the Event
  disconnect(slot:Slot) -> None  # Disconnect from a slot
  emit(flow:Optional['Flow']=None) -> None  # Emit the event and send data to all connected slots
  serialize() -> Dict[str, Any]  # Serialize the Event

### Functions
  activate_slot(s=slot, f=flow, k=kwargs.copy())  # Thread-safe slot activation function
  remove_future(fut=future, f=flow)  # Remove from tracking set when task completes

## flowforge/connection.py

### Connection
Bases: Serializable
Connection object representing a link from an event to a slot.
  __init__(source_event:Optional['Event']=None, target_slot:Optional['Slot']=None, param_mapping:Optional[Dict[str, str]]=None)  # Initialize a Connection between an event and a slot
  __repr__() -> str  # Return string representation of the Connection
  _apply_mapping(data:Dict[str, Any]) -> Dict[str, Any]  # Apply parameter mapping to transform data dictionary
  activate(data:Dict[str, Any]) -> None  # Activate the connection and transmit data to the target slot
  deserialize(data:Dict[str, Any]) -> None  # Deserialize the Connection
  disconnect() -> None  # Disconnect the connection
  serialize() -> Dict[str, Any]  # Serialize the Connection

### Functions

## flowforge/error_handler.py

### ErrorHandler
Bases: Serializable
Error handler for managing error handling strategies and retry mechanisms.
  __init__(strategy:str='stop', max_retries:int=3, retry_delay:float=1.0, retry_backoff:float=2.0, retryable_exceptions:Optional[tuple]=None, is_critical:bool=False)  # Initialize ErrorHandler with configuration
  deserialize(data:Dict[str, Any]) -> None  # Deserialize the ErrorHandler
  handle_error(error:Exception, routine:Routine, routine_id:str, flow:Flow, context:Optional[Dict[str, Any]]=None) -> bool  # Handle an error according to the configured strategy
  reset() -> None  # Reset the retry count
  serialize() -> Dict[str, Any]  # Serialize the ErrorHandler

### ErrorStrategy
Bases: Enum
Error handling strategy enumeration.

### Functions

## flowforge/job_state.py

### ExecutionRecord
Bases: Serializable
Execution record for a single routine execution.
  __init__(routine_id:str='', event_name:str='', data:Optional[Dict[str, Any]]=None, timestamp:Optional[datetime]=None)  # Initialize ExecutionRecord
  __repr__() -> str  # Return string representation of the ExecutionRecord
  deserialize(data:Dict[str, Any]) -> None  # Deserialize, handling datetime conversion
  serialize() -> Dict[str, Any]  # Serialize, handling datetime conversion

### JobState
Bases: Serializable
Job state for tracking flow execution.
  __init__(flow_id:str='')  # Initialize JobState
  __repr__() -> str  # Return string representation of the JobState
  _set_cancelled(reason:str='') -> None  # Internal method: Set cancelled state (called by Flow)
  _set_paused(reason:str='', checkpoint:Optional[Dict[str, Any]]=None) -> None  # Internal method: Set paused state (called by Flow)
  _set_running() -> None  # Internal method: Set running state (called by Flow)
  deserialize(data:Dict[str, Any]) -> None  # Deserialize, handling datetime and ExecutionRecord
  get_execution_history(routine_id:Optional[str]=None) -> List[ExecutionRecord]  # Get execution history, optionally filtered by routine
  get_routine_state(routine_id:str) -> Optional[Dict[str, Any]]  # Get execution state for a specific routine
  load(filepath:str) -> JobState  # Load state from file
  record_execution(routine_id:str, event_name:str, data:Dict[str, Any]) -> None  # Record an execution event in the execution history
  save(filepath:str) -> None  # Persist state to file
  serialize() -> Dict[str, Any]  # Serialize, handling datetime and ExecutionRecord
  update_routine_state(routine_id:str, state:Dict[str, Any]) -> None  # Update state for a specific routine

### Functions

## flowforge/execution_tracker.py

### ExecutionTracker
Bases: Serializable
Execution tracker for monitoring flow execution state and performance.
  __init__(flow_id:str='')  # Initialize ExecutionTracker
  get_flow_performance() -> Dict[str, Any]  # Get performance metrics for the entire flow
  get_routine_performance(routine_id:str) -> Optional[Dict[str, Any]]  # Get performance metrics for a routine
  record_event(source_routine_id:str, event_name:str, target_routine_id:Optional[str]=None, data:Dict[str, Any]=None) -> None  # Record an event emission in the event flow
  record_routine_end(routine_id:str, status:str='completed', result:Any=None, error:Optional[str]=None) -> None  # Record the end of a routine execution
  record_routine_start(routine_id:str, params:Dict[str, Any]=None) -> None  # Record the start of a routine execution

### Functions

## flowforge/utils/serializable.py

### Serializable
A base class for objects that can be serialized and deserialized.
  __init__() -> None  # Initialize a serializable object with no specific fields
  add_serializable_fields(fields:List[str]) -> None  # Add field names to the list that should be included in serialization
  deserialize(data:Dict[str, Any]) -> None  # Deserialize the object from a dictionary, restoring its state
  deserialize_item(item:Dict[str, Any]) -> Any  # Deserialize an item
  remove_serializable_fields(fields:List[str]) -> None  # Remove field names from the list that should be included in serialization
  serialize() -> Dict[str, Any]  # Serialize the object to a dictionary

### SerializableRegistry
Registry for serializable classes to facilitate class lookup and instantiation.
  get_class(class_name:str)  # Retrieve a class reference from the registry by its name
  register_class(class_name:str, class_ref:type)  # Register a class for serialization purposes by adding it to the registry

### Functions
  check_serializable_constructability(obj:Serializable) -> None  # Check if a Serializable object can be constructed without arguments
  register_serializable()  # Decorator to register a class as serializable in the registry
  validate_serializable_tree(obj:Serializable, visited:Optional[set]=None) -> None  # Recursively validate that all Serializable objects in a tree can be constructed

## flowforge/serialization_utils.py

### Functions
  deserialize_callable(callable_data:Optional[Dict[str, Any]], context:Optional[Dict[str, Any]]=None) -> Optional[Callable]  # Deserialize a callable object
  get_routine_class_info(routine:Any) -> Dict[str, Any]  # Get class information for a Routine
  load_routine_class(class_info:Dict[str, Any]) -> Optional[Type]  # Load Routine class from class information
  serialize_callable(callable_obj:Optional[Callable]) -> Optional[Dict[str, Any]]  # Serialize a callable object (function or method)
