"""Tests for PipelineOrchestrator."""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from longform_lore_videos.pipeline.orchestrator import JobState, JobStatus, PipelineOrchestrator


class TestJobState:
    """Test JobState model."""

    def test_create_job_state(self):
        """Create a new job state."""
        state = JobState(
            job_id="test123",
            status=JobStatus.QUEUED,
            started_at=datetime.utcnow(),
            output_path="/tmp/test123",
        )
        assert state.job_id == "test123"
        assert state.status == JobStatus.QUEUED
        assert state.progress_pct == 0

    def test_update_status(self):
        """Update job status."""
        state = JobState(
            job_id="test123",
            status=JobStatus.QUEUED,
            started_at=datetime.utcnow(),
            output_path="/tmp/test123",
        )
        updated = state.model_copy(update={"status": JobStatus.GENERATING_SCRIPT})
        assert updated.status == JobStatus.GENERATING_SCRIPT


class TestPipelineOrchestrator:
    """Test PipelineOrchestrator."""

    def test_init(self):
        """Initialize orchestrator."""
        orch = PipelineOrchestrator()
        assert orch.output_dir.name == "output"

    def test_stage_weights(self):
        """Verify stage weights sum to 100%."""
        orch = PipelineOrchestrator()
        total = sum(orch.STAGE_WEIGHTS.values())
        assert total == 100

    def test_stage_order(self):
        """Verify stages are in correct order."""
        orch = PipelineOrchestrator()
        expected = ["script", "narration", "music", "images", "subtitles", "assembly"]
        actual = [name for name, _ in orch.STAGES]
        assert actual == expected

    @pytest.mark.asyncio
    async def test_submit_job(self):
        """Submit a new job."""
        orch = PipelineOrchestrator()
        state = await orch.submit_job("test123", chapter_count=3)
        assert state.job_id == "test123"
        assert state.status == JobStatus.QUEUED
        assert state.chapter_count == 3

        state_path = orch.output_dir / "test123" / "state.json"
        assert state_path.exists()

    @pytest.mark.asyncio
    async def test_run_job_complete(self):
        """Run a job to completion (mocked stages)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = PipelineOrchestrator(output_dir=tmpdir)
            await orch.submit_job("test123", chapter_count=1)

            # Mock _run_stage to simulate successful stage execution
            async def mock_run_stage(job_id, stage_name, stage_status, state):
                stage_path = Path(tmpdir) / job_id / stage_name
                stage_path.mkdir(parents=True, exist_ok=True)
                (stage_path / "done").touch()
                return state

            with patch.object(orch, "_run_stage", mock_run_stage):
                state = await orch.run_job("test123")

            assert state.status == JobStatus.COMPLETE
            assert state.progress_pct == 100

    @pytest.mark.asyncio
    async def test_run_job_skips_completed_stages(self):
        """Restarting job skips completed stages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = PipelineOrchestrator(output_dir=tmpdir)
            await orch.submit_job("test123", chapter_count=1)

            async def mock_run_stage(job_id, stage_name, stage_status, state):
                stage_path = Path(tmpdir) / job_id / stage_name
                stage_path.mkdir(parents=True, exist_ok=True)
                (stage_path / "done").touch()
                return state

            with patch.object(orch, "_run_stage", mock_run_stage):
                state = await orch.run_job("test123")

            assert state.status == JobStatus.COMPLETE

            # Second run should skip all stages (already done)
            state = await orch.run_job("test123")
            assert state.status == JobStatus.COMPLETE
            assert state.progress_pct == 100

    @pytest.mark.asyncio
    async def test_cancel_job(self):
        """Cancel a running job."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = PipelineOrchestrator(output_dir=tmpdir)
            await orch.submit_job("test123", chapter_count=1)

            # Set cancellation flag before running
            orch._cancellation_flags["test123"] = asyncio.Event()

            async def mock_run_stage(job_id, stage_name, stage_status, state):
                stage_path = Path(tmpdir) / job_id / stage_name
                stage_path.mkdir(parents=True, exist_ok=True)
                (stage_path / "done").touch()
                return state

            with patch.object(orch, "_run_stage", mock_run_stage):
                state = await orch.run_job("test123")

            # With cancellation flag set, job should fail
            assert state.status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_job_state_persistence(self):
        """Job state is persisted to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = PipelineOrchestrator(output_dir=tmpdir)
            await orch.submit_job("test123")

            async def mock_run_stage(job_id, stage_name, stage_status, state):
                stage_path = Path(tmpdir) / job_id / stage_name
                stage_path.mkdir(parents=True, exist_ok=True)
                (stage_path / "done").touch()
                return state

            with patch.object(orch, "_run_stage", mock_run_stage):
                await orch.run_job("test123")

            state_path = Path(tmpdir) / "test123" / "state.json"
            assert state_path.exists()

            with open(state_path) as f:
                data = json.load(f)
            assert data["status"] == "complete"

    @pytest.mark.asyncio
    async def test_run_job_not_found(self):
        """Run a non-existent job raises ValueError."""
        orch = PipelineOrchestrator()
        with pytest.raises(ValueError, match="not found"):
            await orch.run_job("nonexistent")

    @pytest.mark.asyncio
    async def test_get_state(self):
        """Get job state from disk."""
        orch = PipelineOrchestrator()
        await orch.submit_job("test123", chapter_count=2)
        state = orch.get_state("test123")
        assert state is not None
        assert state.job_id == "test123"
        assert state.status == JobStatus.QUEUED
        assert state.chapter_count == 2

    @pytest.mark.asyncio
    async def test_get_state_not_found(self):
        """Get state for non-existent job returns None."""
        orch = PipelineOrchestrator()
        state = orch.get_state("nonexistent")
        assert state is None
