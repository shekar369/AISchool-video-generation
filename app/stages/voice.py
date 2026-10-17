"""Stage 3 — voice: synthesise narration audio for each scene."""

import wave
from typing import Any

from app.stages.base import Provider, ProviderRegistry, StageContext

registry = ProviderRegistry("voice")

SAMPLE_RATE = 16_000


@registry.register("mock")
class MockVoiceProvider(Provider):
    """Writes silent WAV files of the right length, so timing downstream is realistic."""

    def run(self, ctx: StageContext) -> dict[str, Any]:
        out_dir = ctx.run_dir / "audio"
        out_dir.mkdir(exist_ok=True)
        clips = []
        for scene in ctx.artifacts["storyboard"]["scenes"]:
            path = out_dir / f"scene_{scene['index']:02d}.wav"
            frames = int(scene["duration_s"] * SAMPLE_RATE)
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(SAMPLE_RATE)
                wav.writeframes(b"\x00\x00" * frames)
            clips.append(
                {"scene": scene["index"], "path": str(path), "duration_s": scene["duration_s"]}
            )
        return {"clips": clips}
