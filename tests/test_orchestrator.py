"""Tests for PipelineOrchestrator."""

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from longform_lore_videos.pipeline.orchestrator import JobState, JobStatus, PipelineOrchestrator


class TestJobState:
    def test_create_job_state(self):
        state = JobState(
            job_id="test123", status=JobStatus.QUEUED,
            started_at=datetime.utcnow(), output_path="/tmp/test123",
        )
        assert state.job_id == "test123"
        assert state.status == JobStatus.QUEUED

    def test_update_status(self):
        state = JobState(
            job_id="test123", status=JobStatus.QUEUED,
            started_at=datetime.utcnow(), output_path="/tmp/test123",
        )
        updated = state.model_copy(update={"status": JobStatus.GENERATING_SCRIPT})
        assert updated.status == JobStatus.GENERATING_SCRIPT


class TestPipelineOrchestrator:
    def test_init(self):
        orch = PipelineOrchestrator()
        assert orch.output_dir.name == "output"

    def test_stage_weights(self):
        orch = PipelineOrchestrator()
        total = sum(orch.STAGE_WEIGHTS.values())
        assert total == 100

    def test_stage_order(self):
        orch = PipelineOrchestrator()
        expected = ["script", "narration", "music", "images", "subtitles", "assembly"]
        actual = [name for name, _ in orch.STAGES]
        assert actual == expected

    @pytest.mark.asyncio
    async def test_submit_job(self):
        orch = PipelineOrchestrator()
        state = await orch.submit_job("submit_job_1", chapter_count=3)
        assert state.job_id == "submit_job_1"
        assert state.status == JobStatus.QUEUED
        assert state.chapter_count == 3
        state_path = orch.output_dir / "submit_job_1" / "state.json"
        assert state_path.exists()

    @pytest.mark.asyncio
    async def test_run_job_complete(self):
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
            assert state.progress_pct == 100

    @pytest.mark.asyncio
    async def test_run_job_complete_with_tts_mock(self):
        orch = PipelineOrchestrator()
        await orch.submit_job("run_job_1", chapter_count=1)
        script_path = orch.output_dir / "run_job_1" / "script.txt"
        script_path.write_text("Test narration text.\n\nAnother paragraph.")
        mock_gen = AsyncMock()
        mock_gen.generate_chapter.return_value = 5.2
        orch._tts_generator = mock_gen
        state = await orch.run_job("run_job_1")
        assert state.status == JobStatus.COMPLETE
        assert state.progress_pct == 100

    @pytest.mark.asyncio
    async def test_run_job_skips_completed_stages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = PipelineOrchestrator(output_dir=tmpdir)
            await orch.submit_job("test123", chapter_count=1)
            async def mock_run_stage(job_id, stage_name, stage_status,
                                    state):
                stage_path = Path(tmpdir) / job_id / stage_name
                stage_path.mkdir(parents=True, exist_ok=True)
                (stage_path / "done").touch()
                return state
            with patch.object(orch, "_run_stage", mock_run_stage):
                state = await orch.run_job("test123")
            assert state.status == JobStatus.COMPLETE
            state = await orch.run_job("test123")
            assert state.status == JobStatus.COMPLETE
            assert state.progress_pct == 100

    @pytest.mark.asyncio
    async def test_run_job_skips_completed_stages_with_tts(self):
        orch = PipelineOrchestrator()
        await orch.submit_job("run_job_2", chapter_count=1)
        script_path = orch.output_dir / "run_job_2" / "script.txt"
        script_path.write_text("Test narration text.\n\nAnother paragraph.")
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
        orch = PipelineOrchestrator()
        await orch.submit_job("cancel_job_1", chapter_count=1)
        script_path = orch.output_dir / "cancel_job_1" / "script.txt"
        script_path.write_text("Test narration text.\n\nAnother paragraph.")
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
        with tempfile.TemporaryDirectory() as tmpdir:
            orch = PipelineOrchestrator(output_dir=tmpdir)
            await orch.submit_job("persist_job_1")
            script_path = Path(tmpdir) / "persist_job_1" / "script.txt"
            script_path.write_text("Test narration text.\n\nAnother paragraph.")
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
    async def test_run_job_not_found(self):
        orch = PipelineOrchestrator()
        with pytest.raises(ValueError, match="not found"):
            await orch.run_job("nonexistent")

    @pytest.mark.asyncio
    async def test_run_job_missing_script_fails(self):
        orch = PipelineOrchestrator()
        await orch.submit_job("missing_script_1", chapter_count=1)
        state = await orch.run_job("missing_script_1")
        assert state.status == JobStatus.FAILED
        assert "Script not found" in state.error

    @pytest.mark.asyncio
    async def test_get_state(self):
        orch = PipelineOrchestrator()
        await orch.submit_job("test123", chapter_count=2)
        state = orch.get_state("test123")
        assert state is not None
        assert state.job_id == "test123"
        assert state.status == JobStatus.QUEUED
        assert state.chapter_count == 2

    @pytest.mark.asyncio
    async def test_get_state_not_found(self):
        orch = PipelineOrchestrator()
        state = orch.get_state("nonexistent")
        assert state is None

    @pytest.mark.asyncio
    async def test_narration_chapter_count(self):
        orch = PipelineOrchestrator()
        await orch.submit_job("chapter_count_1", chapter_count=1)
        script_path = orch.output_dir / "chapter_count_1" / "script.txt"
        script_path.write_text("First paragraph.\n\nSecond paragraph.\n\nThird paragraph.")
        mock_gen = AsyncMock()
        mock_gen.generate_chapter.return_value = 5.2
        orch._tts_generator = mock_gen
        state = await orch.run_job("chapter_count_1")
        assert state.status == JobStatus.COMPLETE
        assert mock_gen.generate_chapter.call_count == 3
