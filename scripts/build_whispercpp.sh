#!/usr/bin/env bash
# build_whispercpp.sh — Clone and build whisper.cpp, download base.en model
# Usage: bash scripts/build_whispercpp.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WHISPER_DIR="$REPO_DIR/../whisper.cpp"
BUILD_DIR="$WHISPER_DIR/build"
MODELS_DIR="$REPO_DIR/models"

# Clone if not present
if [[ ! -d "$WHISPER_DIR/.git" ]]; then
    echo "📦 Cloning ggml-org/whisper.cpp ..."
    git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$WHISPER_DIR"
else
    echo "✅ whisper.cpp already cloned — pulling latest"
    cd "$WHISPER_DIR"
    git pull --ff-only
    cd "$REPO_DIR"
fi

# Build whisper.cpp
echo "🔨 Building whisper.cpp ..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

cmake .. -B . \
    -DCMAKE_BUILD_TYPE=Release

cmake --build . --config Release --parallel $(sysctl -n hw.ncpu 2>/dev/null || nproc)

echo "✅ whisper.cpp built successfully"

# Download base.en model
mkdir -p "$MODELS_DIR"
MODEL_PATH="$MODELS_DIR/ggml-base.en.bin"

if [[ ! -f "$MODEL_PATH" ]]; then
    echo "📥 Downloading whisper base.en model ..."
    cd "$MODELS_DIR"
    curl -L -o ggml-base.en.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
    echo "✅ Model downloaded: $(ls -lh ggml-base.en.bin | awk '{print $5}')"
else
    echo "✅ Model already present: $MODEL_PATH"
fi

# Verify CLI
WHISPER_BIN="$BUILD_DIR/bin/Release/whisper-cli"
if [[ ! -f "$WHISPER_BIN" ]]; then
    # Try alternative build path
    WHISPER_BIN=$(find "$BUILD_DIR" -name "whisper-cli" -type f 2>/dev/null | head -1)
fi

if [[ -n "$WHISPER_BIN" && -f "$WHISPER_BIN" ]]; then
    echo "✅ whisper-cli available at $WHISPER_BIN"
else
    echo "⚠️ whisper-cli not found at expected path"
fi

echo "🎉 build_whispercpp.sh complete"
