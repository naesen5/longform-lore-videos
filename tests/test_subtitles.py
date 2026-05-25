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
