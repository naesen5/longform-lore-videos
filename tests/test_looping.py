"""Tests for audio looping functionality."""
import numpy as np
import pytest

from pipeline.loop import find_loop_point, crossfade, loop_audio


class TestFindLoopPoint:
    """Test find_loop_point function."""
    
    def test_finds_zero_crossing(self):
        """Should find a zero-crossing point."""
        # Create audio with clear zero-crossing at index 50
        audio = np.zeros(100)
        audio[:50] = 1.0
        audio[50:] = -1.0
        
        point = find_loop_point(audio)
        assert 45 <= point <= 55  # Should find around index 50
    
    def test_handles_flat_signal(self):
        """Should handle flat signals gracefully."""
        audio = np.ones(100) * 0.5
        point = find_loop_point(audio)
        assert 90 <= point <= 95  # Should fallback to 90% position


class TestCrossfade:
    """Test crossfade function."""
    
    def test_creates_smooth_transition(self):
        """Should create smooth transition between segments."""
        audio1 = np.ones(100)
        audio2 = np.ones(100) * 2.0
        
        result = crossfade(audio1, audio2, 10)
        
        # Should start at 1.0 and end at 2.0
        assert 0.9 < result[0] < 1.1
        assert 1.9 < result[-1] < 2.1
    
    def test_raises_on_mismatched_lengths(self):
        """Should raise error on mismatched lengths."""
        audio1 = np.ones(100)
        audio2 = np.ones(50)
        
        with pytest.raises(ValueError):
            crossfade(audio1, audio2, 10)


class TestLoopAudio:
    """Test loop_audio function."""
    
    def test_extends_short_audio(self):
        """Should extend audio to target duration."""
        audio = np.random.randn(44100)  # 1 second at 44.1kHz
        result = loop_audio(audio, target_duration_s=5.0)
        
        assert len(result) >= 44100 * 5
    
    def test_truncates_long_audio(self):
        """Should truncate audio if already long enough."""
        audio = np.random.randn(44100 * 10)  # 10 seconds
        result = loop_audio(audio, target_duration_s=5.0)
        
        assert len(result) == 44100 * 5
    
    def test_handles_exact_duration(self):
        """Should return audio unchanged if exact duration."""
        audio = np.random.randn(44100 * 5)  # 5 seconds
        result = loop_audio(audio, target_duration_s=5.0)
        
        assert len(result) == 44100 * 5
