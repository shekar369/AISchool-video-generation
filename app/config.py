"""Application settings, loaded from environment variables and an optional .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    runs_dir: Path = Path("runs")
    outputs_dir: Path = Path("outputs")

    # Default provider per stage; a run request may override any of these.
    script_provider: str = "mock"
    storyboard_provider: str = "mock"
    voice_provider: str = "mock"
    visuals_provider: str = "mock"
    assemble_provider: str = "mock"

    anthropic_api_key: SecretStr | None = None
    elevenlabs_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None

    def default_provider(self, stage: str) -> str:
        return getattr(self, f"{stage}_provider")


@lru_cache
def get_settings() -> Settings:
    return Settings()
