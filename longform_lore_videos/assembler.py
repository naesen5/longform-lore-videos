"""Video assembler for longform lore videos."""

import os
from pathlib import Path
from typing import Dict, List, Optional

from moviepy import AudioFileClip, ColorClip, CompositeVideoClip, VideoFileClip, concatenate_videoclips
from moviepy.video.tools import subtitles


class VideoAssembler:
    """Assembles chapter clips into a final MP4 video."""

    QUALITY_PRESETS = {
        "draft": {"resolution": (1280, 720), "crf": 28, "preset": "fast"},
        "standard": {"resolution": (1920, 1080), "crf": 23, "preset": "medium"},
        "hq": {"resolution": (1920, 1080), "crf": 18, "preset": "slow"},
    }

    def __init__(self, quality: str = "standard"):
        """Initialize assembler with quality preset.

        Args:
            quality: Quality preset - "draft", "standard", or "hq".
        """
        if quality not in self.QUALITY_PRESETS:
            raise ValueError(f"Invalid quality: {quality}. Must be one of {list(self.QUALITY_PRESETS.keys())}")
        self.quality = quality

    def _get_quality_params(self) -> Dict[str, int]:
        """Get quality preset parameters."""
        return self.QUALITY_PRESETS[self.quality]

    def assemble(self, job_dir: str, output_path: Optional[str] = None) -> Optional[str]:
        """Assemble all chapter clips into final MP4.

        Args:
            job_dir: Path to job directory containing chapters/
            output_path: Output path (default: job_dir/output/final.mp4)

        Returns:
            Path to final MP4 or None if no chapters found.
        """
        job_path = Path(job_dir)
        chapters_dir = job_path / "chapters"

        if not chapters_dir.exists():
            return None

        chapter_dirs = sorted(chapters_dir.glob("chapter_*"))
        if not chapter_dirs:
            return None

        # Build per-chapter clips
        chapter_clips = []
        for chapter_dir in chapter_dirs:
            clip = self._build_chapter_clip(chapter_dir)
            if clip:
                chapter_clips.append(clip)

        if not chapter_clips:
            return None

        # Assemble global video
        final = self._assemble_global(chapter_clips)

        # Write output
        output = Path(output_path) if output_path else job_path / "output" / "final.mp4"
        output.parent.mkdir(parents=True, exist_ok=True)

        quality = self._get_quality_params()
        final.write_videofile(
            str(output),
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset=quality["preset"],
            ffmpeg_params=[f"-crf", str(quality["crf"])],
        )

        final.close()
        return str(output)

    def _build_chapter_clip(self, chapter_dir: Path) -> Optional[CompositeVideoClip]:
        """Build a single chapter clip with title card, images, narration, subtitles.

        Args:
            chapter_dir: Directory containing chapter assets.

        Returns:
            CompositeVideoClip or None if no assets found.
        """
        images = sorted(chapter_dir.glob("image_*.png"))
        narration = chapter_dir / "narration.mp3"
        subtitles_file = chapter_dir / "subtitles.srt"

        if not images:
            return None

        # Load narration audio
        audio_clip = None
        if narration.exists():
            audio_clip = AudioFileClip(str(narration))

        # Calculate duration per image
        duration = audio_clip.duration if audio_clip else 5.0
        per_image_duration = duration / len(images)

        # Build image sequence with Ken Burns effect
        image_clips = []
        for i, img_path in enumerate(images):
            clip = VideoFileClip(str(img_path))
            clip = clip.set_duration(per_image_duration)

            # Apply Ken Burns effect (alternate zoom-in/pan)
            zoom_start = 1.0
            zoom_end = 1.08 if i % 2 == 0 else 1.06
            clip = clip.resize(lambda t: zoom_start + (zoom_end - zoom_start) * (t / per_image_duration))

            image_clips.append(clip)

        # Combine images
        if image_clips:
            # Concatenate images
            video_clip = concatenate_videoclips(image_clips, method="compose")
        else:
            return None

        # Overlay subtitles
        if subtitles_file.exists():
            video_clip = subtitles.SubtitlesClip(
                str(subtitles_file),
                [(video_clip.w // 20, video_clip.h - video_clip.h // 10)],
            ).set_clip(video_clip)

        # Mix audio
        if audio_clip:
            video_clip = video_clip.set_audio(audio_clip)

        return video_clip

    def _assemble_global(self, chapter_clips: List[CompositeVideoClip]) -> CompositeVideoClip:
        """Concatenate chapter clips with crossfade transitions.

        Args:
            chapter_clips: List of chapter clips.

        Returns:
            Final CompositeVideoClip with intro, chapters, and outro.
        """
        # Crossfade transition clip (1 second black)
        transition = ColorClip((640, 360), duration=1.0, fps=24)

        # Concatenate with crossfade
        clips_with_transitions = []
        for i, clip in enumerate(chapter_clips):
            if i > 0:
                clips_with_transitions.append(transition)
            clips_with_transitions.append(clip)

        # Concatenate all
        final = concatenate_videoclips(clips_with_transitions, method="compose")

        # Add intro (5 second title card)
        intro = ColorClip((640, 360), duration=5.0, fps=24)
        intro = intro.with_audio(AudioFileClip(__file__))  # dummy audio
        final = concatenate_videoclips([intro, final], method="compose")

        # Add outro (5 second black fade)
        outro = ColorClip((640, 360), duration=5.0, fps=24)
        final = concatenate_videoclips([final, outro], method="compose")

        return final
