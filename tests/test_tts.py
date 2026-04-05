"""Tests for TTS narration pipeline."""

import pytest

from longform_lore_videos.pipeline.tts import TTSNarrator


class TestTTSNarrator:
    """Tests for TTSNarrator."""

    @pytest.fixture
    def narrator(self):
        """Create TTSNarrator instance."""
        return TTSNarrator()

    def test_generate_narration_success(self, narrator, tmp_path):
        """Generate narration audio successfully."""
        output_path = tmp_path / "output.wav"
        narrator.generate_narration(
            text="Test narration",
            voice="default",
            output_path=str(output_path),
        )

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_duration_recorded(self, narrator, tmp_path):
        """Duration is calculated from text length."""
        output_path = tmp_path / "test.wav"
        metadata = narrator.generate_narration(
            text="Test",
            voice="default",
            output_path=str(output_path),
        )

        assert metadata["duration_s"] > 0

    def test_voice_parameter_accepted(self, narrator, tmp_path):
        """Voice parameter is accepted."""
        output_path = tmp_path / "test.wav"
        metadata = narrator.generate_narration(
            text="Test",
            voice="custom-voice",
            output_path=str(output_path),
        )

        assert metadata["path"] == str(output_path)
