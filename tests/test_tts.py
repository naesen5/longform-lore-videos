"""Tests for the TTS narration pipeline."""
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pipeline.tts import NarrationGenerator


class TestNarrationGenerator:
    """Unit tests for NarrationGenerator."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        gen = NarrationGenerator()
        assert gen.preset == "standard"
        assert gen.voice_path is None
        assert gen.output_dir == Path("output")

    def test_init_custom_preset(self):
        """Test initialization with custom preset."""
        gen = NarrationGenerator(preset="draft")
        assert gen.preset == "draft"

    def test_init_invalid_preset(self):
        """Test initialization with invalid preset raises error."""
        with pytest.raises(ValueError, match="Invalid preset"):
            NarrationGenerator(preset="invalid")

    def test_init_voice_path(self):
        """Test initialization with voice path."""
        gen = NarrationGenerator(voice_path="/path/to/speaker.wav")
        assert gen.voice_path == "/path/to/speaker.wav"

    @patch("pipeline.tts.TTS")
    def test_generate_chapter_mock(self, mock_tts_class):
        """Test generate_chapter with mocked TTS."""
        # Mock TTS model
        mock_model = MagicMock()
        mock_model.tts.return_value = np.array([0.1, -0.1, 0.05, -0.05], dtype=np.float32)
        mock_tts_class.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(output_dir=tmpdir)
            duration = gen.generate_chapter(
                text="Hello world",
                chapter_num=1,
                job_id="test-job",
            )

            # Verify model was called
            mock_model.tts.assert_called_once()
            args = mock_model.tts.call_args
            assert args[0][0] == "Hello world"

            # Verify output file exists
            out_path = Path(tmpdir) / "test-job" / "narration" / "chapter_1.wav"
            assert out_path.exists()

            # Verify duration returned
            assert duration > 0

    @patch("pipeline.tts.TTS")
    def test_generate_chapter_voice_cloning(self, mock_tts_class):
        """Test generate_chapter with voice cloning."""
        mock_model = MagicMock()
        mock_model.tts_from_file.return_value = np.array([0.1, -0.1], dtype=np.float32)
        mock_tts_class.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(
                preset="hq",
                voice_path="/path/to/speaker.wav",
                output_dir=tmpdir,
            )
            gen.generate_chapter(text="Test", chapter_num=1, job_id="test")

            mock_model.tts_from_file.assert_called_once()
            args = mock_model.tts_from_file.call_args
            assert args[0][0] == "Test"
            assert args[1]["speaker_wav"] == "/path/to/speaker.wav"

    def test_generate_chapter_empty_text(self):
        """Test generate_chapter with empty text raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(output_dir=tmpdir)
            with pytest.raises(ValueError, match="Text cannot be empty"):
                gen.generate_chapter(text="", chapter_num=1, job_id="test")

    def test_generate_chapter_long_text(self):
        """Test generate_chapter with too long text raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(output_dir=tmpdir)
            long_text = "x" * 5001
            with pytest.raises(ValueError, match="Text too long"):
                gen.generate_chapter(text=long_text, chapter_num=1, job_id="test")

    @patch("pipeline.tts.TTS")
    def test_generate_batch(self, mock_tts_class):
        """Test generate_batch."""
        mock_model = MagicMock()
        mock_model.tts.return_value = np.array([0.1, -0.1, 0.05], dtype=np.float32)
        mock_tts_class.return_value = mock_model

        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(output_dir=tmpdir)
            chapters = ["First chapter", "Second chapter"]
            durations = gen.generate_batch(chapters=chapters, job_id="test")

            assert len(durations) == 2
            assert all(d > 0 for d in durations)
