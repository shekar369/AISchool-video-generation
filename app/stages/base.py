"""Stage/provider contracts and the per-stage provider registry."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from app.config import Settings
from app.models import RunRequest


class UnknownProviderError(LookupError):
    pass


@dataclass
class StageContext:
    """Everything a provider needs to do its work for one run."""

    run_id: str
    run_dir: Path
    outputs_dir: Path
    request: RunRequest
    settings: Settings
    # Outputs of previously completed stages, keyed by stage name.
    artifacts: dict[str, dict[str, Any]] = field(default_factory=dict)


class Provider(ABC):
    """One implementation of a stage (e.g. a specific TTS vendor).

    ``run`` must be JSON-serialisable in, JSON-serialisable out: its return value is persisted
    to ``state.json`` and handed to downstream stages via ``StageContext.artifacts``.
    """

    name: ClassVar[str]

    @abstractmethod
    def run(self, ctx: StageContext) -> dict[str, Any]: ...


class ProviderRegistry:
    def __init__(self, stage: str) -> None:
        self.stage = stage
        self._providers: dict[str, type[Provider]] = {}

    def register(self, name: str) -> Callable[[type[Provider]], type[Provider]]:
        def decorator(cls: type[Provider]) -> type[Provider]:
            if name in self._providers:
                raise ValueError(f"{self.stage}: provider {name!r} already registered")
            cls.name = name
            self._providers[name] = cls
            return cls

        return decorator

    def get(self, name: str) -> Provider:
        try:
            return self._providers[name]()
        except KeyError:
            raise UnknownProviderError(
                f"Unknown {self.stage} provider {name!r}; available: {self.names()}"
            ) from None

    def names(self) -> list[str]:
        return sorted(self._providers)

    def __contains__(self, name: str) -> bool:
        return name in self._providers
