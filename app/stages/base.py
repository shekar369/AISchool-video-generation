"""The provider registry ``STAGES[(stage, provider)]`` and the context passed to every stage."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import Settings
from app.models import RunConfig

STAGE_ORDER: tuple[str, ...] = (
    "capture",
    "script",
    "fact_check",
    "slides",
    "voice",
    "render",
    "metadata",
    "review",
    "upload",
)

# Stages that always run, with the provider used when the config doesn't name one.
REQUIRED_STAGES: dict[str, str] = {"capture": "text", "review": "checklist"}


class StageInputError(RuntimeError):
    """A stage could not find an artifact an earlier stage should have written."""


@dataclass(frozen=True)
class StageContext:
    run_id: str
    run_dir: Path
    config: RunConfig
    settings: Settings

    def path(self, *parts: str) -> Path:
        return self.run_dir.joinpath(*parts)

    def read_json(self, name: str) -> Any:
        path = self.path(name)
        if not path.is_file():
            raise StageInputError(f"{name} not found; enable the stage that produces it")
        return json.loads(path.read_text(encoding="utf-8"))

    def write_json(self, name: str, data: Any) -> Path:
        path = self.path(name)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


StageFn = Callable[[StageContext], None]

STAGES: dict[tuple[str, str], StageFn] = {}


def register(stage: str, provider: str) -> Callable[[StageFn], StageFn]:
    if stage not in STAGE_ORDER:
        raise ValueError(f"Unknown stage {stage!r}")

    def decorator(fn: StageFn) -> StageFn:
        if (stage, provider) in STAGES:
            raise ValueError(f"Provider {provider!r} already registered for {stage!r}")
        STAGES[(stage, provider)] = fn
        return fn

    return decorator


def providers(stage: str) -> list[str]:
    return sorted(p for s, p in STAGES if s == stage)
