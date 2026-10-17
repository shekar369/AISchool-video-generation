"""Stage 5: voice. Generate audio per slide; slide timing follows audio length."""

import wave

from app.stages.base import StageContext, register

SAMPLE_RATE = 16_000
WORDS_PER_SECOND = 2.5
MIN_SECONDS = 2.0


@register("voice", "stub")
def voice_stub(ctx: StageContext) -> None:
    """Offline placeholder: silent WAVs sized to a natural speaking rate for each narration."""
    script = ctx.read_json("script.json")
    out = ctx.path("audio")
    out.mkdir(exist_ok=True)
    for slide in script["slides"]:
        seconds = max(len(slide["narration"].split()) / WORDS_PER_SECOND, MIN_SECONDS)
        with wave.open(str(out / f"{slide['index']:02d}.wav"), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(b"\x00\x00" * int(seconds * SAMPLE_RATE))
