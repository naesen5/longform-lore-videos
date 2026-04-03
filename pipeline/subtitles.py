"""Subtitle generation pipeline using whisper.cpp."""
import json
import subprocess
from pathlib import Path
from typing import Optional


class SubtitleGenerator:
    """Generate SRT subtitles from TTS narration using whisper.cpp."""
    
    # Whisper.cpp model sizes
    MODEL_SIZES = {
        "draft": "base.en",
        "standard": "small.en",
        "hq": "medium.en",
    }
    
    def __init__(
        self,
        whisper_binary: str = "whisper-cpp",
        model_size: str = "standard",
        output_dir: str = "output",
    ):
        """
        Initialize the subtitle generator.
        
        Args:
            whisper_binary: Path to whisper-cpp binary
            model_size: Model size (draft/standard/hq)
            output_dir: Base directory for output files
        """
        self.whisper_binary = whisper_binary
        self.model_size = model_size
        self.output_dir = Path(output_dir)
    
    @property
    def model_id(self) -> str:
        """Get model ID for current size preset."""
        return self.MODEL_SIZES.get(self.model_size, "small.en")
    
    def generate(self, job_id: str, chapter_timings: list[dict]) -> list[str]:
        """
        Generate subtitles for a job.
        
        Args:
            job_id: Unique job identifier
            chapter_timings: List of chapter data with audio_path, start_s, end_s
            
        Returns:
            List of output SRT file paths
        """
        output_dir = self.output_dir / job_id / "subtitles"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        srt_files = []
        total_offset_s = 0
        
        for i, chapter in enumerate(chapter_timings):
            audio_path = chapter.get("audio_path")
            if not audio_path:
                continue
                
            srt_path = self._generate_chapter_srt(
                audio_path=audio_path,
                output_dir=output_dir,
                chapter_index=i,
                global_offset_s=total_offset_s,
            )
            srt_files.append(str(srt_path))
            
            # Accumulate offset for next chapter
            if "duration_s" in chapter:
                total_offset_s += chapter["duration_s"]
        
        return srt_files
    
    def _generate_chapter_srt(
        self,
        audio_path: str,
        output_dir: Path,
        chapter_index: int,
        global_offset_s: float = 0,
    ) -> Path:
        """
        Generate SRT for a single chapter.
        
        Args:
            audio_path: Path to audio file
            output_dir: Output directory
            chapter_index: Chapter number (0-based)
            global_offset_s: Time offset for this chapter
            
        Returns:
            Path to generated SRT file
        """
        srt_path = output_dir / f"chapter_{chapter_index}.srt"
        
        # Run whisper.cpp with JSON output
        result = subprocess.run(
            [
                self.whisper_binary,
                "-m", self.model_id,
                "-f", audio_path,
                "--output-json",
                "--word-thold", "0.5",
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"whisper.cpp failed: {result.stderr}")
        
        # Parse JSON output
        whisper_output = json.loads(result.stdout)
        words = whisper_output.get("words", [])
        
        # Generate SRT content
        srt_lines = []
        for i, word_data in enumerate(words):
            start_s = word_data.get("start", 0) + global_offset_s
            end_s = word_data.get("end", start_s) + global_offset_s
            word = word_data.get("text", "")
            
            srt_lines.append(f"{i+1}")
            srt_lines.append(f"{self._to_srt_time(start_s)} --> {self._to_srt_time(end_s)}")
            srt_lines.append(word)
            srt_lines.append("")
        
        # Write SRT file
        srt_path.write_text("\n".join(srt_lines))
        
        return srt_path
    
    def _to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        ms = int((seconds % 1) * 1000)
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
