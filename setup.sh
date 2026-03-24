#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Magyar Beszédfelismerő — Offline Setup
#  One-command install for macOS with Apple Silicon
# ═══════════════════════════════════════════════════════════

set -e

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Magyar Beszédfelismerő — Offline Setup"
echo "  Apple Silicon · mlx-whisper · 100% local"
echo "═══════════════════════════════════════════════════════"
echo ""

# Check macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "✗ This app requires macOS with Apple Silicon."
    exit 1
fi

# Check Apple Silicon
if [[ "$(uname -m)" != "arm64" ]]; then
    echo "⚠ Warning: This Mac does not appear to be Apple Silicon."
    echo "  The app will run but will be significantly slower."
    echo ""
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 is required. Install it with:"
    echo "  brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "  Python: $PYTHON_VERSION"

# Check/install ffmpeg
if command -v ffmpeg &> /dev/null; then
    echo "  ffmpeg: $(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f3)"
else
    echo "  ffmpeg: not found"
    echo ""
    echo "  ffmpeg is recommended for best format support."
    read -p "  Install ffmpeg via Homebrew? [Y/n] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo "  Homebrew not found. Install ffmpeg manually:"
            echo "  https://ffmpeg.org/download.html"
        fi
    fi
fi

# Create virtual environment
echo ""
echo "  Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo "  Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "  Building frontend..."

# Check if Node.js is available for building frontend
if command -v npm &> /dev/null; then
    cd frontend
    npm install --silent 2>/dev/null
    npm run build --silent 2>/dev/null
    cd ..
    echo "  Frontend built successfully"
else
    echo "  Node.js not found — using pre-built frontend if available"
    if [ ! -d "frontend/dist" ]; then
        echo ""
        echo "  ⚠ No pre-built frontend found. Install Node.js to build:"
        echo "    brew install node"
        echo "    cd frontend && npm install && npm run build"
    fi
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✓ Setup complete!"
echo ""
echo "  Start the app:"
echo "    source .venv/bin/activate"
echo "    python server.py"
echo ""
echo "  Then open: http://localhost:5000"
echo ""
echo "  First run will download the Whisper model (~1.6 GB)."
echo "  After that, everything works fully offline."
echo "═══════════════════════════════════════════════════════"
echo ""
