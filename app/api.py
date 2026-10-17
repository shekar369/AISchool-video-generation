"""FastAPI service: create runs, track their progress, inspect available providers."""

import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, status
from pydantic import BaseModel

from app import __version__
from app.config import Settings, get_settings
from app.models import RunRequest, RunState, RunStatus
from app.pipeline import create_run, execute
from app.stages import STAGES, UnknownProviderError
from app.state import RunNotFoundError, RunStore


class StageInfo(BaseModel):
    stage: str
    providers: list[str]
    default: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(title="AI School 369 Video Pipeline", version=__version__)
    app.state.settings = settings
    app.state.store = RunStore(settings.runs_dir)

    def store(request: Request) -> RunStore:
        return request.app.state.store

    def load_or_404(request: Request, run_id: str) -> RunState:
        try:
            return store(request).load(run_id)
        except RunNotFoundError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Run {run_id!r} not found") from None

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/stages")
    def list_stages() -> list[StageInfo]:
        return [
            StageInfo(stage=name, providers=reg.names(), default=settings.default_provider(name))
            for name, reg in STAGES.items()
        ]

    @app.post("/runs", status_code=status.HTTP_202_ACCEPTED)
    def start_run(body: RunRequest, request: Request, tasks: BackgroundTasks) -> RunState:
        try:
            state = create_run(store(request), settings, body)
        except UnknownProviderError as exc:
            raise HTTPException(422, str(exc)) from None
        tasks.add_task(execute, store(request), settings, state.id)
        return state

    @app.get("/runs")
    def list_runs(request: Request) -> list[RunState]:
        return store(request).list()

    @app.get("/runs/{run_id}")
    def get_run(run_id: str, request: Request) -> RunState:
        return load_or_404(request, run_id)

    @app.post("/runs/{run_id}/resume", status_code=status.HTTP_202_ACCEPTED)
    def resume_run(run_id: str, request: Request, tasks: BackgroundTasks) -> RunState:
        state = load_or_404(request, run_id)
        if state.status != RunStatus.FAILED:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Run is {state.status}, not failed")
        tasks.add_task(execute, store(request), settings, run_id)
        return state

    return app


app = create_app()
