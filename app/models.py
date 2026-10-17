"""Pydantic models for the run config (dashboard -> API) and the persisted run state."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(UTC)


class Status(StrEnum):
    """Status vocabulary shared by stages and runs."""

    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    AWAITING_REVIEW = "awaiting_review"
    SKIPPED = "skipped"
    ERROR = "error"


class StageChoice(BaseModel):
    stage: str
    provider: str


class RunConfig(BaseModel):
    """What the dashboard sends to ``POST /runs``. Stages not listed are skipped."""

    channel: str = "AI School 369"
    title: str = Field(min_length=1, max_length=120)
    idea: str = Field(min_length=1, max_length=20_000, description="Rough text or transcript")
    stages: list[StageChoice] = Field(default_factory=list)


class StageState(BaseModel):
    stage: str
    provider: str | None = None
    status: Status = Status.IDLE
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class ReviewNote(BaseModel):
    at: datetime = Field(default_factory=utcnow)
    notes: str
    redo_from: str


class ReviewState(BaseModel):
    checklist: dict[str, bool] = Field(default_factory=dict)
    approved_at: datetime | None = None
    history: list[ReviewNote] = Field(default_factory=list)


class RunState(BaseModel):
    id: str
    status: Status = Status.IDLE
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    config: RunConfig
    stages: list[StageState]
    review: ReviewState = Field(default_factory=ReviewState)
    error: str | None = None

    def stage(self, name: str) -> StageState:
        return next(s for s in self.stages if s.stage == name)
