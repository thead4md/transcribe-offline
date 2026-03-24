# Magyar Beszédfelismerő — Offline

100% local speech-to-text running on Apple Silicon (M1/M2/M3/M4) using [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper). No internet required after setup. No API keys. Full privacy.

## Features

- **File upload** — drag & drop MP3, WAV, OGG, FLAC, M4A, MP4, AAC, WebM (up to 450 MB)
- **Live recording** — record from your microphone and transcribe
- **Hungarian + English** — optimized for Hungarian with English support and auto-detection
- **Apple Silicon native** — uses MLX framework for GPU-accelerated inference on M-series chips
- **Word timestamps** — get per-word timing for each transcription
- **Fully offline** — after initial model download, works without any network connection

## Requirements

- macOS 13+ (Ventura or later)
- Apple Silicon Mac (M1, M2, M3, or M4)
- Python 3.10+
- ffmpeg (recommended, for broad format support)

## Quick Start

```bash
# Clone
git clone https://github.com/thead4md/transcribe-offline.git
cd transcribe-offline

# Setup (installs dependencies, builds frontend)
chmod +x setup.sh
./setup.sh

# Run
chmod +x start.sh
./start.sh
```

Then open **http://localhost:5000** in your browser.

The first transcription will download the Whisper model (~1.6 GB). After that, everything works fully offline.

## Manual Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Build frontend (requires Node.js)
cd frontend
npm install
npm run build
cd ..

# Install ffmpeg (optional but recommended)
brew install ffmpeg

# Run
python server.py
```

## Choosing a Model

Set the `WHISPER_MODEL` environment variable to change the model:

| Model | Params | Speed (M4) | Accuracy | Download |
|---|---|---|---|---|
| `mlx-community/whisper-tiny-mlx` | 39M | ~60x RT | ★★☆☆☆ | ~75 MB |
| `mlx-community/whisper-base-mlx` | 74M | ~40x RT | ★★★☆☆ | ~140 MB |
| `mlx-community/whisper-small-mlx` | 244M | ~20x RT | ★★★☆☆ | ~460 MB |
| `mlx-community/whisper-medium-mlx` | 769M | ~8x RT | ★★★★☆ | ~1.5 GB |
| **`mlx-community/whisper-large-v3-turbo`** | 809M | ~6x RT | ★★★★★ | ~1.6 GB |
| `mlx-community/whisper-large-v3-mlx` | 1.5B | ~3x RT | ★★★★★ | ~3 GB |

**Default: `whisper-large-v3-turbo`** — best balance of accuracy and speed.

```bash
# Use a different model
WHISPER_MODEL="mlx-community/whisper-small-mlx" python server.py

# Or for maximum accuracy
WHISPER_MODEL="mlx-community/whisper-large-v3-mlx" python server.py
```

"RT" = real-time. 6x RT means a 60-second audio file transcribes in ~10 seconds.

## Project Structure

```
transcribe-offline/
├── server.py              # FastAPI backend with mlx-whisper
├── requirements.txt       # Python dependencies
├── setup.sh               # One-command setup script
├── start.sh               # Quick start script
├── frontend/
│   ├── src/App.tsx         # React frontend
│   ├── src/index.css       # Styles
│   ├── src/main.tsx        # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## How It Works

1. The Python server runs locally on port 5000
2. The React frontend is served as static files by the same server
3. When you upload a file or record audio, it's sent to the local `/api/transcribe` endpoint
4. mlx-whisper runs inference directly on the Apple Silicon GPU/Neural Engine
5. Results are returned to the browser — nothing leaves your machine

## Troubleshooting

**"Server not reachable"** — Make sure `python server.py` is running in a terminal.

**Slow first transcription** — The model is being downloaded from Hugging Face (~1.6 GB). This only happens once.

**"ffmpeg not found"** — Install with `brew install ffmpeg`. The app works without it for WAV and common formats, but ffmpeg ensures all formats are supported.

**Out of memory** — Use a smaller model: `WHISPER_MODEL="mlx-community/whisper-small-mlx" python server.py`

---

Created with [Perplexity Computer](https://www.perplexity.ai/computer)
