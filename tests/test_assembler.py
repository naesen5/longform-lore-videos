"""Tests for VideoAssembler."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from moviepy import AudioFileClip, ColorClip, VideoFileClip
import numpy as np
from PIL import Image

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
            # 1. Create a dummy image (100x100 red) using moviepy's ImageClip
            img_path = os.path.join(chapter_dir, "image_001.png")
            # Create a simple PNG using numpy + PIL
            from PIL import Image
            arr = np.zeros((100, 100, 3), dtype=np.uint8)
            arr[:, :, 0] = 255  # red
            img = Image.fromarray(arr)
            img.save(img_path)
            
            # 2. Create a dummy audio file (10 seconds of silence) using numpy
            audio_path = os.path.join(chapter_dir, "narration.mp3")
            # Generate a simple 10-second mono audio file with numpy + scipy
            import wave
            import struct
            
            # Create a simple WAV file with silent audio
            sample_rate = 22050
            duration = 10  # seconds
            num_samples = sample_rate * duration
            
            with wave.open(audio_path.replace('.mp3', '.wav'), 'w') as wav:
                wav.setnchannels(1)  # mono
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(sample_rate)
                for _ in range(num_samples):
                    wav.writeframes(struct.pack('h', 0))  # silence
            
            # Convert WAV to MP3 using moviepy (minimal dependency)
            audio_clip = AudioFileClip(audio_path.replace('.mp3', '.wav'))
            audio_clip.write_audiofile(audio_path, fps=22050)
            audio_clip.close()
            os.remove(audio_path.replace('.mp3', '.wav'))
            
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
