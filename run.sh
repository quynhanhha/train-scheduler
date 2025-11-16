#!/bin/bash
# Simple startup script for the Train Scheduler API

echo "Starting Train Scheduler API..."
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "WARNING: No virtual environment detected."
    echo "Consider activating one: source venv/bin/activate"
    echo ""
fi

# Run with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

