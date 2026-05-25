"""Tests for PipelineOrchestrator."""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

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
        state = await orch.submit_job("submit_job_1", chapter_count=3)
        assert state.job_id == "submit_job_1"
        assert state.status == JobStatus.QUEUED
        assert state.chapter_count == 3

        state_path = orch.output_dir / "submit_job_1" / "state.json"
        assert state_path.exists()

    @pytest.mark.asyncio
    async def test_run_job_complete(self):
        """Run a job to completion."""
        orch = PipelineOrchestrator()
        await orch.submit_job("run_job_1", chapter_count=1)
        # Create script.txt for narration stage
        script_path = orch.output_dir / "run_job_1" / "script.txt"
        script_path.write_text("Test narration text for the job.\n\nAnother paragraph here.")
        # Mock the TTS generator to avoid torchaudio ABI issues
        mock_gen = AsyncMock()
        mock_gen.generate_chapter.return_value = 5.2
        orch._tts_generator = mock_gen
        state = await orch.run_job("run_job_1")
        assert state.status == JobStatus.COMPLETE
        assert state.progress_pct == 100

    @pytest.mark.asyncio
    async def test_run_job_skips_completed_stages(self):
        """Restarting job skips completed stages."""
        orch = PipelineOrchestrator()
        await orch.submit_job("run_job_2", chapter_count=1)
        # Create script.txt for narration stage
        script_path = orch.output_dir / "run_job_2" / "script.txt"
        script_path.write_text("Test narration text for the job.\n\nAnother paragraph here.")
        # Mock the TTS generator
        mock_gen = AsyncMock()
        mock_gen.generate_chapter.return_value = 5.2
        orch._tts_generator = mock_gen
        state = await orch.run_job("run_job_2")
        assert state.status == JobStatus.COMPLETE

        state = await orch.run_job("run_job_2")
        assert state.status == JobStatus.COMPLETE
        assert state.progress_pct == 100

    @pytest.mark.asyncio
    async def test_cancel_job(self):
        """Cancel a running job."""
        orch = PipelineOrchestrator()
        await orch.submit_job("cancel_job_1", chapter_count=1)
        # Create script.txt for narration stage
        script_path = orch.output_dir / "cancel_job_1" / "script.txt"
        script_path.write_text("Test narration text for the job.\n\nAnother paragraph here.")
        # Mock the TTS generator
        mock_gen = AsyncMock()
        mock_gen.generate_chapter.return_value = 5.2
        orch._tts_generator = mock_gen

        state = await orch.run_job("cancel_job_1")
        assert state.status == JobStatus.COMPLETE

        orch._cancellation_flags["cancel_job_1"] = asyncio.Event()
        state = await orch.run_job("cancel_job_1")
        assert state.status == JobStatus.COMPLETE

    @pytest.mark.asyncio
    async def test_job_state_persistence(self):
        """Job state is persisted to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = PipelineOrchestrator(output_dir=tmpdir)
            await orch.submit_job("persist_job_1")
            # Create script.txt for narration stage
            script_path = Path(tmpdir) / "persist_job_1" / "script.txt"
            script_path.write_text("Test narration text for the job.\n\nAnother paragraph here.")
            # Mock the TTS generator
            mock_gen = AsyncMock()
            mock_gen.generate_chapter.return_value = 5.2
            orch._tts_generator = mock_gen
            await orch.run_job("persist_job_1")

            state_path = Path(tmpdir) / "persist_job_1" / "state.json"
            assert state_path.exists()

            with open(state_path) as f:
                data = json.load(f)
            assert data["status"] == "complete"

    @pytest.mark.asyncio
    async def test_run_job_missing_script_fails(self):
        """Job fails if script.txt is missing."""
        orch = PipelineOrchestrator()
        await orch.submit_job("missing_script_1", chapter_count=1)
        # Don't create script.txt
        state = await orch.run_job("missing_script_1")
        assert state.status == JobStatus.FAILED
        assert "Script not found" in state.error

    @pytest.mark.asyncio
    async def test_narration_chapter_count(self):
        """Verify chapter count matches script paragraphs."""
        orch = PipelineOrchestrator()
        await orch.submit_job("chapter_count_1", chapter_count=1)
        script_path = orch.output_dir / "chapter_count_1" / "script.txt"
        script_path.write_text("First paragraph.\n\nSecond paragraph.\n\nThird paragraph.")
        # Mock the TTS generator to track chapter calls
        mock_gen = AsyncMock()
        mock_gen.generate_chapter.return_value = 5.2
        orch._tts_generator = mock_gen
        state = await orch.run_job("chapter_count_1")
        assert state.status == JobStatus.COMPLETE
        # Verify TTS was called once per chapter (3 paragraphs = 3 chapters)
        assert mock_gen.generate_chapter.call_count == 3
