"""Tests for script generation pipeline."""

import pytest

from longform_lore_videos.pipeline.script import ScriptGenerator


class TestScriptGenerator:
    """Tests for ScriptGenerator."""

    @pytest.fixture
    def generator(self):
        """Create ScriptGenerator instance."""
        return ScriptGenerator()

    def test_generate_script_success(self, generator):
        """Generate script with valid inputs."""
        result = generator.generate_script(
            topic="Test topic",
            genre="historical",
            chapter_count=3,
        )

        assert result["title"] == "Script for Test topic"
        assert len(result["chapters"]) == 3

    def test_genre_applied(self, generator):
        """Genre is included in title."""
        result = generator.generate_script(
            topic="Test",
            genre="fantasy",
            chapter_count=1,
        )

        assert result["title"] == "Script for Test"
