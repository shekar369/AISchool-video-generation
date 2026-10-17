"""Orchestrator: plans a run from its config, executes stages in order, pauses at review.

Every function that schedules work (create_run, approve, request_changes, redo) sets the run to
``running`` under ``store.lock`` before returning, so a second click gets a conflict instead of
starting a parallel worker. The caller then hands the run id to ``execute``.
"""

import logging

from app.config import Settings
from app.models import ReviewNote, RunConfig, RunState, StageState, Status, utcnow
from app.stages import CHECKLIST, REQUIRED_STAGES, STAGE_ORDER, STAGES, StageContext
from app.state import RunStore

log = logging.getLogger(__name__)


class InvalidConfigError(ValueError):
    pass


class InvalidTransitionError(RuntimeError):
    """The requested action doesn't fit the run's current status."""


class ChecklistIncompleteError(ValueError):
    def __init__(self, missing: list[str]) -> None:
        super().__init__(f"Unticked checklist items: {missing}")
        self.missing = missing


def plan_stages(config: RunConfig) -> list[StageState]:
    """One StageState per pipeline stage, in canonical order; unselected stages are skipped."""
    chosen: dict[str, str] = {}
    for choice in config.stages:
        if choice.stage not in STAGE_ORDER:
            raise InvalidConfigError(f"Unknown stage {choice.stage!r}; stages: {list(STAGE_ORDER)}")
        if choice.stage in chosen:
            raise InvalidConfigError(f"Stage {choice.stage!r} listed more than once")
        if (choice.stage, choice.provider) not in STAGES:
            raise InvalidConfigError(f"No provider {choice.provider!r} for stage {choice.stage!r}")
        chosen[choice.stage] = choice.provider

    plan = []
    for stage in STAGE_ORDER:
        provider = chosen.get(stage, REQUIRED_STAGES.get(stage))
        status = Status.IDLE if provider else Status.SKIPPED
        plan.append(StageState(stage=stage, provider=provider, status=status))
    return plan


def create_run(store: RunStore, config: RunConfig) -> RunState:
    state = store.create(config, plan_stages(config))
    state.status = Status.RUNNING
    store.save(state)
    return state


def execute(store: RunStore, settings: Settings, run_id: str) -> RunState:
    """Run every idle/errored stage in order. Stops at the review gate or on the first error."""
    state = store.load(run_id)
    state.status, state.error = Status.RUNNING, None
    store.save(state)
    ctx = StageContext(run_id, store.run_dir(run_id), state.config, settings)

    for rec in state.stages:
        if rec.status in (Status.DONE, Status.SKIPPED):
            continue

        rec.status, rec.started_at, rec.finished_at, rec.error = (
            Status.RUNNING,
            utcnow(),
            None,
            None,
        )
        store.save(state)
        log.info("run=%s stage=%s provider=%s", run_id, rec.stage, rec.provider)
        try:
            STAGES[(rec.stage, rec.provider)](ctx)
        except Exception as exc:
            log.exception("run=%s stage=%s failed", run_id, rec.stage)
            rec.status, rec.error, rec.finished_at = (
                Status.ERROR,
                f"{type(exc).__name__}: {exc}",
                utcnow(),
            )
            state.status, state.error = Status.ERROR, f"Stage {rec.stage!r} failed"
            store.save(state)
            return state
        rec.finished_at = utcnow()

        if rec.stage == "review" and state.review.approved_at is None:
            rec.status = state.status = Status.AWAITING_REVIEW
            store.save(state)
            log.info("run=%s awaiting review", run_id)
            return state

        rec.status = Status.DONE
        store.save(state)

    state.status = Status.DONE
    store.save(state)
    log.info("run=%s done", run_id)
    return state


def approve(store: RunStore, run_id: str, checklist: dict[str, bool]) -> RunState:
    with store.lock:
        state = store.load(run_id)
        if state.status != Status.AWAITING_REVIEW:
            raise InvalidTransitionError(f"Run is {state.status}, not awaiting_review")
        unknown = set(checklist) - set(CHECKLIST)
        if unknown:
            raise InvalidConfigError(f"Unknown checklist items: {sorted(unknown)}")
        missing = [key for key in CHECKLIST if not checklist.get(key)]
        if missing:
            raise ChecklistIncompleteError(missing)

        state.review.checklist, state.review.approved_at = dict(checklist), utcnow()
        state.stage("review").status = Status.DONE
        state.status = Status.RUNNING
        store.save(state)
        return state


def request_changes(store: RunStore, run_id: str, notes: str, redo_from: str) -> RunState:
    with store.lock:
        state = store.load(run_id)
        if state.status != Status.AWAITING_REVIEW:
            raise InvalidTransitionError(f"Run is {state.status}, not awaiting_review")
        if redo_from in STAGE_ORDER and STAGE_ORDER.index(redo_from) >= STAGE_ORDER.index("review"):
            raise InvalidConfigError("Changes must redo a stage before review")
        state.review.history.append(ReviewNote(notes=notes, redo_from=redo_from))
        store.save(state)
        return _reset_from(store, state, redo_from)


def redo(store: RunStore, run_id: str, from_stage: str) -> RunState:
    with store.lock:
        state = store.load(run_id)
        if state.status == Status.RUNNING:
            raise InvalidTransitionError("Run is already running")
        return _reset_from(store, state, from_stage)


def _reset_from(store: RunStore, state: RunState, from_stage: str) -> RunState:
    """Reset ``from_stage`` and every later non-skipped stage to idle. Caller holds the lock."""
    if from_stage not in STAGE_ORDER:
        raise InvalidConfigError(f"Unknown stage {from_stage!r}")
    if state.stage(from_stage).status == Status.SKIPPED:
        raise InvalidConfigError(f"Stage {from_stage!r} is not enabled for this run")

    start = STAGE_ORDER.index(from_stage)
    for rec in state.stages[start:]:
        if rec.status != Status.SKIPPED:
            rec.status, rec.started_at, rec.finished_at, rec.error = Status.IDLE, None, None, None
    # Anything upstream of the gate changed, so a previous approval no longer applies.
    if start <= STAGE_ORDER.index("review"):
        state.review.checklist, state.review.approved_at = {}, None
    state.status, state.error = Status.RUNNING, None
    store.save(state)
    return state
