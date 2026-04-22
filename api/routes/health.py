"""Health check route."""

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from api.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


class ModelStatus(BaseModel):
    available: bool
    path: str | None = None
    reason: str | None = None


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    # Check disk space
    stat = Path("/").statvfs() if hasattr(Path("/"), "statvfs") else None
    disk_free_gb = stat.f_bavail * stat.f_frsize / (1024**3) if stat else 0.0

    # Check model availability (placeholder logic)
    models = {
        "llama": ModelStatus(available=False, reason="model not downloaded"),
        "stable_diffusion": ModelStatus(available=False, reason="model not downloaded"),
        "tts": ModelStatus(available=False, reason="model not downloaded"),
        "whisper": ModelStatus(available=False, reason="model not downloaded"),
        "stable_audio": ModelStatus(available=False, reason="model not downloaded"),
    }

    return HealthResponse(
        status="ok",
        models={k: {"available": v.available, "path": v.path, "reason": v.reason} for k, v in models.items()},
        disk_free_gb=disk_free_gb,
        queue_depth=0,
    )
