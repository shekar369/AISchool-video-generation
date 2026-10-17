"""Stage 6: render. Stitch slides and audio into video.mp4 with fades and burned-in captions."""

import wave
from pathlib import Path

from app.stages.base import StageContext, StageInputError, register


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as wav:
        return wav.getnframes() / wav.getframerate()


@register("render", "stub")
def render_stub(ctx: StageContext) -> None:
    """Offline placeholder: computes the timeline an encoder would use; writes no video."""
    script = ctx.read_json("script.json")
    timeline, cursor = [], 0.0
    for slide in script["slides"]:
        image = ctx.path("slides", f"{slide['index']:02d}.png")
        audio = ctx.path("audio", f"{slide['index']:02d}.wav")
        for path in (image, audio):
            if not path.is_file():
                raise StageInputError(f"{path.relative_to(ctx.run_dir)} not found")
        duration = round(wav_seconds(audio), 2)
        timeline.append(
            {
                "index": slide["index"],
                "start_s": round(cursor, 2),
                "duration_s": duration,
                "image": str(image.relative_to(ctx.run_dir)),
                "audio": str(audio.relative_to(ctx.run_dir)),
                "caption": slide["narration"],
            }
        )
        cursor += duration
    ctx.write_json("timeline.json", {"total_s": round(cursor, 2), "slides": timeline})
