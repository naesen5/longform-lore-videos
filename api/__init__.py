"""API package for longform-lore-videos."""

from fastapi import FastAPI

from api.routes import health, jobs

app = FastAPI(
    title="Longform Lore Videos API",
    description="REST API for video generation pipeline orchestration",
    version="0.1.0",
)

app.include_router(jobs.router)
app.include_router(health.router)
