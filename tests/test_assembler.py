"""Tests for VideoAssembler."""

import os
import tempfile
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

    @patch("moviepy.VideoFileClip")
    @patch("moviepy.AudioFileClip")
    def test_assemble_single_chapter(self, mock_audio, mock_video):
        """Assemble with single chapter produces valid output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = os.path.join(tmpdir, "job456")
            chapter_dir = os.path.join(job_dir, "chapters", "chapter_001")
            os.makedirs(chapter_dir)
            
            # Create dummy asset files
            with open(os.path.join(chapter_dir, "image_001.png"), "w") as f:
                f.write("dummy")
            with open(os.path.join(chapter_dir, "narration.mp3"), "w") as f:
                f.write("dummy")
            with open(os.path.join(chapter_dir, "subtitles.srt"), "w") as f:
                f.write("dummy")
            
            assembler = VideoAssembler()
            
            # Mock the video/audio clips
            mock_clip = MagicMock()
            mock_clip.duration = 10.0
            mock_clip.write_videofile = MagicMock(return_value=None)
            mock_video.return_value.__enter__ = MagicMock(return_value=mock_clip)
            mock_video.return_value.__exit__ = MagicMock(return_value=None)
            
            mock_audio_clip = MagicMock()
            mock_audio_clip.volumex = MagicMock(return_value=mock_audio_clip)
            mock_audio.return_value.__enter__ = MagicMock(return_value=mock_audio_clip)
            mock_audio.return_value.__exit__ = MagicMock(return_value=None)
            
            result = assembler.assemble(job_dir)
            
            assert result is not None

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
