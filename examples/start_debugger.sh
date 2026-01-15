#!/bin/bash
# Quick start script for Routilux Debugger with test flows

echo "=================================="
echo "Starting Routilux Debugger Server"
echo "=================================="

cd /home/percy/works/mygithub/routilux

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Set debugger mode
export ROUTILUX_DEBUGGER_MODE=true

# Start API server
echo "Starting API server with debugger mode..."
echo ""
uv run uvicorn routilux.api.main:app --host 0.0.0.0 --port 20555 --reload
