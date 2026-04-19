#!/usr/bin/env bash
# build_sdcpp.sh — Clone and build stable-diffusion.cpp, then install Python bindings
# Usage: bash scripts/build_sdcpp.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SD_DIR="$REPO_DIR/../stable-diffusion.cpp"
BUILD_DIR="$SD_DIR/build"

# Detect platform
if [[ "$(uname)" == "Darwin" ]]; then
    echo "🍎 macOS detected — building with Metal support"
    SD_METAL="-DSD_METAL=ON"
else
    echo "🖥️  Linux build"
    SD_METAL=""
fi

# Clone if not present
if [[ ! -d "$SD_DIR/.git" ]]; then
    echo "📦 Cloning leejet/stable-diffusion.cpp ..."
    git clone --depth 1 https://github.com/leejet/stable-diffusion.cpp.git "$SD_DIR"
else
    echo "✅ stable-diffusion.cpp already cloned — pulling latest"
    cd "$SD_DIR"
    git pull --ff-only
    cd "$REPO_DIR"
fi

# Build stable-diffusion.cpp shared library
echo "🔨 Building stable-diffusion.cpp ..."
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

cmake .. -B . $SD_METAL \
    -DCMAKE_BUILD_TYPE=Release \
    -DSD_BUILD_SHARED_LIB=ON \
    -DSD_BUILD_EXAMPLES=OFF \
    -DSD_BUILD_TESTS=OFF

cmake --build . --config Release --parallel $(sysctl -n hw.ncpu 2>/dev/null || nproc)

echo "✅ stable-diffusion.cpp built successfully"

# Install Python bindings
echo "📦 Installing stable-diffusion-cpp-python ..."
cd "$REPO_DIR"
pip install -U stable-diffusion-cpp-python --quiet

echo "✅ stable-diffusion-cpp-python installed"

# Verify import
python3 -c "import stable_diffusion_cpp; print('✅ stable_diffusion_cpp importable')" 2>/dev/null || echo "⚠️ stable_diffusion_cpp import failed"

echo "🎉 build_sdcpp.sh complete"
