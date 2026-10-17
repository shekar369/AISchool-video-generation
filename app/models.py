"""Pydantic models shared by the API, the pipeline and the run store."""

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=200, examples=["Photosynthesis"])
    audience: str = Field(default="high school students", max_length=100)
    duration_minutes: float = Field(default=3.0, gt=0, le=30)
    providers: dict[str, str] = Field(
        default_factory=dict,
        description="Per-stage provider overrides, e.g. {'voice': 'mock'}.",
    )


class StageRecord(BaseModel):
    name: str
    provider: str
    status: StageStatus = StageStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)


class RunState(BaseModel):
    id: str
    status: RunStatus = RunStatus.QUEUED
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    request: RunRequest
    stages: list[StageRecord]
    output_path: Path | None = None
    error: str | None = None
