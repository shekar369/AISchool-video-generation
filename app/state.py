"""Filesystem-backed run store: one directory per run under ``runs/`` with a ``state.json``."""

import re
import secrets
from pathlib import Path

from app.models import RunRequest, RunState, StageRecord, utcnow

_RUN_ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}$")


class RunNotFoundError(KeyError):
    pass


class RunStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def run_dir(self, run_id: str) -> Path:
        if not _RUN_ID_RE.match(run_id):
            raise RunNotFoundError(run_id)
        return self.root / run_id

    def create(self, request: RunRequest, providers: dict[str, str]) -> RunState:
        run_id = f"{utcnow():%Y%m%d-%H%M%S}-{secrets.token_hex(3)}"
        state = RunState(
            id=run_id,
            request=request,
            stages=[StageRecord(name=stage, provider=p) for stage, p in providers.items()],
        )
        self.run_dir(run_id).mkdir(parents=True)
        self.save(state)
        return state

    def save(self, state: RunState) -> None:
        state.updated_at = utcnow()
        path = self.run_dir(state.id) / "state.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        tmp.replace(path)  # atomic on POSIX, so readers never see a half-written file

    def load(self, run_id: str) -> RunState:
        path = self.run_dir(run_id) / "state.json"
        if not path.is_file():
            raise RunNotFoundError(run_id)
        return RunState.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[RunState]:
        runs = [
            RunState.model_validate_json(p.read_text(encoding="utf-8"))
            for p in self.root.glob("*/state.json")
        ]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)
