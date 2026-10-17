"""Stage 7: metadata. Draft title, description, chapters, tags and thumbnail text."""

from app.stages.base import StageContext, register


def timestamp(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


@register("metadata", "stub")
def metadata_stub(ctx: StageContext) -> None:
    """Offline placeholder derived from the script (and the timeline, if rendered)."""
    script = ctx.read_json("script.json")
    starts: dict[int, float] = {}
    if ctx.path("timeline.json").is_file():
        starts = {s["index"]: s["start_s"] for s in ctx.read_json("timeline.json")["slides"]}

    ctx.write_json(
        "metadata.json",
        {
            "title": script["title"],
            "description": " ".join(s["narration"] for s in script["slides"][:2]),
            "chapters": [
                f"{timestamp(starts.get(s['index'], 0))} {s['heading']}" for s in script["slides"]
            ]
            if starts
            else [],
            "tags": sorted(
                {w.lower().strip(".,:!?") for w in script["title"].split() if len(w) > 3}
            ),
            "thumbnail_text": script["title"][:40],
        },
    )
