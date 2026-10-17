"""FastAPI service: the dashboard creates runs, polls their state, and drives the review gate."""

import logging
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from app import __version__
from app.config import Settings, get_settings
from app.models import RunConfig, RunState
from app.pipeline import (
    ChecklistIncompleteError,
    InvalidConfigError,
    InvalidTransitionError,
    approve,
    create_run,
    execute,
    redo,
    request_changes,
)
from app.stages import CHECKLIST, REQUIRED_STAGES, STAGE_ORDER, providers
from app.state import RunNotFoundError, RunStore

log = logging.getLogger(__name__)


class StageInfo(BaseModel):
    stage: str
    providers: list[str]
    required: bool


class ApproveBody(BaseModel):
    checklist: dict[str, bool]


class ChangesBody(BaseModel):
    notes: str = Field(min_length=1, max_length=5_000)
    redo_from: str = "script"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=settings.log_level)
    store = RunStore(settings.runs_dir)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if recovered := store.recover_interrupted():
            log.warning("Marked interrupted runs as error: %s", recovered)
        yield

    app = FastAPI(title="AI School 369 Video Pipeline", version=__version__, lifespan=lifespan)
    app.state.settings, app.state.store = settings, store

    def guarded(action, *args) -> RunState:
        """Run a state transition, mapping domain errors to HTTP status codes."""
        try:
            return action(store, *args)
        except RunNotFoundError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found") from None
        except InvalidTransitionError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
        except ChecklistIncompleteError as exc:
            raise HTTPException(422, {"message": str(exc), "missing": exc.missing}) from None
        except InvalidConfigError as exc:
            raise HTTPException(422, str(exc)) from None

    def schedule(tasks: BackgroundTasks, state: RunState) -> RunState:
        tasks.add_task(execute, store, settings, state.id)
        return state

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/stages")
    def list_stages() -> list[StageInfo]:
        return [
            StageInfo(stage=s, providers=providers(s), required=s in REQUIRED_STAGES)
            for s in STAGE_ORDER
        ]

    @app.get("/review/checklist")
    def review_checklist() -> dict[str, str]:
        return CHECKLIST

    @app.post("/runs", status_code=status.HTTP_202_ACCEPTED)
    def start_run(config: RunConfig, tasks: BackgroundTasks) -> RunState:
        return schedule(tasks, guarded(create_run, config))

    @app.get("/runs")
    def list_runs() -> list[RunState]:
        return store.all()

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> RunState:
        return guarded(RunStore.load, run_id)

    @app.post("/runs/{run_id}/approve", status_code=status.HTTP_202_ACCEPTED)
    def approve_run(run_id: str, body: ApproveBody, tasks: BackgroundTasks) -> RunState:
        return schedule(tasks, guarded(approve, run_id, body.checklist))

    @app.post("/runs/{run_id}/changes", status_code=status.HTTP_202_ACCEPTED)
    def changes(run_id: str, body: ChangesBody, tasks: BackgroundTasks) -> RunState:
        return schedule(tasks, guarded(request_changes, run_id, body.notes, body.redo_from))

    @app.post("/runs/{run_id}/redo", status_code=status.HTTP_202_ACCEPTED)
    def redo_run(
        run_id: str, tasks: BackgroundTasks, from_stage: str = Query(alias="from")
    ) -> RunState:
        return schedule(tasks, guarded(redo, run_id, from_stage))

    return app


app = create_app()
