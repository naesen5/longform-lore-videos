"""Image generation pipeline."""

import subprocess
from pathlib import Path
from typing import Any, Dict


class ImageGenerator:
    """Generate images using stable-diffusion.cpp."""

    def __init__(self):
        """Initialize image generator."""
        pass

    def generate_image(self, prompt: str, quality: str, output_path: str) -> Dict[str, Any]:
        """Generate an image.

        Args:
            prompt: Image prompt.
            quality: Quality preset (low, standard, high, hd).
            output_path: Path to save PNG file.

        Returns:
            Metadata with path.
        """
        cmd = [
            "stable-diffusion.cpp",
            "--prompt", prompt,
            "--quality", quality,
            "--output", output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, check=True)
        Path(output_path).touch()
        return {"path": output_path}
