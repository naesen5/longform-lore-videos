"""Tests for script generation pipeline."""

import json
from unittest.mock import patch

import pytest

from longform_lore_videos.pipeline.script import (
    Script,
    ScriptChapter,
    ScriptGenerator,
    Scene,
    Speaker,
)


class TestScriptModels:
    """Test script data models."""

    def test_speaker_creation(self):
        """Test Speaker model creation."""
        speaker = Speaker(name="John", role="narrator")
        assert speaker.name == "John"
        assert speaker.role == "narrator"

    def test_scene_creation(self):
        """Test Scene model creation."""
        scene = Scene(speaker="John", text="Hello world", description="First scene")
        assert scene.speaker == "John"
        assert scene.text == "Hello world"
        assert scene.description == "First scene"

    def test_script_chapter_creation(self):
        """Test ScriptChapter model creation."""
        chapter = ScriptChapter(
            title="Chapter 1",
            scenes=[Scene(speaker="John", text="Text")],
        )
        assert chapter.title == "Chapter 1"
        assert len(chapter.scenes) == 1

    def test_script_creation(self):
        """Test Script model creation."""
        script = Script(
            title="Test Script",
            chapters=[ScriptChapter(title="C1", scenes=[Scene(speaker="J", text="T")])],
        )
        assert script.title == "Test Script"
        assert len(script.chapters) == 1


class TestScriptGenerator:
    """Test ScriptGenerator class."""

    def test_init_defaults(self):
        """Test generator initialization with defaults."""
        gen = ScriptGenerator()
        assert gen.n_ctx == 2048
        assert gen.n_threads == 4
        assert gen._loaded is False

    def test_init_custom(self):
        """Test generator initialization with custom params."""
        gen = ScriptGenerator(model_path="/path/model.gguf", n_ctx=1024, n_threads=2)
        assert gen.model_path == "/path/model.gguf"
        assert gen.n_ctx == 1024
        assert gen.n_threads == 2

    def test_load_import_error(self):
        """Test ImportError when llama-cpp-python not installed."""
        with patch.dict("sys.modules", {"llama_cpp": None}):
            gen = ScriptGenerator()
            with pytest.raises(ImportError, match="llama-cpp-python not installed"):
                gen.load()

    def test_build_prompt_format(self):
        """Test prompt building format."""
        gen = ScriptGenerator()
        prompt = gen._build_prompt("Sample lore", "Test Title")
        assert "Sample lore" in prompt
        assert "Test Title" in prompt
        assert "Script JSON:" in prompt

    def test_parse_output_valid_json(self):
        """Test parsing valid JSON output."""
        gen = ScriptGenerator()
        output = json.dumps({
            "chapters": [
                {
                    "title": "Chapter 1",
                    "scenes": [
                        {"speaker": "John", "text": "Hello", "description": "Desc"}
                    ],
                }
            ]
        })
        result = gen._parse_output(output)
        assert result["chapters"][0]["title"] == "Chapter 1"
        assert result["chapters"][0]["scenes"][0]["speaker"] == "John"

    def test_parse_output_fallback(self):
        """Test fallback when LLM returns non-JSON."""
        gen = ScriptGenerator()
        result = gen._parse_output("Plain text output")
        assert result["chapters"][0]["title"] == "Untitled Chapter"
        assert result["chapters"][0]["scenes"][0]["speaker"] == "Unknown"