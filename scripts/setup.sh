#!/usr/bin/env bash
# setup.sh — Master setup script: builds all C++ backends and downloads models
# Usage: bash scripts/setup.sh
#
# This script is designed to run on a fresh clone and produce a working environment.
# It runs all build scripts in order, then downloads models.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

SCRIPTS_DIR="$REPO_DIR/scripts"
LOG_FILE="$REPO_DIR/setup.log"

echo "============================================"
echo " longform-lore-videos — Full Setup"
echo " $(date)"
echo "============================================"

# Log all output
exec > >(tee -a "$LOG_FILE") 2>&1

echo ""
echo "📋 Step 1/4: Building llama.cpp ..."
bash "$SCRIPTS_DIR/build_llamacpp.sh"
echo ""

echo "📋 Step 2/4: Building stable-diffusion.cpp ..."
bash "$SCRIPTS_DIR/build_sdcpp.sh"
echo ""

echo "📋 Step 3/4: Building whisper.cpp ..."
bash "$SCRIPTS_DIR/build_whispercpp.sh"
echo ""

echo "📋 Step 4/4: Downloading models ..."
bash "$SCRIPTS_DIR/download_models.sh"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies ..."
pip install -e ".[dev]" --quiet 2>/dev/null || pip install -e "." --quiet

echo ""
echo "============================================"
echo " Setup complete! ✅"
echo " Log: $LOG_FILE"
echo "============================================"

# Run health check
python3 -c "
from longform_lore_videos.config import health_check
import json
h = health_check()
print(json.dumps(h, indent=2, default=str))
" 2>/dev/null || echo "Health check skipped (config not yet importable)"
