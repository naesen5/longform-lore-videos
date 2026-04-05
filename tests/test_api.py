"""Tests for FastAPI routes."""

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


class TestHealth:
    """Health check endpoint tests."""

    def test_health_check(self):
        """GET /health returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "models" in data
        assert "disk_free_gb" in data
        assert "queue_depth" in data


class TestJobs:
    """Job endpoint tests."""

    def test_submit_job(self):
        """POST /jobs creates a new job."""
        job = {
            "topic": "Test topic",
            "genre": "historical",
            "chapters": 3,
            "quality": "standard",
        }
        response = client.post("/jobs", json=job)
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert "estimated_duration_s" in data

    def test_get_job_status_not_found(self):
        """GET /jobs/{id} returns 404 for unknown job."""
        response = client.get("/jobs/nonexistent")
        assert response.status_code == 404

    def test_list_jobs_empty(self):
        """GET /jobs returns empty list when no jobs exist."""
        # Clean up any leftover output
        output_dir = Path("output")
        if output_dir.exists():
            shutil.rmtree(output_dir)

        response = client.get("/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert data["jobs"] == []
