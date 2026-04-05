"""Tests for video assembly pipeline."""


import pytest

from longform_lore_videos.pipeline.assembly import VideoAssembler


class TestVideoAssembler:
    """Tests for VideoAssembler."""

    @pytest.fixture
    def generator(self):
        """Create VideoAssembler instance."""
        return VideoAssembler()

    def test_assemble_video_success(self, generator, tmp_path):
        """Assemble video successfully."""
        (tmp_path / "chapter_0.mp4").write_bytes(b"VIDEO1")
        (tmp_path / "chapter_1.mp4").write_bytes(b"VIDEO2")

        output_path = tmp_path / "final.mp4"
        generator.assemble_video(
            chapter_paths=[str(tmp_path / "chapter_0.mp4"), str(tmp_path / "chapter_1.mp4")],
            audio_path=str(tmp_path / "narration.wav"),
            output_path=str(output_path),
        )

        assert output_path.exists()

    def test_audio_mixing_accepted(self, generator, tmp_path):
        """Audio path is accepted."""
        (tmp_path / "chapter_0.mp4").write_bytes(b"VIDEO")

        output_path = tmp_path / "final.mp4"
        generator.assemble_video(
            chapter_paths=[str(tmp_path / "chapter_0.mp4")],
            audio_path=str(tmp_path / "narration.wav"),
            output_path=str(output_path),
        )

        assert output_path.exists()

    def test_output_directory_created(self, generator, tmp_path):
        """Output directory is created if missing."""
        (tmp_path / "chapter_0.mp4").write_bytes(b"VIDEO")

        output_dir = tmp_path / "output"
        output_path = output_dir / "final.mp4"

        generator.assemble_video(
            chapter_paths=[str(tmp_path / "chapter_0.mp4")],
            audio_path=str(tmp_path / "narration.wav"),
            output_path=str(output_path),
        )

        assert output_dir.exists()
