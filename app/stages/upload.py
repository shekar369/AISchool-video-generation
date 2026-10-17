"""Stage 9: upload. Upload to YouTube as PRIVATE; the owner publishes manually."""

from app.stages.base import StageContext, register


@register("upload", "stub")
def upload_stub(ctx: StageContext) -> None:
    """Offline placeholder: records what would be uploaded. Never publishes."""
    ctx.write_json(
        "upload.json",
        {
            "uploaded": False,
            "privacy": "private",
            "video": "video.mp4" if ctx.path("video.mp4").exists() else None,
            "metadata": ctx.read_json("metadata.json")
            if ctx.path("metadata.json").exists()
            else None,
        },
    )
