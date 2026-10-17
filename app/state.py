"""Filesystem-backed run store: ``runs/<run_id>/state.json`` plus the stages' artifacts."""

import re
import secrets
import threading
from pathlib import Path

from app.models import RunConfig, RunState, StageState, Status, utcnow

_RUN_ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")


class RunNotFoundError(KeyError):
    pass


class RunStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        # Serialises check-then-set state transitions (approve, redo, ...) across request threads.
        self.lock = threading.Lock()

    def run_dir(self, run_id: str) -> Path:
        if not _RUN_ID_RE.match(run_id):
            raise RunNotFoundError(run_id)
        return self.root / run_id

    def create(self, config: RunConfig, stages: list[StageState]) -> RunState:
        run_id = f"{utcnow():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
        state = RunState(id=run_id, config=config, stages=stages)
        self.run_dir(run_id).mkdir(parents=True)
        self.save(state)
        return state

    def save(self, state: RunState) -> None:
        state.updated_at = utcnow()
        path = self.run_dir(state.id) / "state.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(path)  # atomic on POSIX, so the polling dashboard never reads a partial file

    def load(self, run_id: str) -> RunState:
        path = self.run_dir(run_id) / "state.json"
        if not path.is_file():
            raise RunNotFoundError(run_id)
        return RunState.model_validate_json(path.read_text(encoding="utf-8"))

    def all(self) -> list[RunState]:
        runs = [
            RunState.model_validate_json(p.read_text(encoding="utf-8"))
            for p in self.root.glob("*/state.json")
        ]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)

    def recover_interrupted(self) -> list[str]:
        """Mark runs left ``running`` by a dead process as ``error`` so they can be redone."""
        recovered = []
        for state in self.all():
            if state.status != Status.RUNNING:
                continue
            for stage in state.stages:
                if stage.status == Status.RUNNING:
                    stage.status, stage.error = Status.ERROR, "Interrupted (server restarted)"
            state.status, state.error = Status.ERROR, "Interrupted (server restarted)"
            self.save(state)
            recovered.append(state.id)
        return recovered
