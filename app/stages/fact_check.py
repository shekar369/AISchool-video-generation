"""Stage 3: fact_check. Verify technical claims and code; flag anything uncertain."""

from app.stages.base import StageContext, register


@register("fact_check", "stub")
def fact_check_stub(ctx: StageContext) -> None:
    """Offline placeholder: checks nothing, and says so, so the reviewer isn't misled."""
    script = ctx.read_json("script.json")
    ctx.write_json(
        "fact_check.json",
        {
            "verified": False,
            "note": "Stub provider: no claims were checked.",
            "flags": [],
            "slides_seen": len(script["slides"]),
        },
    )
