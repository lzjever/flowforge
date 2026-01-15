#!/bin/bash
# Quick start script for Routilux Overseer Demo

echo "========================================"
echo "  Routilux Overseer Demo - Quick Start"
echo "========================================"
echo ""
echo "This script will:"
echo "  1. Start the Routilux API Server with demo flows"
echo "  2. Provide instructions for connecting Overseer"
echo ""
echo "Press Ctrl+C to stop the server at any time"
echo ""
echo "========================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 not found"
    echo "   Please install Python 3.9+ to run this demo"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "overseer_demo_app.py" ]; then
    echo "❌ Error: overseer_demo_app.py not found"
    echo "   Please run this script from the examples/ directory"
    exit 1
fi

# Make the demo app executable
chmod +x overseer_demo_app.py

# Start the demo app
echo "✓ Starting Routilux Overseer Demo App..."
echo ""
python3 overseer_demo_app.py
