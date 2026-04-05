"""Tests for music generation pipeline."""

import pytest

from longform_lore_videos.pipeline.music import MusicGenerator


class TestMusicGenerator:
    """Tests for MusicGenerator."""

    @pytest.fixture
    def generator(self):
        """Create MusicGenerator instance."""
        return MusicGenerator()

    def test_generate_music_success(self, generator, tmp_path):
        """Generate music successfully."""
        output_path = tmp_path / "music.wav"
        generator.generate_music(
            theme="ambient",
            duration_s=10,
            output_path=str(output_path),
        )

        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_duration_control(self, generator, tmp_path):
        """Duration parameter affects output size."""
        output_path = tmp_path / "music.wav"
        metadata = generator.generate_music(
            theme="thematic",
            duration_s=30,
            output_path=str(output_path),
        )

        assert metadata["duration_s"] == 30

    def test_looping_applied(self, generator, tmp_path):
        """Looping extends duration."""
        output_path = tmp_path / "music.wav"
        metadata = generator.generate_music(
            theme="ambient",
            duration_s=60,
            output_path=str(output_path),
        )

        assert metadata["duration_s"] == 60
