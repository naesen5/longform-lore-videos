"""Music generation pipeline using stable-audio-diffusion."""
import os
from pathlib import Path
from typing import Optional
import numpy as np
import librosa
import torch


class MusicGenerator:
    """Generate thematic background music using local audio diffusion models."""
    
    def __init__(
        self,
        model_id: str = "stabilityai/stable-audio-open-1.0",
        output_dir: str = "output",
        fallback_dir: Optional[str] = None
    ):
        """
        Initialize the music generator.
        
        Args:
            model_id: HuggingFace model ID for stable audio diffusion
            output_dir: Base directory for output files
            fallback_dir: Directory containing CC0 royalty-free fallback clips
        """
        self.model_id = model_id
        self.output_dir = Path(output_dir)
        self.fallback_dir = Path(fallback_dir) if fallback_dir else None
        
        # Initialize pipeline (lazy load)
        self._pipeline = None
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
    
    @property
    def pipeline(self):
        """Lazy-load the stable audio pipeline."""
        if self._pipeline is None:
            from diffusers import StableAudioPipeline
            self._pipeline = StableAudioPipeline.from_pretrained(
                self.model_id,
                torch_dtype=torch.float16 if self._device == "cuda" else torch.float32
            )
            self._pipeline.to(self._device)
        return self._pipeline
    
    def _construct_prompt(self, genre: str = "", mood: str = "") -> str:
        """
        Construct a music generation prompt from genre and mood tags.
        
        Args:
            genre: Music genre (fantasy, sci-fi, medieval, etc)
            mood: Emotional tone (epic, dark, cinematic, etc)
            
        Returns:
            Formatted prompt string
        """
        parts = []
        
        if genre:
            parts.append(f"{genre} music")
        if mood:
            parts.append(mood)
        
        # Add standard descriptors for better generation
        standard_descriptors = [
            "cinthetic orchestral",
            "fantasy theme",
            "ambient background",
            "looping music"
        ]
        parts.extend(standard_descriptors)
        
        return ", ".join(parts)
    
    def generate(
        self,
        total_duration_s: float,
        prompt: str,
        job_id: str,
        genre: str = "",
        mood: str = "",
        per_chapter: bool = False
    ) -> str:
        """
        Generate background music for the video.
        
        Args:
            total_duration_s: Target duration in seconds
            prompt: Text prompt for music generation
            job_id: Job identifier for output path
            genre: Genre tag (optional, used if prompt not provided)
            mood: Mood tag (optional, used if prompt not provided)
            per_chapter: If True, generate separate music per chapter
            
        Returns:
            Path to generated music file
        """
        # Construct prompt from tags if not provided
        if not prompt:
            prompt = self._construct_prompt(genre=genre, mood=mood)
        
        # Calculate duration with 30s buffer
        target_duration = total_duration_s + 30
        
        # Generate audio
        audio_tensor = self._generate_audio(prompt, target_duration)
        
        # Normalize to -30 LUFS
        audio_tensor = self._normalize(audio_tensor)
        
        # Create output path
        output_path = self.output_dir / job_id / "music" / "background.wav"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        self._save_audio(audio_tensor, str(output_path))
        
        return str(output_path)
    
    def _generate_audio(self, prompt: str, duration_s: float):
        """
        Generate audio using the diffusion model.
        
        Args:
            prompt: Text prompt for generation
            duration_s: Target duration in seconds
            
        Returns:
            Audio tensor
        """
        # Call the pipeline
        output = self.pipeline(
            prompt=prompt,
            duration=duration_s
        )
        
        # Extract audio tensor
        audio_tensor = output.audio_data
        
        # Convert to numpy array if needed
        if hasattr(audio_tensor, 'numpy'):
            audio_tensor = audio_tensor.numpy()
        
        return audio_tensor
    
    def _normalize(self, audio: np.ndarray, target_lufs: float = -30.0) -> np.ndarray:
        """
        Normalize audio to target LUFS.
        
        Args:
            audio: Input audio array
            target_lufs: Target loudness in LUFS (default -30)
            
        Returns:
            Normalized audio array
        """
        # Calculate current loudness (simplified)
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 1e-10:
            return audio
        
        # Normalize to -30 LUFS (rough approximation)
        target_rms = 10 ** (target_lufs / 20)
        scale = target_rms / rms
        return audio * scale
    
    def _save_audio(self, audio: np.ndarray, path: str, sample_rate: int = 44100):
        """
        Save audio to WAV file.
        
        Args:
            audio: Audio array (normalized)
            path: Output path
            sample_rate: Sample rate in Hz
        """
        import wave
        
        # Convert to 16-bit PCM
        audio_int = (audio * 32767).astype(np.int16)
        
        # Create WAV file
        with wave.open(path, 'w') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_int.tobytes())


def generate_music(
    total_duration_s: float,
    prompt: str,
    job_id: str,
    genre: str = "",
    mood: str = "",
    per_chapter: bool = False
) -> str:
    """
    Convenience function to generate music.
    
    Args:
        total_duration_s: Target duration in seconds
        prompt: Text prompt for music generation
        job_id: Job identifier
        genre: Genre tag (optional)
        mood: Mood tag (optional)
        per_chapter: Generate per-chapter music (optional)
        
    Returns:
        Path to generated music file
    """
    generator = MusicGenerator()
    return generator.generate(
        total_duration_s=total_duration_s,
        prompt=prompt,
        job_id=job_id,
        genre=genre,
        mood=mood,
        per_chapter=per_chapter
    )
