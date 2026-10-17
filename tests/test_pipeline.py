import json

import pytest

from app.models import RunConfig, StageChoice, Status
from app.pipeline import (
    ChecklistIncompleteError,
    InvalidConfigError,
    InvalidTransitionError,
    approve,
    create_run,
    execute,
    plan_stages,
    redo,
    request_changes,
)
from app.stages import CHECKLIST, STAGE_ORDER, STAGES, providers
from app.stages.slides import HEIGHT, WIDTH

ALL_TICKED = dict.fromkeys(CHECKLIST, True)
FULL_FLOW = [
    {"stage": s, "provider": "stub"}
    for s in ("script", "fact_check", "slides", "voice", "render", "metadata", "upload")
]


def make_config(stages=FULL_FLOW, **kw) -> RunConfig:
    return RunConfig(
        title="What is a vector database?",
        idea="Embeddings turn text into numbers. Vector DBs search them fast. Use them for RAG.",
        stages=[StageChoice(**s) for s in stages],
        **kw,
    )


def run_to_gate(store, settings, config=None):
    state = create_run(store, config or make_config())
    return execute(store, settings, state.id)


def statuses(state):
    return {s.stage: s.status for s in state.stages}


def test_registry_covers_every_stage():
    assert STAGE_ORDER == (
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
    assert all(providers(stage) for stage in STAGE_ORDER)
    assert ("capture", "text") in STAGES and ("review", "checklist") in STAGES


def test_plan_skips_unselected_and_keeps_required_stages():
    plan = {s.stage: s for s in plan_stages(make_config([{"stage": "script", "provider": "stub"}]))}
    assert plan["capture"].provider == "text" and plan["capture"].status == Status.IDLE
    assert plan["review"].provider == "checklist"
    assert plan["voice"].status == Status.SKIPPED and plan["voice"].provider is None


@pytest.mark.parametrize(
    "stages",
    [
        [{"stage": "storyboard", "provider": "stub"}],
        [{"stage": "voice", "provider": "nope"}],
        [{"stage": "voice", "provider": "stub"}, {"stage": "voice", "provider": "stub"}],
    ],
)
def test_invalid_config_is_rejected(stages):
    with pytest.raises(InvalidConfigError):
        plan_stages(make_config(stages))


def test_run_pauses_at_review_gate(store, settings):
    state = run_to_gate(store, settings)
    assert state.status == Status.AWAITING_REVIEW
    s = statuses(state)
    assert s["review"] == Status.AWAITING_REVIEW and s["upload"] == Status.IDLE
    assert all(s[x] == Status.DONE for x in STAGE_ORDER[: STAGE_ORDER.index("review")])

    run_dir = store.run_dir(state.id)
    script = json.loads((run_dir / "script.json").read_text())
    pngs = sorted((run_dir / "slides").glob("*.png"))
    assert len(pngs) == len(script["slides"]) == len(list((run_dir / "audio").glob("*.wav")))
    assert pngs[0].read_bytes()[16:24] == WIDTH.to_bytes(4, "big") + HEIGHT.to_bytes(4, "big")
    metadata = json.loads((run_dir / "metadata.json").read_text())
    assert metadata["chapters"][0].startswith("0:00 ")


def test_approve_requires_every_checklist_item(store, settings):
    state = run_to_gate(store, settings)
    with pytest.raises(ChecklistIncompleteError) as exc:
        approve(store, state.id, {**ALL_TICKED, "facts": False})
    assert exc.value.missing == ["facts"]
    with pytest.raises(InvalidConfigError):
        approve(store, state.id, {**ALL_TICKED, "vibes": True})

    approve(store, state.id, ALL_TICKED)
    state = execute(store, settings, state.id)
    assert state.status == Status.DONE
    assert statuses(state)["upload"] == Status.DONE
    assert json.loads((store.run_dir(state.id) / "upload.json").read_text())["privacy"] == "private"


def test_approve_only_at_gate(store, settings):
    state = run_to_gate(store, settings)
    approve(store, state.id, ALL_TICKED)
    with pytest.raises(InvalidTransitionError):
        approve(store, state.id, ALL_TICKED)


def test_redo_resets_chosen_and_later_stages_only(store, settings):
    state = run_to_gate(store, settings)
    approve(store, state.id, ALL_TICKED)
    state = execute(store, settings, state.id)
    script_finished = state.stage("script").finished_at

    state = redo(store, state.id, "voice")
    s = statuses(state)
    assert s["slides"] == Status.DONE
    assert all(s[x] == Status.IDLE for x in ("voice", "render", "metadata", "review", "upload"))
    assert state.review.approved_at is None  # approval voided by upstream change

    state = execute(store, settings, state.id)
    assert state.status == Status.AWAITING_REVIEW
    assert state.stage("script").finished_at == script_finished


def test_request_changes_records_notes_and_reruns(store, settings):
    state = run_to_gate(store, settings)
    state = request_changes(store, state.id, "Hook is too slow", "script")
    assert state.review.history[0].notes == "Hook is too slow"
    assert statuses(state)["script"] == Status.IDLE
    assert execute(store, settings, state.id).status == Status.AWAITING_REVIEW


def test_redo_rejects_skipped_or_unknown_stage(store, settings):
    state = run_to_gate(store, settings, make_config([{"stage": "script", "provider": "stub"}]))
    with pytest.raises(InvalidConfigError):
        redo(store, state.id, "voice")
    with pytest.raises(InvalidConfigError):
        redo(store, state.id, "storyboard")


def test_error_stops_run_and_redo_recovers(store, settings, monkeypatch):
    def boom(ctx):
        raise RuntimeError("tts outage")

    monkeypatch.setitem(STAGES, ("voice", "stub"), boom)
    state = run_to_gate(store, settings)
    assert state.status == Status.ERROR
    assert state.stage("voice").error == "RuntimeError: tts outage"
    assert statuses(state)["render"] == Status.IDLE

    monkeypatch.undo()
    redo(store, state.id, "voice")
    assert execute(store, settings, state.id).status == Status.AWAITING_REVIEW


def test_missing_input_gives_actionable_error(store, settings):
    # slides needs script.json, but script is not enabled
    state = run_to_gate(store, settings, make_config([{"stage": "slides", "provider": "stub"}]))
    assert state.status == Status.ERROR
    assert "script.json not found" in state.stage("slides").error


def test_interrupted_runs_are_recovered(store, settings):
    state = create_run(store, make_config())  # left "running", as if the worker died
    assert store.recover_interrupted() == [state.id]
    assert store.load(state.id).status == Status.ERROR


def test_changes_must_target_a_stage_before_review(store, settings):
    state = run_to_gate(store, settings)
    with pytest.raises(InvalidConfigError):
        request_changes(store, state.id, "notes", "upload")
