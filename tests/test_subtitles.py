"""Tests for subtitle generation pipeline."""
import json

from pipeline.subtitles import SubtitleGenerator


class TestSubtitleGenerator:
    def test_init(self):
        gen = SubtitleGenerator()
        assert gen.model_id == "small.en"

    def test_model_sizes(self):
        gen = SubtitleGenerator(model_size="draft")
        assert gen.model_id == "base.en"
        gen = SubtitleGenerator(model_size="hq")
        assert gen.model_id == "medium.en"

    def test_to_srt_time(self):
        gen = SubtitleGenerator()
        assert gen._to_srt_time(0) == "00:00:00,000"
        assert gen._to_srt_time(1.5) == "00:00:01,500"
        assert gen._to_srt_time(65.25) == "00:01:05,250"
        assert gen._to_srt_time(3661.123) == "01:01:01,123"

    def test_generate_creates_files(self, tmp_path, monkeypatch):
        gen = SubtitleGenerator(output_dir=str(tmp_path))
        mock_output = json.dumps({
            "words": [
                {"text": "Hello", "start": 0.0, "end": 0.5},
                {"text": "world", "start": 0.5, "end": 1.0},
            ]
        })
        def mock_run(*args, **kwargs):
            class Result:
                returncode = 0
                stdout = mock_output
                stderr = ""
            return Result()
        monkeypatch.setattr("subprocess.run", mock_run)
        chapters = [{"audio_path": "/tmp/test.wav", "duration_s": 10.0}]
        srt_files = gen.generate("test-job", chapters)
        assert len(srt_files) == 1
        assert "chapter_0.srt" in srt_files[0]
TESTSUBTILES

# Resolve test_tts.py - just remove the blank line
cat > tests/test_tts.py << 'TESTTTSEOF'
"""Tests for the TTS narration pipeline."""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from pipeline.tts import NarrationGenerator


class TestNarrationGenerator:
    def test_init_defaults(self):
        gen = NarrationGenerator()
        assert gen.preset == "standard"
        assert gen.voice_path is None
        assert gen.output_dir == Path("output")

    def test_init_custom_preset(self):
        gen = NarrationGenerator(preset="draft")
        assert gen.preset == "draft"

    def test_init_invalid_preset(self):
        with pytest.raises(ValueError, match="Invalid preset"):
            NarrationGenerator(preset="invalid")

    def test_init_voice_path(self):
        gen = NarrationGenerator(voice_path="/path/to/speaker.wav")
        assert gen.voice_path == "/path/to/speaker.wav"

    def test_generate_chapter_mock(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(output_dir=tmpdir)
            with patch.object(gen, '_init_model') as mock_init:
                mock_model = MagicMock()
                mock_model.tts.return_value = np.array([0.1] * 2400, dtype=np.float32)
                mock_init.return_value = mock_model
                with patch('pipeline.tts.loudnorm') as mock_loudnorm:
                    mock_loudnorm.return_value = np.array([0.1] * 2400, dtype=np.float32)
                    duration = gen.generate_chapter(text="Hello world", chapter_num=1, job_id="test-job")
                    mock_model.tts.assert_called_once()
                    args = mock_model.tts.call_args
                    assert args[1]["text"] == "Hello world"
                    out_path = Path(tmpdir) / "test-job" / "narration" / "chapter_1.wav"
                    assert out_path.exists()
                    assert duration > 0

    def test_generate_chapter_voice_cloning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(preset="hq", voice_path="/path/to/speaker.wav", output_dir=tmpdir)
            with patch.object(gen, '_init_model') as mock_init:
                mock_model = MagicMock()
                mock_model.tts_with_vc.return_value = np.array([0.1] * 2400, dtype=np.float32)
                mock_init.return_value = mock_model
                with patch('pipeline.tts.loudnorm') as mock_loudmock:
                    mock_loudnorm.return_value = np.array([0.1] * 2400, dtype=np.float32)
                    gen.generate_chapter(text="Test", chapter_num=1, job_id="test")
                    mock_model.tts_with_vc.assert_called_once()
                    args = mock_model.tts_with_vc.call_args
                    assert args[1]["text"] == "Test"
                    assert args[1]["speaker_wav"] == "/path/to/speaker.wav"

    def test_generate_chapter_empty_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(output_dir=tmpdir)
            with pytest.raises(ValueError, match="Text cannot be empty"):
                gen.generate_chapter(text="", chapter_num=1, job_id="test")

    def test_generate_chapter_long_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(output_dir=tmpdir)
            long_text = "x" * 5001
            with pytest.raises(ValueError, match="Text too long"):
                gen.generate_chapter(text=long_text, chapter_num=1, job_id="test")

    def test_generate_batch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = NarrationGenerator(output_dir=tmpdir)
            with patch.object(gen, '_init_model') as mock_init:
                mock_model = MagicMock()
                mock_model.tts.return_value = np.array([0.1] * 2400, dtype=np.float32)
                mock_init.return_value = mock_model
                with patch('pipeline.tts.loudnorm') as mock_loudnorm:
                    mock_loudnorm.return_value = np.array([0.1] * 2400, dtype=np.float32)
                    chapters = ["First chapter", "Second chapter"]
                    durations = gen.generate_batch(chapters=chapters, job_id="test")
                    assert len(durations) == 2
                    assert all(d > 0 for d in durations)
TESTTTSEOF

echo "All test files resolved"