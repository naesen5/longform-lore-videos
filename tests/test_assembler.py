"""Tests for VideoAssembler."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from longform_lore_videos.assembler import VideoAssembler


class TestVideoAssembler:
    """Test suite for VideoAssembler."""

    def test_init_default_quality(self):
        """Initialize with default quality preset."""
        assembler = VideoAssembler()
        assert assembler.quality == "standard"

    def test_init_custom_quality(self):
        """Initialize with custom quality preset."""
        assembler = VideoAssembler(quality="hq")
        assert assembler.quality == "hq"

    def test_init_invalid_quality(self):
        """Initialize with invalid quality raises ValueError."""
        with pytest.raises(ValueError):
            VideoAssembler(quality="invalid")

    @patch("moviepy.VideoFileClip")
    @patch("moviepy.AudioFileClip")
    def test_assemble_no_assets(self, mock_audio, mock_video):
        """Assemble with no assets produces empty video."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = os.path.join(tmpdir, "job123")
            os.makedirs(job_dir)
            
            assembler = VideoAssembler()
            result = assembler.assemble(job_dir)
            
            assert result is None  # No chapter clips to assemble

    # Integration test temporarily disabled — requires actual video processing setup
   # def test_assemble_single_chapter_integration(self):
   #     """Assemble with single chapter produces valid output (integration test)."""
   #     pass  # Placeholder for future integration test

    def test_quality_presets(self):
        """Verify quality preset parameters."""
        assembler = VideoAssembler(quality="draft")
        assert assembler._get_quality_params() == {
            "resolution": (1280, 720),
            "crf": 28,
            "preset": "fast",
        }

        assembler = VideoAssembler(quality="standard")
        assert assembler._get_quality_params() == {
            "resolution": (1920, 1080),
            "crf": 23,
            "preset": "medium",
        }

        assembler = VideoAssembler(quality="hq")
        assert assembler._get_quality_params() == {
            "resolution": (1920, 1080),
            "crf": 18,
            "preset": "slow",
        }
