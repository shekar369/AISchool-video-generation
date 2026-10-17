"""Pipeline stages. Importing this package registers every provider in ``STAGES``."""

from app.stages import (  # noqa: F401  (imported for their @register side effects)
    capture,
    fact_check,
    metadata,
    render,
    review,
    script,
    slides,
    upload,
    voice,
)
from app.stages.base import (
    REQUIRED_STAGES,
    STAGE_ORDER,
    STAGES,
    StageContext,
    StageFn,
    StageInputError,
    providers,
    register,
)
from app.stages.review import CHECKLIST

__all__ = [
    "CHECKLIST",
    "REQUIRED_STAGES",
    "STAGES",
    "STAGE_ORDER",
    "StageContext",
    "StageFn",
    "StageInputError",
    "providers",
    "register",
]
