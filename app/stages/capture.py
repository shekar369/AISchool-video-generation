"""Stage 1: capture. Persist the raw idea exactly as given; rough input is fine."""

from app.stages.base import StageContext, register


@register("capture", "text")
def capture_text(ctx: StageContext) -> None:
    ctx.write_json(
        "capture.json",
        {"channel": ctx.config.channel, "title": ctx.config.title, "idea": ctx.config.idea},
    )
