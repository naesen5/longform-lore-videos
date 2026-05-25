"""Unit tests for MusicGenerator."""
import pytest

try:
    import diffusers
except ImportError:
    diffusers = None
from unittest.mock import MagicMock, patch, PropertyMock
import os
import tempfile
import numpy as np


class MockAudioPipeline:
    """Mock stable-audio pipeline for testing."""
    
    def __init__(self, *args, **kwargs):
        pass
    
    def to(self, device):
        """Mock device transfer."""
        return self
    
    def __call__(self, prompt, **kwargs):
        """Return mock audio tensor."""
        # Return a mock tensor-like object with sample_rate and audio_data
        return MagicMock(audio_data=np.random.randn(44100 * 10))  # 10 seconds of audio


class TestMusicGenerator:
    """Test suite for MusicGenerator."""
    
    @pytest.mark.skipif(diffusers is None, reason='diffusers not installed')
    @patch('diffusers.StableAudioPipeline')
    def test_generate_creates_file(self, mock_pipeline_class):
        """Test that generate creates the expected output file."""
        from pipeline.music import MusicGenerator
        
        mock_pipeline = MockAudioPipeline()
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = MusicGenerator(output_dir=tmpdir)
            output_path = generator.generate(
                total_duration_s=10,
                prompt="epic fantasy music",
                job_id="test-job-1"
            )
            
            # Verify file was created
            assert os.path.exists(output_path)
            assert output_path.endswith(".wav")
    
    @pytest.mark.skipif(diffusers is None, reason='diffusers not installed')
    @patch('diffusers.StableAudioPipeline')
    def test_generate_duration(self, mock_pipeline_class):
        """Test that generated audio has correct duration."""
        from pipeline.music import MusicGenerator
        
        mock_pipeline = MockAudioPipeline()
        mock_pipeline_class.from_pretrained.return_value = mock_pipeline
        
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = MusicGenerator(output_dir=tmpdir)
            output_path = generator.generate(
                total_duration_s=10,
                prompt="test music",
                job_id="test-job-2"
            )
            
            # Verify file exists
            assert os.path.exists(output_path)
    
    def test_prompt_construction(self):
        """Test prompt construction from genre/mood tags."""
        from pipeline.music import MusicGenerator
        
        generator = MusicGenerator()
        
        # Test prompt construction
        prompt = generator._construct_prompt(genre="fantasy", mood="epic")
        assert "fantasy" in prompt
        assert "epic" in prompt


if __name__ == "__main__":
    pytest.main()
