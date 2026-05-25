"""Pipeline orchestrator for longform lore videos."""

import asyncio
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from pydantic import BaseModel

if TYPE_CHECKING:
    from pipeline.tts import NarrationGenerator


class JobStatus(str, Enum):
    """Job status values."""

    QUEUED = "queued"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_NARRATION = "generating_narration"
    GENERATING_MUSIC = "generating_music"
    GENERATING_IMAGES = "generating_images"
    GENERATING_SUBTITLES = "generating_subtitles"
    ASSEMBLING_VIDEO = "assembling_video"
    COMPLETE = "complete"
    FAILED = "failed"


class JobState(BaseModel):
    """Job state model."""

    job_id: str
    status: JobStatus
    stage: Optional[str] = None
    progress_pct: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    output_path: str
    chapter_count: int = 1


class PipelineOrchestrator:
    """Orchestrates the multi-stage video generation pipeline."""

    STAGE_WEIGHTS = {
        "script": 10,
        "narration": 15,
        "music": 10,
        "images": 30,
        "subtitles": 10,
        "assembly": 25,
    }

    STAGES = [
        ("script", JobStatus.GENERATING_SCRIPT),
        ("narration", JobStatus.GENERATING_NARRATION),
        ("music", JobStatus.GENERATING_MUSIC),
        ("images", JobStatus.GENERATING_IMAGES),
        ("subtitles", JobStatus.GENERATING_SUBTITLES),
        ("assembly", JobStatus.ASSEMBLING_VIDEO),
    ]

    def __init__(
        self,
        output_dir: str = "output",
        tts_preset: str = "standard",
        tts_voice_path: Optional[str] = None,
        tts_generator: Optional[Union["NarrationGenerator", object]] = None,
    ):
        """Initialize orchestrator.

        Args:
            output_dir: Base directory for job outputs.
            tts_preset: TTS quality preset (draft, standard, hq).
            tts_voice_path: Path to speaker WAV for voice cloning (HQ preset).
            tts_generator: Optional TTS generator instance for dependency injection.
        """
        self.output_dir = Path(output_dir)
        self._jobs: Dict[str, asyncio.Task] = {}
        self._queue: List[str] = []
        self._cancellation_flags: Dict[str, asyncio.Event] = {}
        if tts_generator is not None:
            self._tts_generator = tts_generator
        else:
            from pipeline.tts import NarrationGenerator
            self._tts_generator = NarrationGenerator(
                preset=tts_preset,
                voice_path=tts_voice_path,
                output_dir=str(self.output_dir),
            )

    async def submit_job(self, job_id: str, chapter_count: int = 1) -> JobState:
        """Submit a new job to the queue."""
        job_path = self.output_dir / job_id
        job_path.mkdir(parents=True, exist_ok=True)
        state = JobState(
            job_id=job_id, status=JobStatus.QUEUED, stage=None,
            progress_pct=0, started_at=datetime.utcnow(),
            completed_at=None, error=None, output_path=str(job_path),
            chapter_count=chapter_count,
        )
        await self._save_state(job_id, state)
        self._queue.append(job_id)
        return state

    async def run_job(self, job_id: str) -> JobState:
        """Run a single job synchronously (for testing)."""
        state_path = self.output_dir / job_id / "state.json"
        if not state_path.exists():
            raise ValueError(f"Job {job_id} not found")
        with open(state_path) as f:
            data = json.load(f)
        state = JobState(**data)
        if state.status == JobStatus.COMPLETE:
            return state
        try:
            for stage_name, stage_status in self.STAGES:
                if self._is_stage_completed(job_id, stage_name):
                    continue
                if job_id in self._cancellation_flags:
                    return state.model_copy(update={
                        "status": JobStatus.FAILED, "error": "Job cancelled",
                        "completed_at": datetime.utcnow(),
                    })
                state = await self._run_stage(job_id, stage_name, stage_status, state)
                if state.status == JobStatus.FAILED:
                    return state
            state = state.model_copy(update={
                "status": JobStatus.COMPLETE, "completed_at": datetime.utcnow(),
                "progress_pct": 100,
            })
            await self._save_state(job_id, state)
        except Exception as e:
            state = state.model_copy(update={
                "status": JobStatus.FAILED, "error": str(e),
                "completed_at": datetime.utcnow(),
            })
            await self._save_state(job_id, state)
        return state

    async def _run_stage(self, job_id, stage_name, stage_status, state):
        stage_path = self.output_dir / job_id / stage_name
        state = state.model_copy(update={"status": stage_status, "stage": stage_name})
        await self._save_state(job_id, state)
        if stage_name == "narration":
            state = await self._run_narration_stage(job_id, state, stage_path)
        else:
            await asyncio.sleep(0.1)
        stage_path.mkdir(parents=True, exist_ok=True)
        (stage_path / "done").touch()
        completed_weight = sum(
            self.STAGE_WEIGHTS.get(s, 0)
            for s, _ in self.STAGES
            if self._is_stage_completed(job_id, s)
        )
        state = state.model_copy(update={"progress_pct": completed_weight})
        await self._save_state(job_id, state)
        return state

    async def _run_narration_stage(self, job_id, state, stage_path):
        script_path = self.output_dir / job_id / "script.txt"
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        with open(script_path) as f:
            script_text = f.read()
        chapters = [p.strip() for p in script_text.split("\n\n") if p.strip()]
        if not chapters:
            chapters = ["Placeholder narration text."]
        durations = []
        for i, chapter_text in enumerate(chapters, start=1):
            stage_path / f"chapter_{i}.wav"
            duration = await self._tts_generator.generate_chapter(
                text=chapter_text, chapter_num=i, job_id=job_id,
                output_dir=str(self.output_dir),
            )
            durations.append(duration)
        state = state.model_copy(update={
            "narration_durations": durations,
            "narration_chapter_count": len(chapters),
        })
        return state

    def _is_stage_completed(self, job_id, stage_name):
        stage_path = self.output_dir / job_id / stage_name / "done"
        return stage_path.exists()

    async def _save_state(self, job_id, state):
        job_path = self.output_dir / job_id
        job_path.mkdir(parents=True, exist_ok=True)
        state_path = job_path / "state.json"
        data = state.model_dump()
        if data.get("started_at"):
            data["started_at"] = data["started_at"].isoformat()
        if data.get("completed_at"):
            data["completed_at"] = data["completed_at"].isoformat()
        with open(state_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_state(self, job_id):
        state_path = self.output_dir / job_id / "state.json"
        if not state_path.exists():
            return None
        with open(state_path) as f:
            data = json.load(f)
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return JobState(**data)
