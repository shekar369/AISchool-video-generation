import pytest
from fastapi.testclient import TestClient

from app.api import create_app
from app.config import Settings
from app.state import RunStore


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(_env_file=None, runs_dir=tmp_path / "runs")


@pytest.fixture
def store(settings) -> RunStore:
    return RunStore(settings.runs_dir)


@pytest.fixture
def client(settings) -> TestClient:
    return TestClient(create_app(settings))
