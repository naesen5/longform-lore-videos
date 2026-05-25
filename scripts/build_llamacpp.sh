#!/usr/bin/env bash
# build_llamacpp.sh — Clone and build llama.cpp, then install llama-cpp-python
# Usage: bash scripts/build_llamacpp.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LLAMA_DIR="$REPO_DIR/../llama.cpp"
BUILD_DIR="$LLAMA_DIR/build"
METAL_FLAG=""

# Detect platform
if [[ "$(uname)" == "Darwin" ]]; then
    METAL_FLAG="-DGGML_METAL=ON"
    echo "🍎 macOS detected — building with Metal support"
else
    # Check for CUDA
    if command -v nvcc &>/dev/null; then
        METAL_FLAG="-DGGML_CUDA=ON"
        echo "🟢 CUDA detected — building with GPU support"
    else
        METAL_FLAG=""
        echo "🖥️  Linux CPU build (no CUDA detected)"
    fi
fi

# Clone if not present
if [[ ! -d "$LLAMA_DIR/.git" ]]; then
    echo "📦 Cloning ggml-org/llama.cpp ..."
    git clone --depth 1 https://github.com/ggml-org/llama.cpp.git "$LLAMA_DIR"
else
    echo "✅ llama.cpp already cloned — pulling latest"
    cd "$LLAMA_DIR"
    git pull --ff-only
    cd "$REPO_DIR"
fi

# Build llama.cpp
echo "🔨 Building llama.cpp ..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

cmake .. -B . $METAL_FLAG \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$BUILD_DIR/install"

cmake --build . --config Release --parallel $(sysctl -n hw.ncpu 2>/dev/null || nproc)

echo "✅ llama.cpp built successfully"

# Install llama-cpp-python with Metal/CUDA flags
echo "📦 Installing llama-cpp-python ..."
cd "$REPO_DIR"

if [[ "$(uname)" == "Darwin" ]]; then
    LLAMA_CPP_PYTHON_METAL=1 pip install -U llama-cpp-python --quiet
else
    pip install -U llama-cpp-python --quiet
fi

echo "✅ llama-cpp-python installed"

# Verify import
python3 -c "import llama_cpp; print(f'✅ llama_cpp v{llama_cpp.__version__}')" 2>/dev/null || echo "⚠️ llama_cpp import failed"

echo "🎉 build_llamacpp.sh complete"
