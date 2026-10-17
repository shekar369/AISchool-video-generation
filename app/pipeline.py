"""Orchestrator: runs stages in order, persisting state after every transition."""

import logging
from typing import Any

from app.config import Settings
from app.models import RunRequest, RunState, RunStatus, StageStatus, utcnow
from app.stages import STAGES, StageContext, UnknownProviderError
from app.state import RunStore

log = logging.getLogger(__name__)


def resolve_providers(settings: Settings, overrides: dict[str, str]) -> dict[str, str]:
    """Merge request overrides over configured defaults and validate every name."""
    unknown_stages = set(overrides) - set(STAGES)
    if unknown_stages:
        raise UnknownProviderError(f"Unknown stage(s): {sorted(unknown_stages)}")
    providers = {stage: overrides.get(stage, settings.default_provider(stage)) for stage in STAGES}
    for stage, name in providers.items():
        if name not in STAGES[stage]:
            raise UnknownProviderError(
                f"Unknown {stage} provider {name!r}; available: {STAGES[stage].names()}"
            )
    return providers


def create_run(store: RunStore, settings: Settings, request: RunRequest) -> RunState:
    return store.create(request, resolve_providers(settings, request.providers))


def execute(store: RunStore, settings: Settings, run_id: str) -> RunState:
    """Run (or resume) a pipeline. Stages already completed are skipped, not repeated."""
    state = store.load(run_id)
    state.status, state.error = RunStatus.RUNNING, None
    store.save(state)

    artifacts: dict[str, dict[str, Any]] = {}
    for record in state.stages:
        if record.status == StageStatus.COMPLETED:
            artifacts[record.name] = record.output
            continue

        ctx = StageContext(
            run_id=state.id,
            run_dir=store.run_dir(state.id),
            outputs_dir=settings.outputs_dir,
            request=state.request,
            settings=settings,
            artifacts=artifacts,
        )
        record.status, record.started_at, record.error = StageStatus.RUNNING, utcnow(), None
        store.save(state)
        log.info("run=%s stage=%s provider=%s started", state.id, record.name, record.provider)

        try:
            record.output = STAGES[record.name].get(record.provider).run(ctx)
        except Exception as exc:
            log.exception("run=%s stage=%s failed", state.id, record.name)
            record.status, record.error = StageStatus.FAILED, f"{type(exc).__name__}: {exc}"
            record.finished_at = utcnow()
            state.status, state.error = RunStatus.FAILED, f"Stage {record.name!r} failed"
            store.save(state)
            return state

        record.status, record.finished_at = StageStatus.COMPLETED, utcnow()
        artifacts[record.name] = record.output
        store.save(state)

    state.status = RunStatus.COMPLETED
    state.output_path = artifacts.get("assemble", {}).get("output_path")
    store.save(state)
    log.info("run=%s completed output=%s", state.id, state.output_path)
    return state
