"""Pipeline stages, in execution order. Each module exposes a ``registry`` of providers."""

from app.stages import assemble, script, storyboard, visuals, voice
from app.stages.base import Provider, ProviderRegistry, StageContext, UnknownProviderError

STAGES: dict[str, ProviderRegistry] = {
    m.registry.stage: m.registry for m in (script, storyboard, voice, visuals, assemble)
}

__all__ = ["STAGES", "Provider", "ProviderRegistry", "StageContext", "UnknownProviderError"]
