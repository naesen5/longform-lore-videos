"""Seameless audio looping utilities."""
import numpy as np


def find_loop_point(audio: np.ndarray, sample_rate: int = 44100) -> int:
    """
    Find optimal loop point (zero-crossing with minimum energy).
    
    Args:
        audio: Audio array
        sample_rate: Sample rate in Hz
        
    Returns:
        Sample index for loop point
    """
    # Look for zero-crossings in the last 90% of audio (allow flexibility)
    search_start = int(len(audio) * 0.1)
    search_region = audio[search_start:]
    
    # Find zero-crossings
    zero_crossings = np.where(np.diff(np.sign(search_region)))[0]
    
    if len(zero_crossings) == 0:
        # Fallback: use 90% position
        return int(len(audio) * 0.9)
    
    # Find zero-crossing with minimum energy (smoothest transition)
    min_energy = float('inf')
    best_idx = zero_crossings[0]
    
    for idx in zero_crossings[:10]:  # Check first 10 zero-crossings
        # Look around this point for minimum energy
        window = search_region[max(0, idx-5):idx+5]
        energy = np.sum(window ** 2)
        if energy < min_energy:
            min_energy = energy
            best_idx = idx
    
    return search_start + best_idx


def crossfade(audio1: np.ndarray, audio2: np.ndarray, fade_length: int) -> np.ndarray:
    """
    Apply crossfade between two audio segments.
    
    Args:
        audio1: First audio segment
        audio2: Second audio segment (must be same length as audio1)
        fade_length: Length of fade in samples
        
    Returns:
        Crossfaded audio
    """
    if len(audio1) != len(audio2):
        raise ValueError("Audio segments must be same length for crossfade")
    
    # Create fade curve
    fade_in = np.linspace(0, 1, fade_length)
    fade_out = np.linspace(1, 0, fade_length)
    
    # Apply crossfade
    result = np.zeros(len(audio1))
    result[:fade_length] = audio1[:fade_length] * fade_out + audio2[:fade_length] * fade_in
    result[fade_length:-fade_length] = audio1[fade_length:-fade_length] + audio2[fade_length:-fade_length]
    result[-fade_length:] = audio1[-fade_length:] * fade_out + audio2[-fade_length:] * fade_in
    
    return result


def loop_audio(
    audio: np.ndarray,
    target_duration_s: float,
    sample_rate: int = 44100,
    fade_in: float = 3.0,
    fade_out: float = 5.0
) -> np.ndarray:
    """
    Loop audio seamlessly to reach target duration.
    
    Args:
        audio: Input audio array
        target_duration_s: Target duration in seconds
        sample_rate: Sample rate in Hz
        fade_in: Fade-in length in seconds
        fade_out: Fade-out length in seconds
        
    Returns:
        Looped audio of target duration
    """
    target_samples = int(target_duration_s * sample_rate)
    current_samples = len(audio)
    
    if current_samples >= target_samples:
        return audio[:target_samples]
    
    # Find loop point
    loop_point = find_loop_point(audio, sample_rate)
    
    # Extract loopable segment
    loop_segment = audio[loop_point:]
    
    # Calculate how many loops needed
    remaining = target_samples - current_samples
    loops_needed = max(1, int(remaining / len(loop_segment)) + 1)
    
    # Build looped audio
    looped = audio.copy()
    for _ in range(loops_needed):
        # Apply crossfade at join point
        fade_samples = min(int(fade_in * sample_rate), int(fade_out * sample_rate), len(loop_segment) // 2)
        if len(looped) >= loop_point + fade_samples:
            # Overlap-add with crossfade
            overlap_start = len(looped) - fade_samples
            overlap_end = overlap_start + len(loop_segment)
            
            # Create overlapping region
            segment_start = max(0, overlap_start - loop_point)
            segment_end = segment_start + fade_samples
            
            if segment_end <= len(loop_segment) and overlap_end <= target_samples:
                fade_curve = np.linspace(1, 0, fade_samples)
                looped[overlap_start:overlap_start+fade_samples] *= fade_curve
                looped[overlap_start:overlap_start+fade_samples] += loop_segment[segment_start:segment_start+fade_samples] * (1 - fade_curve)
        
        looped = np.concatenate([looped, loop_segment])
        
        if len(looped) >= target_samples:
            break
    
    return looped[:target_samples]


def create_loop_pipeline(
    audio: np.ndarray,
    target_duration_s: float,
    sample_rate: int = 44100
) -> np.ndarray:
    """
    Create a looped audio pipeline with smooth transitions.
    
    Args:
        audio: Input audio array
        target_duration_s: Target duration in seconds
        sample_rate: Sample rate in Hz
        
    Returns:
        Looped audio of target duration
    """
    # Find optimal loop point
    loop_point = find_loop_point(audio, sample_rate)
    
    # Extract loop segment
    loop_segment = audio[loop_point:]
    
    # Calculate loop count
    target_samples = int(target_duration_s * sample_rate)
    loop_count = max(1, int(target_samples / len(loop_segment)) + 1)
    
    # Build looped audio with smooth transitions
    result = []
    prev_end = audio[:loop_point]
    
    for i in range(loop_count):
        current_loop = loop_segment
        
        if i == 0:
            # First loop: just use audio up to loop point
            result.append(audio[:loop_point])
        else:
            # Subsequent loops: crossfade with previous
            fade_samples = min(int(0.5 * sample_rate), len(loop_segment) // 4)  # 0.5s fade
            if len(prev_end) >= fade_samples:
                # Crossfade between previous and current
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                overlap = prev_end[-fade_samples:] * fade_out + current_loop[:fade_samples] * fade_in
                result.append(overlap)
            else:
                result.append(current_loop[:fade_samples])
        
        result.append(current_loop[fade_samples:])
        prev_end = current_loop
    
    return np.concatenate(result)[:target_samples]
