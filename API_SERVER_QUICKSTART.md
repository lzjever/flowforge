# Routilux API Server Quick Start

This guide shows you how to start the Routilux HTTP API server for creating, monitoring, and debugging flows.

## Prerequisites

Install the API dependencies:

```bash
cd /home/percy/works/mygithub/routilux
uv sync --extra api
```

Or if using pip:

```bash
pip install -e ".[api]"
```

## Starting the Server

### Method 1: Using the Start Script (Recommended)

```bash
cd /home/percy/works/mygithub/routilux
./scripts/start_api_server.sh
```

You can customize the host and port using environment variables:

```bash
HOST=127.0.0.1 PORT=8080 ./scripts/start_api_server.sh
```

### Method 2: Using uvicorn Directly

```bash
cd /home/percy/works/mygithub/routilux

# Using uv (recommended)
uv run uvicorn routilux.api.main:app --host 0.0.0.0 --port 8000 --reload

# Or using python directly
uvicorn routilux.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Method 3: Running main.py Directly

```bash
cd /home/percy/works/mygithub/routilux
uv run python -m routilux.api.main
```

## Accessing the API

Once the server is running, you can access:

- **API Root**: http://localhost:8000/
- **Health Check**: http://localhost:8000/api/health
- **Interactive API Docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

## Available API Endpoints

### Flow Management (`/api/flows`)

- `GET /api/flows` - List all flows
- `GET /api/flows/{flow_id}` - Get flow details
- `POST /api/flows` - Create a new flow
- `DELETE /api/flows/{flow_id}` - Delete a flow
- `GET /api/flows/{flow_id}/dsl` - Export flow as DSL (YAML/JSON)
- `POST /api/flows/{flow_id}/validate` - Validate flow structure
- `GET /api/flows/{flow_id}/routines` - List all routines in a flow
- `GET /api/flows/{flow_id}/connections` - List all connections in a flow
- `POST /api/flows/{flow_id}/routines` - Add a routine to a flow
- `POST /api/flows/{flow_id}/connections` - Add a connection to a flow
- `DELETE /api/flows/{flow_id}/routines/{routine_id}` - Remove a routine
- `DELETE /api/flows/{flow_id}/connections/{connection_index}` - Remove a connection

### Job Management (`/api/jobs`)

- Job execution and monitoring endpoints

### Debugging (`/api/debug`)

- Debug and breakpoint management endpoints

### Monitoring (`/api/monitor`)

- Real-time monitoring endpoints

### WebSocket (`/api/websocket`)

- WebSocket connections for real-time updates

## Example: Creating a Flow via API

```bash
# Create a simple flow
curl -X POST http://localhost:8000/api/flows \
  -H "Content-Type: application/json" \
  -d '{
    "flow_id": "my_first_flow",
    "dsl_dict": {
      "flow_id": "my_first_flow",
      "routines": {},
      "connections": []
    }
  }'

# List all flows
curl http://localhost:8000/api/flows

# Get flow details
curl http://localhost:8000/api/flows/my_first_flow
```

## Configuration

The server runs with the following defaults:

- **Host**: `0.0.0.0` (accessible from all network interfaces)
- **Port**: `8000`
- **Reload**: `true` (auto-reload on code changes in development)

To change these, modify the `uvicorn.run()` call in `routilux/api/main.py` or use command-line arguments with uvicorn.

## Production Deployment

For production, you should:

1. Set `reload=False` in the uvicorn configuration
2. Use a production ASGI server like Gunicorn with Uvicorn workers:
   ```bash
   gunicorn routilux.api.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```
3. Configure proper CORS origins instead of `["*"]`
4. Use environment variables for configuration
5. Set up proper logging and monitoring

## Troubleshooting

### Port Already in Use

If port 8000 is already in use, change the port:

```bash
PORT=8080 ./scripts/start_api_server.sh
```

### Import Errors

Make sure you've installed the API dependencies:

```bash
uv sync --extra api
```

### Module Not Found

Ensure you're running from the project root directory or have installed the package:

```bash
uv sync --extra api
```

