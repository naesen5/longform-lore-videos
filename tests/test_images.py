"""Tests for image generation pipeline."""

from unittest.mock import MagicMock, patch

import pytest

from longform_lore_videos.pipeline.images import ImageGenerator


class TestImageGenerator:
    """Tests for ImageGenerator."""

    @pytest.fixture
    def generator(self):
        """Create ImageGenerator instance."""
        return ImageGenerator()

    def test_generate_image_success(self, generator, tmp_path):
        """Generate image successfully."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"output/image.png"

        with patch("longform_lore_videos.pipeline.images.subprocess.run", return_value=mock_result):
            output_path = tmp_path / "scene.png"
            generator.generate_image(
                prompt="A cinematic scene",
                quality="high",
                output_path=str(output_path),
            )

            assert output_path.exists()

    def test_quality_parameter_accepted(self, generator, tmp_path):
        """Quality parameter is accepted."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"output/image.png"

        with patch("longform_lore_videos.pipeline.images.subprocess.run", return_value=mock_result):
            output_path = tmp_path / "test.png"
            generator.generate_image(
                prompt="Test",
                quality="hd",
                output_path=str(output_path),
            )

            assert output_path.exists()
