import json
from pathlib import Path

import pytest

from app.models import RunRequest, RunStatus, StageStatus
from app.pipeline import create_run, execute, resolve_providers
from app.stages import STAGES, UnknownProviderError
from app.stages.voice import MockVoiceProvider


def test_every_stage_has_a_mock_provider():
    assert list(STAGES) == ["script", "storyboard", "voice", "visuals", "assemble"]
    assert all("mock" in reg for reg in STAGES.values())


def test_mock_pipeline_runs_end_to_end(store, settings):
    state = create_run(store, settings, RunRequest(topic="Photosynthesis"))
    state = execute(store, settings, state.id)

    assert state.status == RunStatus.COMPLETED
    assert all(s.status == StageStatus.COMPLETED for s in state.stages)
    manifest = json.loads(Path(state.output_path).read_text())
    assert manifest["title"] == "Photosynthesis"
    assert len(manifest["timeline"]) == 4
    assert store.load(state.id).status == RunStatus.COMPLETED  # persisted


def test_unknown_provider_is_rejected(settings):
    with pytest.raises(UnknownProviderError):
        resolve_providers(settings, {"voice": "does-not-exist"})
    with pytest.raises(UnknownProviderError):
        resolve_providers(settings, {"not-a-stage": "mock"})


def test_failed_run_resumes_from_failed_stage(store, settings, monkeypatch):
    def boom(self, ctx):
        raise RuntimeError("tts outage")

    monkeypatch.setattr(MockVoiceProvider, "run", boom)
    state = execute(store, settings, create_run(store, settings, RunRequest(topic="Gravity")).id)
    assert state.status == RunStatus.FAILED
    script_finished = state.stages[0].finished_at
    assert [s.status for s in state.stages][:3] == ["completed", "completed", "failed"]

    monkeypatch.undo()
    state = execute(store, settings, state.id)
    assert state.status == RunStatus.COMPLETED
    assert state.stages[0].finished_at == script_finished  # not re-run
