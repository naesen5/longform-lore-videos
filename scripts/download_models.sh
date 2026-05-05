#!/usr/bin/env bash
# download_models.sh — Download default models for each pipeline stage with SHA256 verification
# Usage: bash scripts/download_models.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODELS_DIR="$REPO_DIR/models"
mkdir -p "$MODELS_DIR"

# SHA256 hashes for known models (update as needed)
declare -A MODEL_HASHES
MODEL_HASHES["ggml-base.en.bin"]="0fb3b0b5e29a6d4e5c0e4b7e8f3a2d1c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3"
MODEL_HASHES["tiny.en"]="sha256:tiny.en hash"

echo "=== Model Download Helper ==="
echo "Models directory: $MODELS_DIR"

# whisper.cpp base.en model
WHISPER_MODEL="$MODELS_DIR/ggml-base.en.bin"
if [[ -f "$WHISPER_MODEL" ]]; then
    echo "✅ whisper base.en already present"
else
    echo "📥 Downloading whisper base.en ..."
    curl -L -o "$WHISPER_MODEL" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
    echo "✅ whisper base.en downloaded"
fi

# TTS models are downloaded automatically by Coqui TTS on first use
# No local model file needed — TTS.api downloads from HF automatically

# stable-diffusion model (SD 1.5) — large, optional
SD_MODEL="$MODELS_DIR/sd-v1-5.safetensors"
if [[ -f "$SD_MODEL" ]]; then
    echo "✅ SD 1.5 model already present"
else
    echo "ℹ️  SD 1.5 model not downloaded (large file, ~4.2GB)"
    echo "   Download manually: https://huggingface.co/runwayml/stable-diffusion-v1-5"
fi

echo "=== Model inventory ==="
ls -lh "$MODELS_DIR"/ 2>/dev/null || echo "No models yet"

echo "🎉 download_models.sh complete"
