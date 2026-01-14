# Routilux Debugger Test App

This test application creates multiple flows with various patterns to test the Routilux Debugger web interface.

## Test Flows

### 1. Linear Flow (`linear_flow`)
Simple linear processing pipeline:
```
Source → Validator → Transformer → Sink
```

**Routines:**
- `LinearSource` - Generates test data
- `LinearValidator` - Validates input data
- `LinearTransformer` - Transforms data to uppercase
- `LinearSink` - Receives final result

**Characteristics:**
- 4 routines
- 3 connections
- Linear execution flow

### 2. Branching Flow (`branching_flow`)
Flow with fan-out and fan-in:
```
              → Transformer ↘
Source → Validator
              → Multiplier ↙
                   ↓
                   Sink
```

**Routines:**
- `BranchSource` - Generates test data
- `BranchValidator` - Validates input
- `BranchTransformer` - Transforms to uppercase
- `BranchMultiplier` - Multiplies/duplicates data
- `BranchSink` - Receives both outputs

**Characteristics:**
- 5 routines
- 5 connections
- Fan-out (1 → 2) and fan-in (2 → 1)

### 3. Complex Flow (`complex_flow`)
Complex flow with multiple patterns:
```
Source1 → Validator1 → Transformer → Aggregator
                              ↓
                           SlowProcessor

Source2 → Validator2 → Multiplier ↗
                              ↓
                           Sink
```

**Routines:**
- 2 sources (`Source1`, `Source2`)
- 2 validators (`Validator1`, `Validator2`)
- 2 processors (`Transformer`, `Multiplier`)
- 1 slow processor (`SlowProcessor` - 1s delay)
- 1 aggregator (`Aggregator` - merges multiple inputs)
- 1 sink (`Sink`)

**Characteristics:**
- 9 routines
- 8 connections
- Multiple sources, aggregation, slow processing

### 4. Error Flow (`error_flow`)
Flow for testing error handling:
```
Source → ErrorProcessor → Sink
         (can fail)
```

**Routines:**
- `ErrorSource` - Generates test data
- `ErrorProcessor` - Can generate errors on demand
- `ErrorSink` - Receives result or error

**Characteristics:**
- 3 routines
- 2 connections
- Tests error scenarios

## How to Use

### Quick Start

1. **Start the Routilux API Server with test flows:**

   ```bash
   cd /home/percy/works/mygithub/routilux
   python examples/debugger_test_app.py
   ```

   Or use the shell script:
   ```bash
   ./examples/start_debugger_test.sh
   ```

2. **Start the Debugger Web Interface:**

   In a new terminal:
   ```bash
   cd /home/percy/works/mygithub/routilux-debugger
   npm run dev
   ```

3. **Connect to the API Server:**

   - Open browser: http://localhost:3000
   - You'll be redirected to `/connect`
   - Enter server URL: `http://localhost:20555`
   - Click "Connect"

4. **View and Monitor Flows:**

   After connecting, you can:
   - View all available flows
   - See flow visualizations (when implemented)
   - Start jobs and monitor execution
   - Set breakpoints and debug (when implemented)

### Testing Scenarios

#### Scenario 1: Monitor Linear Flow
```python
# This will be available via API
flow_id = "linear_flow"
entry_routine = "source"
entry_params = {"data": "Hello, Debugger!"}
```

#### Scenario 2: Test Branching
```python
flow_id = "branching_flow"
entry_routine = "source"
entry_params = {"data": "Branch Test"}
```

#### Scenario 3: Complex Flow with Slow Processing
```python
flow_id = "complex_flow"
entry_routine = "source1"  # or "source2"
entry_params = {"data": "Complex Test", "index": 0}
```

#### Scenario 4: Error Handling
```python
flow_id = "error_flow"
entry_routine = "source"
entry_params = {"data": "Error Test", "should_fail": True}
```

## Manual Testing with Python

You can also manually test flows using Python:

```python
from routilux import Flow
from routilux.monitoring.storage import flow_store

# Get a flow
flow = flow_store.get("linear_flow")

# Start a job
job_state = flow.execute(
    "source",
    entry_params={"data": "Test Data"}
)

# Wait for completion
from routilux.job_state import JobState
JobState.wait_for_completion(flow, job_state, timeout=5.0)

# Check status
print(f"Status: {job_state.status}")
print(f"Execution History: {len(job_state.execution_history)} events")
```

## API Endpoints

Once the server is running, these endpoints are available:

- `GET http://localhost:20555/api/flows` - List all flows
- `GET http://localhost:20555/api/flows/{flow_id}` - Get flow details
- `POST http://localhost:20555/api/jobs` - Start a new job
- `GET http://localhost:20555/api/jobs` - List all jobs
- `GET http://localhost:20555/api/jobs/{job_id}` - Get job details
- `POST http://localhost:20555/api/jobs/{job_id}/pause` - Pause a job
- `POST http://localhost:20555/api/jobs/{job_id}/resume` - Resume a job
- `WS http://localhost:20555/api/ws/jobs/{job_id}/monitor` - Real-time monitoring

## Troubleshooting

### Port Already in Use
If port 20555 is already in use, change it in `routilux/api/main.py`:
```python
uvicorn.run(
    "routilux.api.main:app",
    host="0.0.0.0",
    port=8080,  # Change to available port
    reload=True,
)
```

### Dependencies Missing
```bash
cd /home/percy/works/mygithub/routilux
uv sync --extra api
# or
pip install -e ".[api]"
```

### Connection Refused
Make sure the API server is running:
```bash
curl http://localhost:20555/api/health
# Should return: {"status":"healthy"}
```

## Next Steps

1. ✅ Test flows created
2. ✅ API server ready
3. ⏳ Implement Flow Visualization in debugger (Phase 2)
4. ⏳ Implement Real-time Monitoring (Phase 3)
5. ⏳ Implement Debugging (Phase 4)

Enjoy testing! 🚀
