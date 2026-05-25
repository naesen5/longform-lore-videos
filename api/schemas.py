"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Genre(str, Enum):
    """Valid genre options."""

    HISTORICAL = "historical"
    SCIFI = "scifi"
    FANTASY = "fantasy"
    NARRATIVE = "narrative"
    EDUCATIONAL = "educational"


class Quality(str, Enum):
    """Valid quality options."""

    LOW = "low"
    STANDARD = "standard"
    HIGH = "high"
    HD = "hd"


class JobSubmission(BaseModel):
    """Request body for POST /jobs."""

    topic: str = Field(..., max_length=500, description="Topic for the video")
    genre: Genre = Field(..., description="Genre category")
    chapters: int = Field(..., ge=1, le=20, description="Number of chapters (1-20)")
    quality: Quality = Field(default=Quality.STANDARD, description="Output quality")
    voice_clone_url: Optional[str] = Field(default=None, description="Optional voice clone URL")


class JobResponse(BaseModel):
    """Response body for job submission."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    estimated_duration_s: int = Field(..., ge=1, description="Estimated duration in seconds")


class JobStatusResponse(BaseModel):
    """Response body for GET /jobs/{job_id}."""

    job_id: str
    status: str
    stage: Optional[str] = None
    progress_pct: int = Field(ge=0, le=100)
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    output_path: str
    chapter_count: int


class JobEvent(BaseModel):
    """Server-Sent Event for job progress."""

    event: str = "progress"
    data: str


class JobListResponse(BaseModel):
    """Response body for GET /jobs (list)."""

    jobs: List[JobStatusResponse]
    total: int
    limit: int
    offset: int


class HealthModelStatus(BaseModel):
    """Health check status for a single model."""

    available: bool
    path: Optional[str] = None
    reason: Optional[str] = None


class HealthResponse(BaseModel):
    """Response body for GET /health."""

    status: str = "ok"
    models: Dict[str, HealthModelStatus]
    disk_free_gb: float
    queue_depth: int


class ErrorResponse(BaseModel):
    """Error response body."""

    error: str
    message: str
    code: int
