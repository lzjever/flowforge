#!/bin/bash
# Script to start the Routilux API Server with test flows

cd /home/percy/works/mygithub/routilux

echo "=================================="
echo "Starting Routilux Debugger Test App"
echo "=================================="
echo ""

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if API dependencies are installed
echo "Checking dependencies..."
python -c "import fastapi; import uvicorn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing API dependencies..."
    uv sync --extra api
    # or: pip install -e ".[api]"
fi

echo ""
echo "Starting test application..."
echo ""
python examples/debugger_test_app.py
