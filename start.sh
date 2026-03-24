#!/bin/bash
# Quick start — activates venv and runs the server

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Run setup first:"
    echo "  chmod +x setup.sh && ./setup.sh"
    exit 1
fi

source .venv/bin/activate
python server.py
