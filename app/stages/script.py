"""Stage 1 — script: turn a topic into a sectioned lesson narration."""

from typing import Any

from app.stages.base import Provider, ProviderRegistry, StageContext

registry = ProviderRegistry("script")


@registry.register("mock")
class MockScriptProvider(Provider):
    """Deterministic, offline script so the pipeline runs end to end without API keys."""

    def run(self, ctx: StageContext) -> dict[str, Any]:
        topic, audience = ctx.request.topic, ctx.request.audience
        sections = [
            {
                "heading": "Introduction",
                "narration": f"Today we explore {topic}, made for {audience}.",
            },
            {
                "heading": "Core idea",
                "narration": f"At its heart, {topic} comes down to one key idea.",
            },
            {
                "heading": "Example",
                "narration": f"Let's walk through a real-world example of {topic}.",
            },
            {"heading": "Recap", "narration": f"To recap: you now know the essentials of {topic}."},
        ]
        path = ctx.run_dir / "script.md"
        body = "\n\n".join(f"## {s['heading']}\n\n{s['narration']}" for s in sections)
        path.write_text(f"# {topic}\n\n{body}\n", encoding="utf-8")
        return {"title": topic, "sections": sections, "path": str(path)}
