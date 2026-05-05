#!/usr/bin/env bash
# generate_script.sh — End-to-end script generation from lore text
# Usage: ./scripts/generate_script.sh <input_lore.txt> [output_script.json]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INPUT_FILE="${1:-}"
OUTPUT_FILE="${2:-$REPO_DIR/output/script.json}"

if [[ -z "$INPUT_FILE" ]]; then
    echo "Usage: $0 <input_lore.txt> [output_script.json]"
    echo "  input_lore.txt   Path to lore/story text file"
    echo "  output_script.json  Output path (default: output/script.json)"
    exit 1
fi

if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: Input file not found: $INPUT_FILE"
    exit 1
fi

echo "=== Script Generation Pipeline ==="
echo "Input:  $INPUT_FILE"
echo "Output: $OUTPUT_FILE"

# Create output directory
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Run the Python script generator
cd "$REPO_DIR"
python3 -c "
import sys, json
sys.path.insert(0, '.')
from longform_lore_videos.pipeline.script import ScriptGenerator

# Read input lore
with open('$INPUT_FILE') as f:
    lore_text = f.read()

# Derive title from filename
import os
title = os.path.splitext(os.path.basename('$INPUT_FILE'))[0]

# Generate script (mock mode — no llama.cpp required)
try:
    gen = ScriptGenerator()
    # Try real generation first
    gen.load()
    script = gen.generate(lore_text=lore_text, title=title)
    print('Real generation successful')
except Exception as e:
    print(f'Note: {e}')
    print('Falling back to mock generation (llama.cpp not available)')
    # Mock fallback: create a structured script from lore text
    paragraphs = [p.strip() for p in lore_text.split('\n\n') if p.strip()]
    chapters = []
    for i, para in enumerate(paragraphs, start=1):
        chapters.append({
            'title': f'Chapter {i}: {para[:50]}...',
            'scenes': [{
                'speaker': 'Narrator',
                'text': para,
                'description': f'Original lore paragraph {i}'
            }]
        })
    script = ScriptGenerator._parse_output(
        ScriptGenerator(),
        json.dumps({'title': title, 'chapters': chapters})
    )

# Write output
output = {'title': script.title, 'chapters': [
    {'title': ch.title, 'scenes': [
        {'speaker': s.speaker, 'text': s.text, 'description': s.description}
        for s in ch.scenes
    ]}
    for ch in script.chapters
]}

with open('$OUTPUT_FILE', 'w') as f:
    json.dump(output, f, indent=2)

print(f'Script saved to $OUTPUT_FILE')
print(f'Chapters: {len(output[\"chapters\"])}')
"

echo "=== Done ==="
echo "Output: $OUTPUT_FILE"
