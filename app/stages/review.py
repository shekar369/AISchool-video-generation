"""Stage 8: review. The human gate: the pipeline pauses at ``awaiting_review`` after this runs.

Approval (``app.pipeline.approve``) is only accepted once every checklist item is ticked.
"""

from app.stages.base import StageContext, register

CHECKLIST: dict[str, str] = {
    "hook": "Hook lands in the first 15 seconds",
    "facts": "Facts and code are correct",
    "voice": "Voice sounds natural, technical terms pronounced correctly",
    "readable": "Slides readable on a phone",
    "title_thumbnail": "Title and thumbnail match the content",
    "helps_learner": "It would genuinely help one learner",
}

REVIEW_ARTIFACTS = ("video.mp4", "timeline.json", "metadata.json", "fact_check.json", "script.json")


@register("review", "checklist")
def review_checklist(ctx: StageContext) -> None:
    """Prepare the review packet: the checklist plus the artifacts that exist to look at."""
    ctx.write_json(
        "review.json",
        {
            "checklist": CHECKLIST,
            "artifacts": [name for name in REVIEW_ARTIFACTS if ctx.path(name).exists()],
        },
    )
