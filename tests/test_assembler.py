"""Tests for VideoAssembler."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from moviepy import AudioFileClip, ColorClip, VideoFileClip
import numpy as np

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

    @pytest.mark.integration
    def test_assemble_single_chapter_integration(self):
        """Assemble with single chapter produces valid output (integration test)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_dir = os.path.join(tmpdir, "job456")
            chapter_dir = os.path.join(job_dir, "chapters", "chapter_001")
            os.makedirs(chapter_dir)
            
            # Create actual test assets using moviepy
            # 1. Create a dummy image (100x100 red) using ColorClip
            img_path = os.path.join(chapter_dir, "image_001.png")
            clip = ColorClip((100, 100), duration=5.0, color=(255, 0, 0))
            clip.write_frame(img_path)
            clip.close()
            
            # 2. Create a dummy audio file (10 seconds of silence)
            audio_path = os.path.join(chapter_dir, "narration.mp3")
            audio = AudioFileClip(__file__)  # use this file as source
            audio = audio.subclip(0, min(10.0, audio.duration))
            audio.write_audiofile(audio_path, fps=22050)
            audio.close()
            
            # 3. Create a dummy subtitles file
            srt_path = os.path.join(chapter_dir, "subtitles.srt")
            with open(srt_path, "w") as f:
                f.write("1\n00:00:00,000 --> 00:00:05,000\nTest subtitle\n\n")
            
            assembler = VideoAssembler()
            result = assembler.assemble(job_dir)
            
            assert result is not None
            assert os.path.exists(result)

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
