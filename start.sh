#!/bin/bash

# Flask Chat UI with MCP Client Startup Script

echo "=== Flask Chat UI with MCP Client ==="
echo "Starting up the application..."
echo

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please create one with your DEEPSEEK_API_KEY"
    echo "Example: echo 'DEEPSEEK_API_KEY=your_api_key_here' > .env"
    echo
fi

echo "Starting Flask application..."
echo "The chat UI will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo

# Start the Flask app
python app.py
