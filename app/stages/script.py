"""Stage 2: script. Turn the capture into one entry per slide, each with narration."""

import re

from app.stages.base import StageContext, register

MAX_BODY_SLIDES = 6


@register("script", "stub")
def script_stub(ctx: StageContext) -> None:
    """Offline placeholder: one slide per sentence of the idea, framed by a hook and an outro."""
    capture = ctx.read_json("capture.json")
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", capture["idea"]) if s.strip()]

    entries = [{"heading": capture["title"], "narration": f"In this video: {capture['title']}."}]
    entries += [
        {"heading": f"Point {i}", "narration": sentence}
        for i, sentence in enumerate(sentences[:MAX_BODY_SLIDES], start=1)
    ]
    entries.append({"heading": "Recap", "narration": f"That's {capture['title']} in a nutshell."})

    slides = [{"index": i, **entry} for i, entry in enumerate(entries, start=1)]
    ctx.write_json("script.json", {"title": capture["title"], "slides": slides})
