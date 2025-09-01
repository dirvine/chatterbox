#!/bin/bash

# ChatterBox TTS Service Startup Script

echo "Starting ChatterBox TTS Service..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Install dependencies if needed
echo "Installing dependencies..."
uv pip install -e .

# Start the service
echo "Starting service on http://127.0.0.1:8000"
python3 tts_service.py --host 127.0.0.1 --port 8000