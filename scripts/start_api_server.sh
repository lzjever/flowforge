#!/bin/bash
# Start the Routilux API server

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-true}"

# Change to project directory
cd "$PROJECT_DIR" || exit 1

# Check if API dependencies are installed
echo "Starting Routilux API server..."
echo "Host: $HOST"
echo "Port: $PORT"
echo "Reload: $RELOAD"
echo ""

# Start the server using uv
if command -v uv &> /dev/null; then
    echo "Using uv to run the server..."
    uv run uvicorn routilux.api.main:app \
        --host "$HOST" \
        --port "$PORT" \
        $([ "$RELOAD" = "true" ] && echo "--reload" || echo "")
else
    echo "Using python to run the server..."
    uvicorn routilux.api.main:app \
        --host "$HOST" \
        --port "$PORT" \
        $([ "$RELOAD" = "true" ] && echo "--reload" || echo "")
fi

