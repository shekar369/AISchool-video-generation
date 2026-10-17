"""Stage 2 — storyboard: split the script into timed scenes with visual prompts."""

from typing import Any

from app.stages.base import Provider, ProviderRegistry, StageContext

registry = ProviderRegistry("storyboard")

WORDS_PER_SECOND = 2.5


@registry.register("mock")
class MockStoryboardProvider(Provider):
    """One scene per script section; duration estimated from narration length."""

    def run(self, ctx: StageContext) -> dict[str, Any]:
        scenes = []
        for i, section in enumerate(ctx.artifacts["script"]["sections"], start=1):
            words = len(section["narration"].split())
            scenes.append(
                {
                    "index": i,
                    "heading": section["heading"],
                    "narration": section["narration"],
                    "visual_prompt": f"Clean educational slide titled '{section['heading']}'",
                    "duration_s": round(max(words / WORDS_PER_SECOND, 2.0), 2),
                }
            )
        return {"scenes": scenes}
