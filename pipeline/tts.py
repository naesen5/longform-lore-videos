"""TTS narration pipeline: per-chapter audio generation using Coqui TTS."""
import os
import warnings
from pathlib import Path
from typing import Optional

import numpy as np
from TTS.tts.utils.synthesis import synthesis
from TTS.tts.utils import find_module
from TTS.configs.xts_config import XtsConfig
from pyloudnorm import loudnorm

warnings.filterwarnings("ignore", category=UserWarning)


class NarrationGenerator:
    """Generate speech audio from narration text using Coqui TTS models."""

    PRESETS = {
        "draft": {"model": "tts_models/en/ljspeech/glow-tts", "sample_rate": 22050},
        "standard": {"model": "tts_models/multilingual/multi-dataset/xtts_v2", "sample_rate": 24000},
        "hq": {"model": "tts_models/multilingual/multi-dataset/xtts_v2", "sample_rate": 24000},
    }

    def __init__(
        self,
        preset: str = "standard",
        voice_path: Optional[str] = None,
        output_dir: str = "output",
    ):
        if preset not in self.PRESETS:
            raise ValueError(f"Invalid preset: {preset}. Must be one of {list(self.PRESETS.keys())}")

        self.preset = preset
        self.voice_path = voice_path
        self.output_dir = Path(output_dir)
        self._model = None

        config = self.PRESETS[preset]
        self._model_id = config["model"]
        self._sample_rate = config["sample_rate"]

    def _init_model(self):
        if self._model is None:
            self._model = self._load_model(self._model_id)
        return self._model

    def _load_model(self, model_id: str):
        """Load TTS model by name."""
        # Coqui TTS uses a module finder pattern
        from TTS.tts.utils import find_module
        module_path = find_module(model_id)
        model = find_module(module_path)
        return model

    def generate_chapter(
        self,
        text: str,
        chapter_num: int,
        job_id: str,
        output_dir: Optional[str] = None,
    ) -> float:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if len(text) > 5000:
            raise ValueError("Text too long (max 5000 chars)")

        out_dir = Path(output_dir or self.output_dir) / job_id / "narration"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = out_dir / f"chapter_{chapter_num}.wav"

        model = self._init_model()
        config = model.CONFIG

        # Generate audio using TTS synthesis function
        if self.preset == "hq" and self.voice_path:
            # Voice cloning mode - pass speaker_wav as style_wav
            audio = synthesis(
                model=model,
                text=text,
                CONFIG=config,
                use_cuda=False,
                style_wav=self.voice_path,
                language_id=0,
            )
        else:
            # Standard mode
            audio = synthesis(
                model=model,
                text=text,
                CONFIG=config,
                use_cuda=False,
                language_id=0,
            )

        # Normalize to -18 LUFS
        normalized = loudnorm(audio, target=-18.0)
        normalized = normalized.astype(np.float32)

        # Save WAV with correct sample rate
        import soundfile as sf
        sf.write(str(output_path), normalized, self._sample_rate, subtype="PCM_16")

        # Measure actual duration
        duration = len(normalized) / self._sample_rate

        return round(duration, 3)

    def generate_batch(
        self,
        chapters: list[str],
        job_id: str,
        output_dir: Optional[str] = None,
    ) -> list[float]:
        durations = []
        for i, text in enumerate(chapters, start=1):
            duration = self.generate_chapter(
                text=text,
                chapter_num=i,
                job_id=job_id,
                output_dir=output_dir,
            )
            durations.append(duration)
            print(f"Chapter {i}: {duration:.3f}s")

        return durations
