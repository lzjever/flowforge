# API Integration Tests

This document describes the comprehensive API integration tests in `test_api.py`.

## Overview

The test file `tests/test_api.py` contains **68 test cases** covering all HTTP API endpoints:

- **Health & Root** (3 tests): Root endpoint, health check, OpenAPI schema
- **Flow Management** (18 tests): CRUD operations, export, validate, routines, connections
- **Job Management** (12 tests): Start, pause, resume, cancel, status, state
- **Breakpoint Management** (10 tests): Create, list, update, delete breakpoints
- **Debug Operations** (8 tests): Session, resume, step, variables, call-stack
- **Monitoring** (9 tests): Metrics, trace, logs for jobs and flows
- **WebSocket** (5 tests): Real-time monitoring and debug connections

## Running the Tests

### Prerequisites

1. Install API dependencies:
```bash
cd /home/percy/works/mygithub/routilux
uv sync --extra api
```

2. Ensure port 20555 is available (or modify `API_PORT` in the test file)

### Run All API Tests

```bash
uv run pytest tests/test_api.py -v
```

### Run Specific Test Classes

```bash
# Test only Flow API
uv run pytest tests/test_api.py::TestFlowAPI -v

# Test only Job API
uv run pytest tests/test_api.py::TestJobAPI -v

# Test only Breakpoint API
uv run pytest tests/test_api.py::TestBreakpointAPI -v
```

### Run Individual Tests

```bash
# Test health endpoint
uv run pytest tests/test_api.py::TestHealthAPI::test_health_endpoint -v

# Test creating a flow
uv run pytest tests/test_api.py::TestFlowAPI::test_create_flow_empty -v
```

## Test Architecture

### Server Management

Tests use a `module`-scoped fixture `api_server` that:
1. Starts a real uvicorn server on `127.0.0.1:20555`
2. Waits for the server to be ready (port open + health check)
3. Cleans up the server after all tests complete

### Test Isolation

Each test uses a `cleanup` fixture that:
- Clears all flows after the test
- Clears all jobs after the test
- Ensures test isolation

### HTTP Client

Tests use `httpx.Client` for HTTP requests with:
- Base URL: `http://127.0.0.1:20555`
- Timeout: 30 seconds
- Automatic JSON serialization/deserialization

## Test Coverage

### Flow API (`/api/flows`)

✅ List flows (empty and with data)  
✅ Create flow (empty, with DSL, with execution strategy)  
✅ Get flow details  
✅ Delete flow  
✅ Export flow as DSL (YAML/JSON)  
✅ Validate flow  
✅ List routines in flow  
✅ List connections in flow  
✅ Add routine to flow  
✅ Add connection to flow  
✅ Remove routine from flow  
✅ Remove connection from flow  
✅ Error handling (404, 400, 422)

### Job API (`/api/jobs`)

✅ Start job  
✅ List jobs  
✅ Get job details  
✅ Get job status  
✅ Get job state  
✅ Pause job  
✅ Resume job  
✅ Cancel job  
✅ Error handling (404, 400)

### Breakpoint API (`/api/jobs/{job_id}/breakpoints`)

✅ Create breakpoint (routine, slot, event types)  
✅ Create breakpoint with condition  
✅ List breakpoints  
✅ Update breakpoint (enable/disable)  
✅ Delete breakpoint  
✅ Error handling (404, 500)

### Debug API (`/api/jobs/{job_id}/debug`)

✅ Get debug session  
✅ Resume debug  
✅ Step over  
✅ Step into  
✅ Get variables  
✅ Set variable  
✅ Get call stack  
✅ Error handling (404, 400, 500)

### Monitor API (`/api/jobs/{job_id}/monitor`, `/api/flows/{flow_id}/metrics`)

✅ Get job metrics  
✅ Get job trace (with limit)  
✅ Get job logs  
✅ Get flow metrics  
✅ Error handling (404, 500)

### WebSocket API (`/api/ws/...`)

✅ Job monitor WebSocket  
✅ Job debug WebSocket  
✅ Flow monitor WebSocket  
✅ Error handling (connection closed for invalid IDs)

## Test Philosophy

Tests are written **strictly against the API interface** without looking at implementation:

1. **Black-box testing**: Tests only use public API endpoints
2. **Challenge business logic**: Tests verify proper error handling and edge cases
3. **Real server**: Tests use a real running HTTP server, not mocks
4. **Comprehensive coverage**: Every endpoint is tested with both success and error cases

## Troubleshooting

### Server Won't Start

If tests fail with "API server failed to start":

1. Check if port 20555 is already in use:
```bash
lsof -i :20555
```

2. Kill any existing processes:
```bash
lsof -ti :20555 | xargs kill -9
```

3. Check server logs in the test output (STDERR)

### Tests Timeout

If tests timeout waiting for server:

1. Increase `max_wait` in the `api_server` fixture
2. Check if there are firewall issues
3. Verify uvicorn is installed correctly

### Import Errors

If you see import errors:

```bash
# Install API dependencies
uv sync --extra api

# Or with pip
pip install -e ".[api]"
```

## Future Improvements

- [ ] Add performance/load testing
- [ ] Add authentication/authorization tests (when implemented)
- [ ] Add more edge case tests
- [ ] Add integration tests with real flow execution
- [ ] Add WebSocket message validation tests

