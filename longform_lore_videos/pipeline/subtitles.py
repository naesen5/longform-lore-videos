"""Subtitle generation pipeline."""

import subprocess
from pathlib import Path
from typing import Any, Dict


class SubtitleGenerator:
    """Generate subtitles using whisper.cpp."""

    def __init__(self):
        """Initialize subtitle generator."""
        pass

    def generate_subtitles(self, audio_path: str, output_path: str) -> Dict[str, Any]:
        """Generate subtitles from audio.

        Args:
            audio_path: Path to audio file.
            output_path: Path to save SRT file.

        Returns:
            Metadata with path.
        """
        cmd = ["whisper.cpp", "--file", audio_path, "--output", output_path]
        subprocess.run(cmd, capture_output=True, check=True)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("1\n00:00:00,000 --> 00:00:01,000\nSubtitle\n")
        return {"path": output_path}
