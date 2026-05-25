"""Tests for image generation pipeline."""
import pytest


class TestImageGenerator:
    """Test ImageGenerator class."""
    
    def test_init(self):
        """Should initialize with default model."""
        from pipeline.images import ImageGenerator
        gen = ImageGenerator()
        assert gen.model_id == "stabilityai/stable-diffusion-2-1"
    
    def test_construct_prompt(self):
        """Should construct prompt from scene description and genre."""
        from pipeline.images import ImageGenerator
        gen = ImageGenerator()
        prompt = gen._construct_prompt("A fantasy battle scene", "fantasy")
        assert "fantasy battle" in prompt.lower()
    
    def test_construct_negative_prompt(self):
        """Should return negative prompt for NSFW filter."""
        from pipeline.images import ImageGenerator
        gen = ImageGenerator()
        neg_prompt = gen._construct_negative_prompt()
        assert "explicit" in neg_prompt.lower() or "nsfw" in neg_prompt.lower()
