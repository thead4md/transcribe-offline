"""
Magyar Beszédfelismerő — Offline Local Server
Runs 100% locally on Apple Silicon (M1/M2/M3/M4) using mlx-whisper.
No internet connection required after initial model download.
No API keys needed.
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path

# ─── Hugging Face token & warnings ───────────────────────────────────────
# Load .env file FIRST (before any HF imports) so the token is available
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

# Propagate HF_TOKEN to all env vars that huggingface_hub checks
_hf_token = os.environ.get("HF_TOKEN", "")
if _hf_token:
    os.environ["HF_TOKEN"] = _hf_token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = _hf_token

# Suppress the "unauthenticated requests" warning that comes via HTTP header.
# This warning is emitted by huggingface_hub's HTTP layer, not Python warnings,
# so the only reliable way to silence it is HF_HUB_DISABLE_IMPLICIT_TOKEN
# combined with reducing verbosity.
os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Magyar Beszédfelismerő — Offline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Configuration ────────────────────────────────────────────────────────────

# Model options (set via WHISPER_MODEL env var or change default here):
#
#   Model                                      Params   Speed     Accuracy
#   ─────────────────────────────────────────  ──────   ───────   ────────
#   mlx-community/whisper-tiny-mlx              39M    ~60x RT    ★★☆☆☆
#   mlx-community/whisper-base-mlx              74M    ~40x RT    ★★★☆☆
#   mlx-community/whisper-small-mlx            244M    ~20x RT    ★★★☆☆
#   mlx-community/whisper-medium-mlx           769M    ~8x RT     ★★★★☆
#   mlx-community/whisper-large-v3-turbo       809M    ~6x RT     ★★★★★
#   mlx-community/whisper-large-v3-mlx         1.5B    ~3x RT     ★★★★★
#
# "RT" = faster than real-time on M4. large-v3-turbo is the recommended default:
# near-best accuracy at roughly 2x the speed of large-v3.

DEFAULT_MODEL = os.environ.get(
    "WHISPER_MODEL", "mlx-community/whisper-large-v3-turbo"
)

MAX_UPLOAD_BYTES = 450 * 1024 * 1024  # 450 MB

# ─── Lazy model loading ──────────────────────────────────────────────────────

_mlx_whisper = None


def get_mlx_whisper():
    """Import mlx_whisper lazily so the server starts fast."""
    global _mlx_whisper
    if _mlx_whisper is None:
        print("  Loading mlx-whisper...")
        import mlx_whisper
        _mlx_whisper = mlx_whisper
        print("  mlx-whisper ready")
    return _mlx_whisper


# ─── Helpers ─────────────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {
    "mp3", "wav", "ogg", "flac", "m4a", "mp4", "aac", "webm", "wma", "opus",
}


def get_file_extension(filename: str | None, content_type: str | None) -> str:
    """Determine file extension from filename or content type."""
    if filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            return ext

    ct_map = {
        "audio/mpeg": "mp3", "audio/mp3": "mp3",
        "audio/wav": "wav", "audio/x-wav": "wav", "audio/wave": "wav",
        "audio/ogg": "ogg", "audio/flac": "flac",
        "audio/mp4": "m4a", "audio/m4a": "m4a", "audio/x-m4a": "m4a",
        "audio/aac": "aac", "audio/webm": "webm",
        "video/webm": "webm", "video/mp4": "mp4",
    }
    return ct_map.get(content_type or "", "webm")


def convert_to_wav(input_path: str, ext: str) -> str:
    """
    Convert audio to 16 kHz mono WAV for best mlx-whisper results.
    Falls back to the original file if ffmpeg is missing.
    """
    if ext == "wav":
        return input_path

    wav_path = input_path.rsplit(".", 1)[0] + ".wav"
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", input_path,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                wav_path,
            ],
            capture_output=True, check=True, timeout=300,
        )
        return wav_path
    except FileNotFoundError:
        print("  ⚠ ffmpeg not found — transcribing without conversion", file=sys.stderr)
        return input_path
    except subprocess.CalledProcessError as e:
        print(f"  ⚠ ffmpeg error: {e.stderr.decode()[:200]}", file=sys.stderr)
        return input_path


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "hu-stt-offline",
        "version": "1.0.0",
        "model": DEFAULT_MODEL,
        "backend": "mlx-whisper (Apple Silicon)",
    }


@app.post("/api/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    language: str = Form(default="hu"),
    timestamps: str = Form(default="word"),
):
    """
    Transcribe audio locally using mlx-whisper on Apple Silicon.
    Supports: mp3, wav, ogg, flac, m4a, mp4, aac, webm
    """
    mlx_whisper = get_mlx_whisper()

    try:
        audio_bytes = await audio.read()

        if len(audio_bytes) < 100:
            raise HTTPException(status_code=400, detail="Audio file is too small or empty")

        if len(audio_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum: {MAX_UPLOAD_BYTES // (1024*1024)} MB",
            )

        ext = get_file_extension(audio.filename, audio.content_type)

        # Write to temp file (mlx-whisper requires a file path)
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            audio_path = convert_to_wav(tmp_path, ext)

            lang_param = None if language == "auto" else language

            kwargs = {
                "path_or_hf_repo": DEFAULT_MODEL,
                "verbose": False,
            }
            if lang_param:
                kwargs["language"] = lang_param
            if timestamps == "word":
                kwargs["word_timestamps"] = True

            size_mb = len(audio_bytes) / (1024 * 1024)
            print(f"  Transcribing: {audio.filename or 'recording'} ({size_mb:.1f} MB, .{ext})")

            t0 = time.time()
            result = mlx_whisper.transcribe(audio_path, **kwargs)
            elapsed = time.time() - t0

            print(f"  Done in {elapsed:.1f}s")

            text = result.get("text", "").strip()

            words = []
            if timestamps == "word" and "segments" in result:
                for seg in result["segments"]:
                    for w in seg.get("words", []):
                        words.append({
                            "text": w.get("word", ""),
                            "start": w.get("start", 0),
                            "end": w.get("end", 0),
                            "speaker_id": None,
                        })

            detected_lang = result.get("language", language)

            return {
                "text": text,
                "language_code": detected_lang,
                "words": words,
                "success": True,
                "processing_time_s": round(elapsed, 2),
                "model": DEFAULT_MODEL,
            }

        finally:
            for p in [tmp_path, tmp_path.rsplit(".", 1)[0] + ".wav"]:
                try:
                    os.unlink(p)
                except OSError:
                    pass

    except HTTPException:
        raise
    except Exception as e:
        print(f"  ✗ Error: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")


# ─── Serve frontend ─────────────────────────────────────────────────────────

DIST = Path(__file__).parent / "frontend" / "dist"

if DIST.exists():
    if (DIST / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="assets")

    @app.get("/")
    async def root():
        return FileResponse(str(DIST / "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        return FileResponse(str(DIST / "index.html"))


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5000))

    print()
    print("═" * 58)
    print("  Magyar Beszédfelismerő — Offline Mode")
    print("  100% local · Apple Silicon · No internet needed")
    print(f"  Model: {DEFAULT_MODEL}")
    print("═" * 58)
    print(f"\n  → Open in browser: http://localhost:{port}")
    print(f"\n  IMPORTANT: use http:// not https://")
    print(f"  (This is a local server without SSL.)\n")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        timeout_keep_alive=30,
    )
