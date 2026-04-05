"""Tests for subtitle generation pipeline."""

from unittest.mock import MagicMock, patch

import pytest

from longform_lore_videos.pipeline.subtitles import SubtitleGenerator


class TestSubtitleGenerator:
    """Tests for SubtitleGenerator."""

    @pytest.fixture
    def generator(self):
        """Create SubtitleGenerator instance."""
        return SubtitleGenerator()

    def test_generate_subtitles_success(self, generator, tmp_path):
        """Generate subtitles successfully."""
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()
        srt_path = tmp_path / "subtitles.srt"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"00:00:00,000 --> 00:00:01,000\nSubtitle\n"
        mock_result.stderr = b""

        with patch("longform_lore_videos.pipeline.subtitles.subprocess.run", return_value=mock_result):
            generator.generate_subtitles(
                audio_path=str(audio_path),
                output_path=str(srt_path),
            )

            assert srt_path.exists()
            content = srt_path.read_text()
            assert "Subtitle" in content

    def test_srt_format(self, generator, tmp_path):
        """Output follows SRT format."""
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()
        srt_path = tmp_path / "subtitles.srt"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"00:00:00,000 --> 00:00:01,000\nSubtitle\n"
        mock_result.stderr = b""

        with patch("longform_lore_videos.pipeline.subtitles.subprocess.run", return_value=mock_result):
            generator.generate_subtitles(
                audio_path=str(audio_path),
                output_path=str(srt_path),
            )

            content = srt_path.read_text()
            lines = content.strip().split("\n")
            assert " --> " in lines[1]

    def test_output_directory_created(self, generator, tmp_path):
        """Output directory is created if missing."""
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()
        output_dir = tmp_path / "output"
        srt_path = output_dir / "subtitles.srt"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = b"00:00:00,000 --> 00:00:01,000\nSubtitle\n"
        mock_result.stderr = b""

        with patch("longform_lore_videos.pipeline.subtitles.subprocess.run", return_value=mock_result):
            generator.generate_subtitles(
                audio_path=str(audio_path),
                output_path=str(srt_path),
            )

            assert output_dir.exists()
