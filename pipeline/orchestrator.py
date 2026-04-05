"""Pipeline orchestrator for async job queue and state machine."""

import asyncio
import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel


class JobStatus(str, Enum):
    """Job status enum."""

    QUEUED = "queued"
    GENERATING_SCRIPT = "generating_script"
    GENERATING_NARRATION = "generating_narration"
    GENERATING_MUSIC = "generating_music"
    GENERATING_IMAGES = "generating_images"
    GENERATING_SUBTITLES = "generating_subtitles"
    ASSEMBLING_VIDEO = "assembling_video"
    COMPLETE = "complete"
    FAILED = "failed"


class Stage(str, Enum):
    """Pipeline stage enum."""

    SCRIPT = "script"
    NARRATION = "narration"
    MUSIC = "music"
    IMAGES = "images"
    SUBTITLES = "subtitles"
    ASSEMBLY = "assembly"


# Stage weights for progress calculation
STAGE_WEIGHTS = {
    Stage.SCRIPT: 10,
    Stage.NARRATION: 15,
    Stage.MUSIC: 10,
    Stage.IMAGES: 30,
    Stage.SUBTITLES: 10,
    Stage.ASSEMBLY: 25,
}


class JobState(BaseModel):
    """Job state model."""

    job_id: str
    status: JobStatus
    stage: Optional[Stage] = None
    progress_pct: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    output_path: Optional[str] = None


class PipelineOrchestrator:
    """Pipeline orchestrator for async job queue and state machine."""

    def __init__(self, output_dir: str = "output", max_concurrent: int = 1):
        self.output_dir = Path(output_dir)
        self.max_concurrent = max_concurrent
        self.active_jobs: dict[str, JobState] = {}
        self.job_queue: list[str] = []
        self.cancellation_flags: dict[str, asyncio.Event] = {}
        self.running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._queue_lock = asyncio.Lock()

    def create_job(self, subject: str) -> JobState:
        """Create a new job and return its state."""
        job_id = str(uuid4())
        job = JobState(
            job_id=job_id,
            status=JobStatus.QUEUED,
            started_at=datetime.now(),
        )
        self.active_jobs[job_id] = job
        self._save_state(job)
        return job

    def _save_state(self, job: JobState) -> None:
        """Save job state to file."""
        state_path = self.output_dir / job.job_id / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump(job.model_dump(), f, indent=2, default=str)

    def _load_state(self, job_id: str) -> Optional[JobState]:
        """Load job state from file."""
        state_path = self.output_dir / job_id / "state.json"
        if not state_path.exists():
            return None
        with open(state_path) as f:
            data = json.load(f)
            return JobState(**data)

    def _get_completed_stages(self, job: JobState) -> set[Stage]:
        """Determine which stages have completed based on output files."""
        job_dir = self.output_dir / job.job_id
        completed = set()

        # Check each stage's output
        if (job_dir / "script.txt").exists():
            completed.add(Stage.SCRIPT)

        narration_dir = job_dir / "narration"
        if narration_dir.exists() and any(narration_dir.glob("*.mp3")):
            completed.add(Stage.NARRATION)

        if (job_dir / "music.mp3").exists():
            completed.add(Stage.MUSIC)

        images_dir = job_dir / "images"
        if images_dir.exists() and any(images_dir.glob("*.png")):
            completed.add(Stage.IMAGES)

        subtitles_dir = job_dir / "subtitles"
        if subtitles_dir.exists() and any(subtitles_dir.glob("*.srt")):
            completed.add(Stage.SUBTITLES)

        if (job_dir / "output.mp4").exists():
            completed.add(Stage.ASSEMBLY)

        return completed

    def _calculate_progress(self, job: JobState) -> float:
        """Calculate progress percentage based on completed stages."""
        completed = self._get_completed_stages(job)
        total_weight = sum(STAGE_WEIGHTS.values())
        completed_weight = sum(STAGE_WEIGHTS[s] for s in completed)
        return (completed_weight / total_weight) * 100

    async def _run_stage(
        self, job: JobState, stage: Stage, job_dir: Path
    ) -> tuple[JobState, Optional[str]]:
        """Run a single pipeline stage."""
        # Check for cancellation
        if job.job_id in self.cancellation_flags:
            return job, "Job cancelled"

        # Determine output path for this stage
        stage_outputs = {
            Stage.SCRIPT: job_dir / "script.txt",
            Stage.NARRATION: job_dir / "narration",
            Stage.MUSIC: job_dir / "music.mp3",
            Stage.IMAGES: job_dir / "images",
            Stage.SUBTITLES: job_dir / "subtitles",
            Stage.ASSEMBLY: job_dir / "output.mp4",
        }

        output_path = stage_outputs.get(stage)
        if output_path and output_path.exists():
            # Stage already completed (checkpoint)
            return job, None

        # Simulate stage execution (placeholder for actual implementation)
        # In real implementation, this would call the specific pipeline stages
        await asyncio.sleep(0.1)  # Simulate work

        # Mark stage as complete
        job.stage = stage
        job.progress_pct = self._calculate_progress(job)
        job.status = JobStatus.GENERATING_NARRATION if stage == Stage.SCRIPT else job.status
        self._save_state(job)

        return job, None

    async def _run_job(self, job: JobState) -> JobState:
        """Run the full pipeline for a job."""
        job_dir = self.output_dir / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        job.started_at = datetime.now()
        self._save_state(job)

        stages = [
            Stage.SCRIPT,
            Stage.NARRATION,
            Stage.MUSIC,
            Stage.IMAGES,
            Stage.SUBTITLES,
            Stage.ASSEMBLY,
        ]

        for stage in stages:
            # Check for cancellation before each stage
            if job.job_id in self.cancellation_flags:
                job.status = JobStatus.FAILED
                job.error = "Job cancelled"
                job.completed_at = datetime.now()
                self._save_state(job)
                return job

            job.status = JobStatus.GENERATING_NARRATION
            job, error = await self._run_stage(job, stage, job_dir)

            if error:
                job.status = JobStatus.FAILED
                job.error = error
                job.completed_at = datetime.now()
                self._save_state(job)
                return job

        job.status = JobStatus.COMPLETE
        job.output_path = str(job_dir / "output.mp4")
        job.completed_at = datetime.now()
        self._save_state(job)
        return job

    async def _worker(self) -> None:
        """Worker loop to process jobs from queue."""
        while self.running:
            async with self._queue_lock:
                if self.job_queue:
                    job_id = self.job_queue.pop(0)
                    job = self.active_jobs.get(job_id)
                    if job:
                        await self._run_job(job)
                else:
                    await asyncio.sleep(0.1)

    def start(self) -> None:
        """Start the orchestrator worker."""
        self.running = True
        self._worker_task = asyncio.create_task(self._worker())

    def stop(self) -> None:
        """Stop the orchestrator worker."""
        self.running = False
        if self._worker_task:
            self._worker_task.cancel()

    def submit_job(self, subject: str) -> JobState:
        """Submit a new job to the queue."""
        job = self.create_job(subject)
        self.job_queue.append(job.job_id)
        return job

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id in self.active_jobs:
            self.cancellation_flags[job_id] = asyncio.Event()
            return True
        return False

    def get_job(self, job_id: str) -> Optional[JobState]:
        """Get job state."""
        return self.active_jobs.get(job_id)

    def get_job_events(self, job_id: str):
        """Generator for SSE events for a job."""
        # Placeholder for SSE implementation
        pass
