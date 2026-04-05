"""Routes for job submission, status, and download."""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse

from api.schemas import (
    ErrorResponse,
    JobEvent,
    JobListResponse,
    JobResponse,
    JobStatusResponse,
    JobSubmission,
)
from longform_lore_videos.pipeline.orchestrator import (
    JobStatus,
    PipelineOrchestrator,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Global orchestrator instance
orchestrator = PipelineOrchestrator(output_dir="output")


def generate_job_id() -> str:
    """Generate a unique job ID."""
    import uuid

    return f"job-{uuid.uuid4().hex[:12]}"


@router.post(
    "",
    response_model=JobResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)
async def submit_job(job: JobSubmission) -> JobResponse:
    """Submit a new video generation job."""
    job_id = generate_job_id()

    # Calculate estimated duration based on chapters and quality
    base_duration = 30  # seconds per chapter
    quality_multiplier = {"low": 0.5, "standard": 1.0, "high": 1.5, "hd": 2.0}
    estimated_duration = int(job.chapters * base_duration * quality_multiplier[job.quality.value])

    state = await orchestrator.submit_job(job_id, chapter_count=job.chapters)

    return JobResponse(
        job_id=job_id,
        status=state.status.value,
        estimated_duration_s=estimated_duration,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Get full job state."""
    state = orchestrator.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="not_found",
                message=f"Job {job_id} not found",
                code=404,
            ).model_dump(),
        )

    return JobStatusResponse(
        job_id=state.job_id,
        status=state.status.value,
        stage=state.stage,
        progress_pct=state.progress_pct,
        started_at=state.started_at,
        completed_at=state.completed_at,
        error=state.error,
        output_path=state.output_path,
        chapter_count=state.chapter_count,
    )


@router.get(
    "/{job_id}/events",
    response_class=Response,
    responses={
        404: {"model": ErrorResponse},
    },
)
async def stream_job_events(job_id: str):
    """Server-Sent Events stream for job progress."""
    state = orchestrator.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="not_found",
                message=f"Job {job_id} not found",
                code=404,
            ).model_dump(),
        )

    async def event_generator():
        """Generate SSE events for job progress."""
        prev_progress = -1
        while True:
            current_state = orchestrator.get_state(job_id)
            if current_state is None:
                break

            if current_state.status == JobStatus.FAILED:
                yield f"data: {JobEvent(data=current_state.error or 'Job failed').model_dump_json()}\n\n"
                break

            if current_state.progress_pct != prev_progress:
                progress_msg = f"Progress: {current_state.progress_pct}%"
                yield f"data: {JobEvent(data=progress_msg).model_dump_json()}\n\n"
                prev_progress = current_state.progress_pct

            if current_state.status == JobStatus.COMPLETE:
                yield f"data: {JobEvent(data='Job complete').model_dump_json()}\n\n"
                break

            await asyncio.sleep(1)

    return Response(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/{job_id}/download",
    responses={
        404: {"model": ErrorResponse},
        200: {
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            }
        },
    },
)
async def download_job(job_id: str):
    """Download the final MP4 file."""
    state = orchestrator.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="not_found",
                message=f"Job {job_id} not found",
                code=404,
            ).model_dump(),
        )

    output_path = Path(state.output_path) / "final.mp4"
    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="not_ready",
                message=f"Job {job_id} not yet completed or output file missing",
                code=404,
            ).model_dump(),
        )

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=f"longform-lore-{job_id}.mp4",
    )


@router.get(
    "/{job_id}/preview",
    responses={
        404: {"model": ErrorResponse},
    },
)
async def get_job_preview(job_id: str):
    """Download a lower-resolution preview MP4."""
    state = orchestrator.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="not_found",
                message=f"Job {job_id} not found",
                code=404,
            ).model_dump(),
        )

    preview_path = Path(state.output_path) / "preview.mp4"
    if not preview_path.exists():
        # Generate preview from final.mp4 if available
        final_path = Path(state.output_path) / "final.mp4"
        if final_path.exists():
            subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    str(final_path),
                    "-vf",
                    "scale=640:360",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "28",
                    "-y",
                    str(preview_path),
                ],
                check=True,
                capture_output=True,
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="not_ready",
                    message=f"Job {job_id} not yet completed or output file missing",
                    code=404,
                ).model_dump(),
            )

    return FileResponse(
        preview_path,
        media_type="video/mp4",
        filename=f"longform-lore-{job_id}-preview.mp4",
    )


@router.get(
    "",
    response_model=JobListResponse,
)
async def list_jobs(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JobListResponse:
    """List all jobs (paginated, newest first)."""
    output_dir = Path("output")
    if not output_dir.exists():
        return JobListResponse(jobs=[], total=0, limit=limit, offset=offset)

    job_dirs = sorted(output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)

    jobs = []
    for job_dir in job_dirs[offset : offset + limit]:
        state = orchestrator.get_state(job_dir.name)
        if state is None:
            continue

        if status is not None and state.status.value != status:
            continue

        jobs.append(
            JobStatusResponse(
                job_id=state.job_id,
                status=state.status.value,
                stage=state.stage,
                progress_pct=state.progress_pct,
                started_at=state.started_at,
                completed_at=state.completed_at,
                error=state.error,
                output_path=state.output_path,
                chapter_count=state.chapter_count,
            )
        )

    total = len(list(output_dir.iterdir()))

    return JobListResponse(jobs=jobs, total=total, limit=limit, offset=offset)


@router.delete(
    "/{job_id}",
    responses={
        204: {},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
    },
)
async def cancel_or_delete_job(job_id: str) -> Response:
    """Cancel a running job or delete a completed one."""
    state = orchestrator.get_state(job_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error="not_found",
                message=f"Job {job_id} not found",
                code=404,
            ).model_dump(),
        )

    if state.status == JobStatus.COMPLETE:
        import shutil

        output_path = Path(state.output_path)
        if output_path.exists():
            shutil.rmtree(output_path)
        return Response(status_code=204)

    if state.status in (JobStatus.QUEUED, JobStatus.GENERATING_SCRIPT):
        orchestrator._cancellation_flags[job_id] = asyncio.Event()
        return Response(status_code=204)

    raise HTTPException(
        status_code=409,
        detail=ErrorResponse(
            error="conflict",
            message=f"Cannot cancel job {job_id} in status {state.status.value}",
            code=409,
        ).model_dump(),
    )
